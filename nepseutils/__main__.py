#!/usr/bin/python3

import argparse
import logging
import os
from cmd import Cmd
from getpass import getpass
from typing import List

from cryptography.fernet import InvalidToken
from tabulate import tabulate

from nepseutils.core.account import Account
from nepseutils.core.errors import LocalException
from nepseutils.core.meroshare import MeroShare
from nepseutils.core.portfolio import PortfolioEntry
from nepseutils.utils import config_converter

logging.basicConfig(format="%(asctime)s %(message)s", level=logging.INFO)
logging.getLogger("urllib3").setLevel(logging.ERROR)


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

    def help_add(self):
        print("Add a new account!")
        print("Usage: add {dmat} {password} {crn} {pin}")

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

    def help_remove(self):
        print("Remove an account!")
        print("Usage: remove")
        print("Then choose an account ID from the list!")

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
        results = self.ms.default_account.fetch_application_reports()

        headers = ["ID", "Scrip", "Name"]

        table = [
            [itm.get("companyShareId"), itm.get("scrip"), itm.get("companyName")]
            for itm in results[::-1]
        ]

        print(tabulate(table, headers=headers, tablefmt="pretty"))
        return results

    def list_capitals(self):
        headers = ["DPID", "ID"]
        table = [[key, value] for key, value in self.ms.capitals.items()]
        print(tabulate(table, headers=headers, tablefmt="pretty"))

    def help_portfolio(self):
        print("List portfolio of an account!")
        print("Usage: portfolio {account_id}")
        print("OR")
        print("Usage: portfolio all")

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

    def help_list(self):
        print("List accounts, capitals or results!")
        print("Usage: list { accounts | accounts full | capitals | results }")

    def do_list(self, args):
        args = args.split(" ")

        if not args:
            print('Incorrect format. Type "help list" for help!')
            return

        if len(args) == 2 and args[0] == "accounts" and args[1] == "full":
            return self.list_accounts_full()

        elif args[0] == "accounts":
            return self.list_accounts()

        elif args[0] == "capitals":
            return self.list_capitals()

        elif args[0] == "results":
            return self.list_results()

    def help_select(self):
        print("Selects accounts with specific tag to be used for further commands!")
        print("Usage: select {tag-name}")
        print("Usage: select all")

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

    def help_sync(self):
        print("Syncs unfetched portfolio and application status from MeroShare!")

    def do_sync(self, args):
        for account in self.ms.accounts:
            account.fetch_portfolio()
            account.fetch_applied_issues()
            account.fetch_applied_issues_status()
            print(f"Synced {account.name}!")

    def help_stats(self):
        print("Shows statistics of accounts!")
        print("Usage: stats")

    def do_stats(self, args):
        headers = [
            "Name",
            "Total Applied",
            "Total Rejected",
            "Total Allocations",
            "Total Units Alloted",
            "Total Amount Alloted",
            "% Alloted",
        ]
        table = []

        for account in self.ms.accounts:
            account_applied = len(account.issues)
            account_alloted = 0
            account_rejected = 0
            account_units_alloted = 0.0
            account_amount_alloted = 0.0

            for issue in account.issues:
                if issue.alloted:
                    account_alloted += 1
                    account_units_alloted += issue.alloted_quantity or 0
                    account_amount_alloted += issue.applied_amount or 0

                if issue.status == "BLOCK_FAILED":
                    account_rejected += 1

            table.append(
                [
                    account.name,
                    account_applied,
                    account_rejected,
                    account_alloted,
                    account_units_alloted,
                    account_amount_alloted,
                    f"{account_alloted/account_applied*100:.2f}%",
                ]
            )

        total_applied = sum([itm[1] for itm in table])
        total_rejected = sum([itm[2] for itm in table])
        total_alloted = sum([itm[3] for itm in table])
        total_units_alloted = sum([itm[4] for itm in table])
        total_amount_alloted = sum([itm[5] for itm in table])
        total_percent_alloted = (
            total_alloted / total_applied * 100 if total_applied > 0 else 0.0
        )

        table.append(
            [
                "Total",
                total_applied,
                total_rejected,
                total_alloted,
                total_units_alloted,
                f"{total_amount_alloted:.2f}",
                f"{total_percent_alloted:.2f}%",
            ]
        )

        print(tabulate(table, headers=headers, tablefmt="pretty"))

    def do_result(self, args):
        if not args:
            self.do_list(args="results")
            company_id = input("Choose a company ID: ")
        else:
            args = args.split(" ")
            company_id = args[0]

        headers = ["Name", "Alloted", "Quantity"]
        table = []
        for account in self.ms.accounts:
            issue_ins = None
            for issue in account.issues:
                if issue.company_share_id == int(company_id):
                    issue_ins = issue
                    break

            if not issue_ins:
                table.append([account.name, "N/A", ""])
                continue

            if issue_ins.alloted == None:
                account.fetch_applied_issues_status(company_id=company_id)

            table.append(
                [
                    account.name,
                    "Yes" if issue_ins.alloted else "No",
                    "" if not issue_ins.alloted else issue_ins.alloted_quantity,
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

    def help_tag(self):
        print("Tag an account to group them!")

    def help_result(self):
        print("Check results of IPO")

    def do_apply(self, args):
        company_to_apply = None
        quantity = None

        apply_headers = ["Name", "Quantity", "Applied", "Message"]
        apply_table = []

        appicable_issues = self.ms.default_account.fetch_applicable_issues()

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
                appicable_issues = account.fetch_applicable_issues()

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

    def do_status(self, args):
        company_share_id = None
        status_headers = ["Name", "Status", "Detail"]
        status_table = []
        for account in self.ms.accounts:
            reports = account.fetch_application_reports()

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
                print(tabulate(table[::-1], headers=headers, tablefmt="pretty"))

                company_share_id = input("Enter Share ID: ")

            form_id = None
            for forms in reports:
                if forms.get("companyShareId") == int(company_share_id) and forms.get(
                    "applicantFormId"
                ):
                    form_id = forms.get("applicantFormId")
                    break

            try:
                detailed_form = account.fetch_application_status(form_id=form_id)
            except LocalException as e:
                account.logout()
                status_table.append([account.name, "N/A", "N/A"])
                continue

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
            self.ms.fernet = self.ms.fernet_init(password)
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

    def help_loglevel(self):
        print("Set logging level")
        print("Usage: loglevel {debug | info | warning | error | critical}")

    def do_loglevel(self, args):
        if args == "debug":
            self.ms.logging_level = logging.DEBUG
        elif args == "info":
            self.ms.logging_level = logging.INFO
        elif args == "warning":
            self.ms.logging_level = logging.WARNING
        elif args == "error":
            self.ms.logging_level = logging.ERROR
        elif args == "critical":
            self.ms.logging_level = logging.CRITICAL
        else:
            print("Invalid argument!")

        self.ms.save_data()
        print(f"Logging level set to {args}! Restart NepseUtils!")
        exit()

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

    def help_telegram(self):
        print("Enable or disable telegram notifications")
        print("Usage: telegram {enable | disable}")

    def do_telegram(self, args):
        if args == "enable":
            token = input("Enter telegram bot token: ")
            chat_id = input("Enter telegram chat id: ")

            if not token or not chat_id:
                print("Invalid token or chat id!")
                return

            self.ms.telegram_bot_token = token
            self.ms.telegram_chat_id = chat_id
            self.ms.save_data()

        elif args == "disable":
            self.ms.telegram_bot_token = None
            self.ms.telegram_chat_id = None
            self.ms.save_data()

        else:
            print("Invalid argument!")

    def do_c(self, args):
        self.do_clear(args)

    @staticmethod
    def auto(password: str):
        if not password:
            print("Password not provided!")
            return

        ms: MeroShare = MeroShare.load(password)

        applicable_issues = ms.default_account.fetch_applicable_issues()

        has_applicable = False
        for issue in applicable_issues:
            if (
                issue.get("shareTypeName") == "IPO"
                and issue.get("shareGroupName") == "Ordinary Shares"
                and issue.get("subGroup") == "For General Public"
            ):
                has_applicable = True
                share_id = issue.get("companyShareId")
                try:
                    min_unit = ms.default_account.find_min_apply_unit(share_id)
                except Exception as _:
                    min_unit = 10

                for account in ms.accounts:
                    try:
                        account.apply(share_id=int(share_id), quantity=min_unit)
                    except Exception as _:
                        pass

        if not has_applicable:
            logging.info("No applicable issues found!")

        ms.save_data()

        for account in ms.accounts:
            account.fetch_applied_issues()
            account.fetch_applied_issues_status()

        ms.save_data()
        ms.logging_handler.shutdown()

    def default(self, inp):
        if inp == "x" or inp == "q" or inp == "EOF":
            return self.do_exit(inp)

        print('Invalid command! Type "help" for help')


def main():
    parser = argparse.ArgumentParser(description="Nepse Utility CLI")

    parser.add_argument("--password", help="Password for auto_apply")
    parser.add_argument("--auto", action="store_true", help="Enable auto_apply mode")

    args = parser.parse_args()

    if args.auto and args.password:
        NepseUtils().auto(args.password)
    else:
        NepseUtils().cmdloop()


if __name__ == "__main__":
    main()
