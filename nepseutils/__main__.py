#!/usr/bin/python3
# -*- coding: utf-8 -*-

import base64
import json
import logging
import os
import re
from cmd import Cmd
from getpass import getpass
from pathlib import Path
from typing import List

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from tabulate import SEPARATING_LINE, tabulate

from nepseutils.account import Account
from nepseutils.errors import LocalException
from nepseutils.portfolio import PortfolioEntry
from nepseutils import config_converter

from .meroshare import MeroShare

logging.basicConfig(format="%(asctime)s %(message)s", level=logging.INFO)


class NepseUtils(Cmd):
    prompt = "NepseUtils > "
    intro = "Welcome to NepseUtils! Type ? for help!"

    ms: MeroShare

    def preloop(self, *args, **kwargs):
        if not (MeroShare.default_config_path()).exists():
            config_converter.pre_versioning_to_current()

            logging.info("Creating a new data file! Existing file not found!")

            MeroShare.default_config_directory().mkdir(parents=True, exist_ok=True)

            password = getpass(prompt="Set a password to unlock: ")
            self.ms = MeroShare.new(password)

        else:
            password = getpass(prompt="Enter password to unlock: ")

            try:
                self.ms = MeroShare.load(password)
            except InvalidToken as e:
                print("Incorrect password!")
                print(e)
                exit()

    def do_add(self, args):
        args = args.split(" ")

        if len(args) == 4:
            dmat, password, crn, pin = args

        elif len(args) == 1 and args[0] == "":
            dmat = input("Enter DMAT: ")
            password = getpass(prompt="Enter Meroshare Password: ")

            if len(password) < 8:
                print("Password too short!")
                print("Pasting password on windows is not recommended!")
                return

            crn = input("Enter CRN Number: ")
            pin = input("Enter Meroshare PIN: ")

        else:
            print('Incorrect format. Type "help add" for help!')
            return

        capital_id = self.ms.capitals.get(dmat[3:8])

        if not capital_id:
            print("Could not find capital ID for given DMAT!")
            print("Updating capital list!")
            self.ms.update_capital_list()
            capital_id = self.ms.capitals.get(dmat[3:8])

        if not capital_id:
            print("Could not find capital ID for given DMAT!")
            print("Please enter capital ID manually!")
            capital_id = input("Enter Capital ID: ")

        account = Account(dmat, password, int(pin), int(capital_id), crn)

        try:
            account.get_details()
        except LocalException as e:
            print(f"Failed to obtain details for account: {e}")

        self.ms.accounts.append(account)
        self.ms.save_data()

        logging.info(f"Successfully obtained details for account: {account.name}")

    def help_add(self):
        print("Add a new account!")
        print("Usage: add {dmat} {password} {crn} {pin}")

    def do_remove(self, args):
        self.do_list(args="accounts")
        account_id = input("Choose an account ID: ")
        del self.ms.accounts[int(account_id) - 1]
        self.ms.save_data()
        print("Account removed!")

    def list_accounts_full(self):
        print("WARNING: This will display password and pin of your accounts!")
        confirm = input("Do you want to continue? (y/n) :")

        if confirm == "y":
            headers = ["ID", "Name", "DMAT", "Account", "CRN", "Password", "PIN"]
            table = [
                [
                    self.ms.accounts.index(itm) + 1,
                    itm.name,
                    itm.dmat,
                    itm.account,
                    itm.crn,
                    itm.password,
                    itm.pin,
                ]
                for itm in self.ms.accounts
            ]
            print(tabulate(table, headers=headers, tablefmt="pretty"))

    def list_accounts(self):
        headers = ["ID", "Name", "DMAT", "Account", "CRN", "Tag"]
        table = [
            [
                self.ms.accounts.index(itm) + 1,
                itm.name,
                itm.dmat,
                itm.account,
                itm.crn,
                itm.tag,
            ]
            for itm in self.ms.accounts
        ]
        print(tabulate(table, headers=headers, tablefmt="pretty"))

    def list_results(self):
        results = self.ms.default_account.get_application_reports()
        results = MeroShare.fetch_result_company_list()

        headers = ["ID", "Scrip", "Name"]

        print(f"{results}")
        table = [[itm.get("id"), itm.get("scrip"), itm.get("name")] for itm in results]

        print(tabulate(table, headers=headers, tablefmt="pretty"))
        return results

    def list_capitals(self):
        headers = ["DPID", "ID"]
        table = [[key, value] for key, value in self.ms.capitals.items()]
        print(tabulate(table, headers=headers, tablefmt="pretty"))

    def do_portfolio(self, args):
        portfolio: List[PortfolioEntry] = []

        if args == "all":
            for account in self.ms.accounts:
                if len(account.portfolio.entries) == 0:
                    account.fetch_portfolio()

                for entry in account.portfolio.entries:
                    found = False

                    for combined_entry in portfolio:
                        if combined_entry.script == entry.script:
                            combined_entry.current_balance += entry.current_balance
                            combined_entry.value_as_of_last_transaction_price += (
                                entry.value_as_of_last_transaction_price
                            )
                            found = True
                            break

                    if not found:
                        portfolio.append(PortfolioEntry.from_json(entry.to_json()))

        else:
            self.list_accounts()
            account_id = input("Choose an account ID: ")

            account = self.ms.accounts[int(account_id) - 1]

            if len(account.portfolio.entries) == 0:
                account.fetch_portfolio()

            portfolio = account.portfolio.entries

        total_value = 0.0
        for entry in portfolio:
            total_value += entry.value_as_of_last_transaction_price

        headers = ["Scrip", "Balance", "Last Transaction Price", "Value"]
        table = [
            [
                itm.script,
                itm.current_balance,
                f"{itm.last_transaction_price:,.1f}",
                f"{itm.value_as_of_last_transaction_price:,.1f}",
            ]
            for itm in portfolio
        ]
        table.append(["Total", "", "", f"{total_value:,.1f}"])
        print(tabulate(table, headers=headers, tablefmt="pretty"))

    def do_list(self, args):
        args = args.split(" ")

        if not args:
            print('Incorrect format. Type "help list" for help!')
            return

        if len(args) == 2 and args[0] == "accounts" and args[1] == "full":
            self.list_accounts_full()

        elif args[0] == "accounts":
            self.list_accounts()

        elif args[0] == "capitals":
            self.list_capitals()

        elif args[0] == "results":
            self.list_results()

    def help_list(self):
        print("Lists added accounts")

    def do_select(self, args):
        if not args:
            print('Incorrect format. Type "help select" for help!')
            return

        args = args.split(" ")

        if args == ["all"]:
            self.ms.tag_selections = []
            self.prompt = f"NepseUtils > "
            return
        else:
            self.ms.tag_selections = args
            self.prompt = f"NepseUtils ({','.join(self.ms.tag_selections)}) > "

    def do_result(self, args):
        results = []
        if not args:
            results = self.do_list(args="results")
            company_id = input("Choose a company ID: ")
        else:
            args = args.split(" ")
            company_id = args[0]

        symbol = None
        for company in results or []:
            if company.get("id") == company_id:
                symbol = company.get("scrip")
                break

        headers = ["Name", "Alloted", "Quantity"]
        table = []
        for account in self.ms.accounts:
            account.fetch_applied_issues()

            issue_ins = None
            for issue in account.issues:
                if issue.symbol == symbol:
                    issue_ins = issue
                    break

            if not issue_ins:
                table.append([account.name, "N/A", "N/A"])
                continue

            table.append(
                [
                    account.name,
                    issue_ins.alloted,
                    "N/A" if not issue_ins.alloted else issue_ins.alloted_quantity,
                ]
            )
        print(tabulate(table, headers=headers, tablefmt="pretty"))

    def do_tag(self, args):
        self.list_accounts()

        input_account_id = input("Choose an account ID: ")

        account = self.ms.accounts[int(input_account_id) - 1]

        tag = input(f"Set tag for account {account.name}: ")

        if tag == "" or tag == "all":
            tag = None
            print(f"Invalid tag {tag}. Setting to None")

        account.tag = tag
        self.ms.save_data()

    def help_result(self):
        print("Check results of IPO")

    def do_apply(self, args):
        company_to_apply = None
        quantity = None

        apply_headers = ["Name", "Quantity", "Applied", "Message"]
        apply_table = []

        appicable_issues = self.ms.default_account.get_applicable_issues()

        headers = [
            "Share ID",
            "Company Name",
            "Scrip",
            "Type",
            "Group",
            "Close Date",
        ]

        table = [
            [
                itm.get("companyShareId"),
                itm.get("companyName"),
                itm.get("scrip"),
                itm.get("shareTypeName"),
                itm.get("shareGroupName"),
                itm.get("issueCloseDate"),
            ]
            for itm in appicable_issues
        ]

        print(tabulate(table, headers=headers, tablefmt="pretty"))
        company_to_apply = input("Enter Share ID: ")
        quantity = input("Units to Apply: ")

        for account in self.ms.accounts:
            if not company_to_apply:
                appicable_issues = account.get_applicable_issues()

            try:
                result = account.apply(
                    share_id=int(company_to_apply), quantity=int(quantity)
                )
            except Exception as e:
                print(e)
                print(f"Failed to apply for {account.name}!")
                result = {"status": "FAILED", "message": "Failed to apply!"}

            try:
                account.logout()
            except:
                print(f"Failed to logout for {account.name}!")

            apply_table.append(
                [
                    account.name,
                    quantity,
                    result.get("status") == "CREATED",
                    result.get("message"),
                ]
            )

        print(tabulate(apply_table, headers=apply_headers, tablefmt="pretty"))

    def help_apply(self):
        print("Apply for shares")

    def do_fetch(self, args):
        pass

    def do_status(self, args):
        company_share_id = None
        status_headers = ["Name", "Status", "Detail"]
        status_table = []
        for account in self.ms.accounts:
            reports = account.get_application_reports()

            if not company_share_id:
                headers = ["Share ID", "Company Name", "Scrip"]
                table = [
                    [
                        itm.get("companyShareId"),
                        itm.get("companyName"),
                        itm.get("scrip"),
                    ]
                    for itm in reports
                ]
                print(tabulate(table, headers=headers, tablefmt="pretty"))

                company_share_id = input("Enter Share ID: ")

            form_id = [
                itm.get("applicantFormId")
                for itm in reports
                if itm.get("companyShareId") == int(company_share_id)
            ][0]
            detailed_form = account.get_application_status(form_id=form_id)
            account.logout()
            status_table.append(
                [
                    account.name,
                    detailed_form.get("statusName"),
                    detailed_form.get("reasonOrRemark"),
                ]
            )

        print(tabulate(status_table, headers=status_headers, tablefmt="pretty"))

    def do_change(self, args):
        args = args.split(" ")

        if args[0] == "lock":
            password = getpass(prompt="Enter new password for NepseUtils: ")
            self.ms.fernet_init(password)
            self.ms.save_data()
            print("Password changed successfully!")
            exit(0)

        elif args[0] == "password":
            self.do_list(args="accounts")
            account_id = input("Choose an account ID: ")
            account = self.ms.accounts[int(account_id) - 1]

            new_password = getpass(
                prompt=f"Enter new password for account {account.name}: "
            )

            if len(new_password) < 8:
                print("Password too short!")
                print("Pasting password on windows is not recommended!")
                return

            self.ms.accounts[int(account_id) - 1].password = new_password
            self.ms.save_data()

    def do_azcaptcha(self, args):
        logging.warning("This command is deprecated!")

    def help_change(self):
        print("Options:")
        print("lock: Change nepseutils password")

    def do_exit(self, *args):
        print("Bye")
        return True

    def help_exit(self):
        print("Exit NepseUtils. Shortcuts: q, or ctrl+D")

    def do_clear(self, args):
        os.system("cls" if os.name == "nt" else "clear")

    def do_c(self, args):
        self.do_clear(args)

    def default(self, inp):
        if inp == "x" or inp == "q" or inp == "EOF":
            return self.do_exit(inp)

        print('Invalid command! Type "help" for help')


if __name__ == "__main__":
    NepseUtils().cmdloop()
