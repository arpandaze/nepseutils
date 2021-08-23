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

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from tabulate import tabulate

from .meroshare import MeroShare

logging.basicConfig(format="%(asctime)s %(message)s", level=logging.INFO)


class NepseUtils(Cmd):
    prompt = "NepseUtils > "
    intro = "Welcome to NepseUtils! Type ? for help!"

    data_folder = Path.home() / ".nepseutils"

    default_data = {
        "accounts": [],
        "capitals": {},
        "max_retry": 5,
        "retry_delay": 3,
    }

    def preloop(self, *args, **kwargs):

        if not (self.data_folder / "data.db").exists():
            logging.info("Creating a new data file! Existing file not found!")

            self.data_folder.mkdir(parents=True, exist_ok=True)
            self.create_new_data()

        else:
            password = getpass(prompt="Enter password to unlock: ")
            self.fernet_init(password)
            self.load_data()

    def load_data(self):
        with open(self.data_folder / "data.db", "rb") as data:
            encrypted_data = data.read()
            try:
                self.data = json.loads(
                    self.fernet.decrypt(encrypted_data).decode("UTF-8")
                )
            except InvalidToken:
                print("Password Incorrect!")
                exit()

        if not self.data["capitals"]:
            self.update_capital_list()

    def fernet_init(self, password):
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=password.encode("UTF-8"),
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode("UTF-8")))
        self.fernet = Fernet(key)

    def update_capital_list(self):
        logging.info("Updating capital list!")
        capital_list = MeroShare.get_capital_list()
        self.data["capitals"].update(capital_list)
        self.save_data()

    def save_data(self):
        with open(self.data_folder / "data.db", "wb") as data:
            encrypted_data = self.fernet.encrypt(json.dumps(self.data).encode())
            data.write(encrypted_data)

    def create_new_data(self):
        password = getpass(prompt="Password to unlock NepseUtils: ")

        self.fernet_init(password)

        self.data = self.default_data.copy()
        self.update_capital_list()

    def do_add(self, args):
        args = args.split(" ")

        if len(args) == 3:
            dmat, password, pin = args

        elif len(args) == 1 and args[0] == "":
            dmat = input("Enter DMAT: ")
            password = getpass(prompt="Enter Meroshare Password: ")

            if len(password) < 8:
                print("Password too short!")
                print("Pasting password on windows is not recommended!")
                return

            pin = input("Enter Meroshare PIN: ")

        else:
            print('Incorrect format. Type "help add" for help!')
            return

        ms = MeroShare(dmat=dmat, password=password, pin=pin)
        details = ms.get_details()
        ms.logout()

        assert details, "Details request failed!"

        self.data["accounts"].append(details)
        self.save_data()

        logging.info(
            f'Successfully obtained details for account: {details.get("name")}'
        )

    def help_add(self):
        print("Add a new account!")
        print("Usage: add {dmat} {password} {pin}")

    def do_remove(self, args):
        self.do_list(args="accounts")
        account_id = input("Choose an account ID: ")
        del self.data["accounts"][int(account_id) - 1]
        self.save_data()
        print("Account removed!")

    def do_list(self, args):
        args = args.split(" ")

        if not args:
            print('Incorrect format. Type "help list" for help!')
            return

        if len(args) == 2 and args[0] == "accounts" and args[1] == "full":
            print("WARNING: This will display password and pin of your accounts!")
            confirm = input("Do you want to continue? (y/n) :")

            if confirm == "y":
                headers = ["ID", "Name", "DMAT", "Account", "CRN", "Password", "PIN"]
                table = [
                    [
                        self.data["accounts"].index(itm) + 1,
                        itm.get("name"),
                        itm.get("dmat"),
                        itm.get("account"),
                        itm.get("crn"),
                        itm.get("password"),
                        itm.get("pin"),
                    ]
                    for itm in self.data["accounts"]
                ]
                print(tabulate(table, headers=headers, tablefmt="pretty"))

        elif args[0] == "accounts":
            headers = ["ID", "Name", "DMAT", "Account", "CRN"]
            table = [
                [
                    self.data["accounts"].index(itm) + 1,
                    itm.get("name"),
                    itm.get("dmat"),
                    itm.get("account"),
                    itm.get("crn"),
                ]
                for itm in self.data["accounts"]
            ]
            print(tabulate(table, headers=headers, tablefmt="pretty"))

        elif args[0] == "capitals":
            headers = ["DPID", "ID"]
            table = [[key, value] for key, value in self.data["capitals"].items()]
            print(tabulate(table, headers=headers, tablefmt="pretty"))

        elif args[0] == "results":
            results = MeroShare.get_result_company_list()

            headers = ["ID", "Scrip", "Name"]
            table = [
                [itm.get("id"), itm.get("scrip"), itm.get("name")] for itm in results
            ]
            print(tabulate(table, headers=headers, tablefmt="pretty"))

    def help_list(self):
        print("Lists added accounts")

    def do_result(self, args):
        if not args:
            self.do_list(args="results")
            company_id = input("Choose a company ID: ")
        else:
            args = args.split(" ")
            company_id = args[0]

        headers = ["Name", "Alloted", "Quantity"]
        table = []
        for account in self.data["accounts"]:
            result = MeroShare.check_result_with_dmat(
                company_id=company_id, dmat=account.get("dmat")
            )
            table.append(
                [
                    account.get("name"),
                    result.get("success"),
                    "None"
                    if not result.get("success")
                    else re.search("([0-9]+)", result.get("message")).group(0),
                ]
            )
        print(tabulate(table, headers=headers, tablefmt="pretty"))

    def help_result(self):
        print("Check results of IPO")

    def do_apply(self, args):
        company_to_apply = None
        appicable_issues = None
        quantity = None

        apply_headers = ["Name", "Quantity", "Applied", "Message"]
        apply_table = []

        for account in self.data["accounts"]:
            ms = MeroShare(**account)
            ms.login()

            if not company_to_apply:
                appicable_issues = ms.get_applicable_issues()
                headers = ["Share ID", "Company Name", "Scrip", "Close Date"]
                table = [
                    [
                        itm.get("companyShareId"),
                        itm.get("companyName"),
                        itm.get("scrip"),
                        itm.get("issueCloseDate"),
                    ]
                    for itm in appicable_issues
                ]
                print(tabulate(table, headers=headers, tablefmt="pretty"))
                company_to_apply = input("Enter Share ID: ")
                quantity = input("Units to Apply: ")
            result = ms.apply(share_id=company_to_apply, quantity=quantity)
            ms.logout()
            apply_table.append(
                [
                    account.get("name"),
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
        for account in self.data["accounts"]:
            ms = MeroShare(**account)
            ms.login()
            reports = ms.get_application_reports()

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
            detailed_form = ms.get_application_status(form_id=form_id)
            ms.logout()
            status_table.append(
                [
                    account.get("name"),
                    detailed_form.get("statusName"),
                    detailed_form.get("reasonOrRemark"),
                ]
            )

        print(tabulate(status_table, headers=status_headers, tablefmt="pretty"))

    def do_change(self, args):
        args = args.split(" ")

        if args[0] == "lock":
            password = getpass(prompt="Enter new password for NepseUtils: ")
            self.fernet_init(password)
            self.save_data()
            print("Password changed successfully!")
            exit(0)

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
