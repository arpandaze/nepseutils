#!/usr/bin/python3
# -*- coding: utf-8 -*-

import requests
import json
import logging
import os
from tenacity import retry, stop_after_attempt, wait_fixed

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.105 Safari/537.36"  # noqa

logging.basicConfig(format="%(asctime)s %(message)s", level=logging.INFO)


class MeroShare:
    def __init__(
        self,
        name=None,
        dpid=None,
        username=None,
        password=None,
        account=None,
        dmat=None,
        crn=None,
        pin=None,
        capital_id=None,
    ):

        self.__name = name
        self.__dpid = dpid
        self.__username = username
        self.__password = password
        self.__account = account
        self.__dmat = dmat
        self.__crn = crn
        self.__pin = pin
        self.__capital_id = capital_id
        self.__capitals = {}
        self.__session = requests.Session()
        self.__auth_token = None
        self.__applicable_issues = {}

        if os.path.isfile("active.token"):
            with open("active.token") as token_file:
                self.__auth_token = token_file.read()
                self.logout()

        try:
            with open("capitals.json", "r") as capitals_file:
                self.__capitals = json.load(capitals_file)
        except Exception:
            pass

        if not self.__capitals:
            self._update_capital_list()

        if not capital_id:
            self.__capital_id = self.__capitals.get(dpid)
            assert self.__capital_id, "DPID not on capital list!"

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2), reraise=True)
    def _update_capital_list(self) -> bool:
        logging.info("Updating capital list!")
        with self.__session as sess:
            headers = {
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.9",
                "Authorization": "null",
                "Connection": "keep-alive",
                "Origin": "https://meroshare.cdsc.com.np",
                "Referer": "https://meroshare.cdsc.com.np/",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-site",
                "Sec-GPC": "1",
                "User-Agent": USER_AGENT,
            }
            sess.headers.update(headers)
            cap_req = sess.get("https://backend.cdsc.com.np/api/meroShare/capital/")
            cap_list = cap_req.json()
            any(
                map(
                    lambda x: self.__capitals.update({x.get("code"): x.get("id")}),
                    cap_list,
                )
            )

            assert self.__capitals, "Capital request failed!"

            with open("capitals.json", "w") as cap_file:
                json.dump(self.__capitals, cap_file)

            return True

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(3), reraise=True)
    def login(self) -> bool:
        assert (
            self.__username and self.__password and self.__dpid
        ), "Username, password and DPID required!"

        try:
            with self.__session as sess:
                data = json.dumps(
                    {
                        "clientId": self.__capital_id,
                        "username": self.__username,
                        "password": self.__password,
                    }
                )

                headers = {
                    "Accept": "application/json, text/plain, */*",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Authorization": "null",
                    "Connection": "keep-alive",
                    "Content-Type": "application/json",
                    "Origin": "https://meroshare.cdsc.com.np",
                    "Referer": "https://meroshare.cdsc.com.np/",
                    "Sec-Fetch-Dest": "empty",
                    "Sec-Fetch-Mode": "cors",
                    "Sec-Fetch-Site": "same-site",
                    "Sec-GPC": "1",
                    "User-Agent": USER_AGENT,
                }
                sess.headers.update(headers)

                login_req = sess.post(
                    "https://backend.cdsc.com.np/api/meroShare/auth/", data=data
                )

                if login_req.status_code != 200:
                    logging.warning(f"Login failed! {login_req.status_code}")
                    raise Exception("Login failed!")

                self.__auth_token = login_req.headers.get("Authorization")

                with open("active.token", "w") as session_file:
                    session_file.write(self.__auth_token)

                logging.info(f"Logged in successfully!  Account: {self.__name}!")

        except Exception as error:
            logging.info(error)
            raise error
            logging.error(
                f"Login request failed! Retrying ({self.login.retry.statistics.get('attempt_number')})!"
            )

    @retry(stop=stop_after_attempt(5), wait=wait_fixed(3), reraise=True)
    def logout(self):
        assert self.__auth_token, "Not logged in!"

        try:
            with self.__session as sess:
                headers = {
                    "Accept": "application/json, text/plain, */*",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Authorization": self.__auth_token,
                    "Connection": "keep-alive",
                    "Origin": "https://meroshare.cdsc.com.np",
                    "Referer": "https://meroshare.cdsc.com.np/",
                    "Sec-Fetch-Dest": "empty",
                    "Sec-Fetch-Mode": "cors",
                    "Sec-Fetch-Site": "same-site",
                    "Sec-GPC": "1",
                    "User-Agent": USER_AGENT,
                }
                sess.headers.update(headers)
                logout_req = sess.get(
                    "https://webbackend.cdsc.com.np/api/meroShare/auth/logout/",
                )

                if logout_req.status_code != 201:
                    logging.warning("Logout failed!")
                    logging.warning(logout_req.content)
                    raise Exception("Logout failed!")

                self.__auth_token = None
                os.remove("active.token")
                logging.info(f"Logged out successfully!  Account: {self.__name}!")
                return True
        except Exception as error:
            logging.error(
                f"Logout request failed! Retrying ({self.logout.retry.statistics.get('attempt_number')})!"
            )
            logging.info(error)
            raise error

    @retry(stop=stop_after_attempt(5), wait=wait_fixed(3), reraise=True)
    def get_applicable_issues(self):
        try:
            with self.__session as sess:
                data = json.dumps(
                    {
                        "filterFieldParams": [
                            {
                                "key": "companyIssue.companyISIN.script",
                                "alias": "Scrip",
                            },
                            {
                                "key": "companyIssue.companyISIN.company.name",
                                "alias": "Company Name",
                            },
                            {
                                "key": "companyIssue.assignedToClient.name",
                                "value": "",
                                "alias": "Issue Manager",
                            },
                        ],
                        "page": 1,
                        "size": 10,
                        "searchRoleViewConstants": "VIEW_APPLICABLE_SHARE",
                        "filterDateParams": [
                            {
                                "key": "minIssueOpenDate",
                                "condition": "",
                                "alias": "",
                                "value": "",
                            },
                            {
                                "key": "maxIssueCloseDate",
                                "condition": "",
                                "alias": "",
                                "value": "",
                            },
                        ],
                    }
                )

                headers = {
                    "Accept": "application/json, text/plain, */*",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Authorization": self.__auth_token,
                    "Connection": "keep-alive",
                    "Content-Type": "application/json",
                    "Origin": "https://meroshare.cdsc.com.np",
                    "Referer": "https://meroshare.cdsc.com.np/",
                    "Sec-Fetch-Dest": "empty",
                    "Sec-Fetch-Mode": "cors",
                    "Sec-Fetch-Site": "same-site",
                    "Sec-GPC": "1",
                    "User-Agent": USER_AGENT,
                }
                sess.headers.clear()
                sess.headers.update(headers)
                issue_req = sess.post(
                    "https://webbackend.cdsc.com.np/api/meroShare/companyShare/applicableIssue/",
                    data=data,
                )
                assert issue_req.status_code == 200, "Applicable issues request failed!"

                self.__applicable_issues = issue_req.json().get("object")
                logging.info(f"Appplicable Issues Obtained! Account: {self.__name}")
        except Exception as error:
            logging.info(error)
            logging.info("Retrying!")
            raise error

    @retry(stop=stop_after_attempt(5), wait=wait_fixed(3), reraise=True)
    def get_my_details(self):
        try:
            with self.__session as sess:
                headers = {
                    "Accept": "application/json, text/plain, */*",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Authorization": self.__auth_token,
                    "Connection": "keep-alive",
                    "Origin": "https://meroshare.cdsc.com.np",
                    "Referer": "https://meroshare.cdsc.com.np/",
                    "Sec-Fetch-Dest": "empty",
                    "Sec-Fetch-Mode": "cors",
                    "Sec-Fetch-Site": "same-site",
                    "Sec-GPC": "1",
                    "User-Agent": USER_AGENT,
                }
                sess.headers.update(headers)

                details_json = sess.get(
                    f"https://webbackend.cdsc.com.np/api/meroShareView/myDetail/{self.__dmat}"
                ).json()
                self.__dmat = details_json.get("boid")
                self.__account = details_json.get("accountNumber")
                self.__name = details_json.get("name")
                return json.dumps(details_json, indent=2)
        except Exception:
            logging.error(
                f"Details request failed! Retrying ({self.get_details.retry.statistics.get('attempt_number')})!"
            )

    @retry(stop=stop_after_attempt(5), wait=wait_fixed(3), reraise=True)
    def get_application_status(self, share_id: str):
        with self.__session as sess:
            try:
                headers = {
                    "Accept": "application/json, text/plain, */*",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Authorization": self.__auth_token,
                    "Connection": "keep-alive",
                    "Content-Type": "application/json",
                    "Origin": "https://meroshare.cdsc.com.np",
                    "Referer": "https://meroshare.cdsc.com.np/",
                    "Sec-Fetch-Dest": "empty",
                    "Sec-Fetch-Mode": "cors",
                    "Sec-Fetch-Site": "same-site",
                    "Sec-GPC": "1",
                    "User-Agent": USER_AGENT,
                }
                sess.headers.update(headers)
                data = json.dumps(
                    {
                        "filterFieldParams": [
                            {
                                "key": "companyShare.companyIssue.companyISIN.script",
                                "alias": "Scrip",
                            },
                            {
                                "key": "companyShare.companyIssue.companyISIN.company.name",
                                "alias": "Company Name",
                            },
                        ],
                        "page": 1,
                        "size": 200,
                        "searchRoleViewConstants": "VIEW_APPLICANT_FORM_COMPLETE",
                        "filterDateParams": [
                            {
                                "key": "appliedDate",
                                "condition": "",
                                "alias": "",
                                "value": "",
                            },
                            {
                                "key": "appliedDate",
                                "condition": "",
                                "alias": "",
                                "value": "",
                            },
                        ],
                    }
                )

                recent_applied_req = sess.post(
                    "https://webbackend.cdsc.com.np/api/meroShare/applicantForm/active/search/",
                    data=data,
                )

                recent_applied_response_json = recent_applied_req.json().get("object")

                target_issue = None

                for issue in recent_applied_response_json:
                    if issue.get("companyShareId") == int(share_id):
                        target_issue = issue

                if not target_issue:
                    logging.critical(
                        "No issue with provided id found in recent application history!"
                    )
                    raise Exception("Issue not found!")

                headers = {
                    "Accept": "application/json, text/plain, */*",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Authorization": self.__auth_token,
                    "Connection": "keep-alive",
                    "Origin": "https://meroshare.cdsc.com.np",
                    "Referer": "https://meroshare.cdsc.com.np/",
                    "Sec-Fetch-Dest": "empty",
                    "Sec-Fetch-Mode": "cors",
                    "Sec-Fetch-Site": "same-site",
                    "Sec-GPC": "1",
                    "User-Agent": USER_AGENT,
                }
                sess.headers.update(headers)

                details_req = sess.get(
                    f"https://webbackend.cdsc.com.np/api/meroShare/applicantForm/report/detail/{target_issue.get('applicantFormId')}",
                )

                details_response_json = details_req.json()
                logging.info(
                    f"Status: {details_response_json.get('meroshareRemark')} for {self.__name}"
                )
                return details_response_json

            except Exception as error:
                logging.warning(
                    f"Application status request failed! Retrying ({self.get_application_status.retry.statistics.get('attempt_number')})"
                )
                logging.exception(error)
                raise error

    def apply(self, share_id: str, quantity: str):
        with self.__session as sess:
            try:
                issue_to_apply = None

                if not self.__applicable_issues:
                    self.get_applicable_issues()

                for issue in self.__applicable_issues:
                    if str(issue.get("companyShareId")) == share_id:
                        issue_to_apply = issue

                if not issue_to_apply:
                    logging.warning(
                        "Provided ID doesn't match any of the applicable issues!"
                    )
                    raise Exception("No matching applicable issues!")

                if issue_to_apply.get("action"):
                    status = issue_to_apply.get("action")
                    logging.warning("Couldn't apply for issue!")
                    logging.warning(f"Issue Status: {status}")
                    raise Exception("Issue has been already applied!")

                headers = {
                    "Accept": "application/json, text/plain, */*",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Authorization": self.__auth_token,
                    "Connection": "keep-alive",
                    "Content-Type": "application/json",
                    "Origin": "https://meroshare.cdsc.com.np",
                    "Referer": "https://meroshare.cdsc.com.np/",
                    "Sec-Fetch-Dest": "empty",
                    "Sec-Fetch-Mode": "cors",
                    "Sec-Fetch-Site": "same-site",
                    "Sec-GPC": "1",
                    "User-Agent": USER_AGENT,
                }

                sess.headers.update(headers)
                bank_req = sess.get(
                    "https://webbackend.cdsc.com.np/api/meroShare/bank/",
                )
                bank_id = bank_req.json()[0].get("id")

                bank_specific_req = sess.get(
                    f"https://webbackend.cdsc.com.np/api/meroShare/bank/{bank_id}"
                )

                bank_specific_response_json = bank_specific_req.json()

                branch_id = bank_specific_response_json.get("accountBranchId")
                account_number = bank_specific_response_json.get("accountNumber")
                customer_id = bank_specific_response_json.get("id")

                data = json.dumps(
                    {
                        "demat": self.__dmat,
                        "boid": self.__dmat[-8:],
                        "accountNumber": account_number,
                        "customerId": customer_id,
                        "accountBranchId": branch_id,
                        "appliedKitta": quantity,
                        "crnNumber": self.__crn,
                        "transactionPIN": self.__pin,
                        "companyShareId": share_id,
                        "bankId": bank_id,
                    }
                )

            except Exception as error:
                logging.critical("Apply failed!")
                logging.critical(error)
                raise error

            apply_req = sess.post(
                "https://webbackend.cdsc.com.np/api/meroShare/applicantForm/share/apply",
                data=data,
            )

            if apply_req.status_code != 201:
                logging.warning("Apply failed!")
                logging.warning(apply_req.content)
                logging.warning(apply_req.status_code)

            logging.info(f"Sucessfully applied! Account: {self.__name}")

    def check_result(self, company_id: str):
        return MeroShare.check_result_with_dmat(company_id, self.__dmat)

    def get_edis_history(self):
        try:
            with self.__session as sess:
                headers = {
                    "Accept": "application/json, text/plain, */*",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Authorization": self.__auth_token,
                    "Connection": "keep-alive",
                    "Origin": "https://meroshare.cdsc.com.np",
                    "Referer": "https://meroshare.cdsc.com.np/",
                    "Sec-Fetch-Dest": "empty",
                    "Sec-Fetch-Mode": "cors",
                    "Sec-Fetch-Site": "same-site",
                    "Sec-GPC": "1",
                    "User-Agent": USER_AGENT,
                }
                sess.headers.update(headers)
                data = json.dumps(
                    {
                        "filterFieldParams": [
                            {
                                "key": "requestStatus.name",
                                "value": "",
                                "alias": "Status",
                            },
                            {
                                "key": "contractObligationMap.obligation.settleId",
                                "alias": "Settlement Id",
                            },
                            {
                                "key": "contractObligationMap.obligation.scriptCode",
                                "alias": "Script",
                            },
                            {
                                "key": "contractObligationMap.obligation.sellCmId",
                                "alias": "CM ID",
                                "condition": "': '",
                            },
                        ],
                        "page": 1,
                        "size": 200,
                        "searchRoleViewConstants": "VIEW",
                        "filterDateParams": [
                            {
                                "key": "contractObligationMap.obligation.settleDate",
                                "condition": "",
                                "alias": "",
                                "value": "",
                            },
                            {
                                "key": "contractObligationMap.obligation.settleDate",
                                "condition": "",
                                "alias": "",
                                "value": "",
                            },
                            {
                                "key": "requestedDate",
                                "condition": "",
                                "alias": "",
                                "value": "",
                            },
                            {
                                "key": "requestedDate",
                                "condition": "",
                                "alias": "",
                                "value": "",
                            },
                        ],
                    }
                )

                details_json = sess.post(
                    "https://webbackend.cdsc.com.np/api/EDIS/report/search/",
                    data=data,
                ).json()
                for item in details_json.get("object"):
                    logging.info(
                        f'Script: {item.get("contract").get("obligation").get("scriptCode")}, Status: {item.get("statusName")}, for account: {self.__name}'
                    )
        except Exception:
            logging.error(
                f"Details request failed! Retrying ({self.get_details.retry.statistics.get('attempt_number')})!"
            )

    @staticmethod
    @retry(stop=stop_after_attempt(5), wait=wait_fixed(3), reraise=True)
    def check_result_with_dmat(company_id: str, dmat: str):
        with requests.Session() as sess:
            data = json.dumps({"boid": dmat, "companyShareId": company_id})
            headers = {
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.9",
                "Authorization": "null",
                "Connection": "keep-alive",
                "Content-Type": "application/json",
                "Origin": "https://iporesult.cdsc.com.np",
                "Referer": "https://iporesult.cdsc.com.np/",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
                "Sec-GPC": "1",
                "User-Agent": USER_AGENT,
            }
            sess.headers.update(headers)
            result_req = sess.post(
                "https://iporesult.cdsc.com.np/result/result/check", data=data
            )
            return result_req.json()
