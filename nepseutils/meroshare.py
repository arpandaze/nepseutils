#!/usr/bin/python3
# -*- coding: utf-8 -*-

import logging
import time
from typing import Optional

import requests
from tenacity import retry, stop_after_attempt, wait_fixed

logging.basicConfig(format="%(asctime)s %(message)s", level=logging.INFO)

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36"  # noqa

MS_API_BASE = "https://webbackend.cdsc.com.np/api"

BASE_HEADERS = {
    "User-Agent": USER_AGENT,
    "Connection": "keep-alive",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": "https://meroshare.cdsc.com.np",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
    "Sec-GPC": "1",
}


class MeroShare:
    def __init__(
        self,
        dmat: str,
        password: str,
        pin: int,
        username: Optional[int] = None,
        name: Optional[str] = None,
        dpid: Optional[str] = None,
        crn: Optional[str] = None,
        account: Optional[str] = None,
        capital_id: Optional[int] = None,
        branch_id: Optional[str] = None,
        customer_id: Optional[str] = None,
        bank_id: Optional[str] = None,
        capitals: Optional[dict] = None,
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
        self.__capitals = capitals
        self.__session = requests.Session()
        self.__auth_token = None
        self.__applicable_issues = {}
        self.__branch_id = branch_id
        self.__customer_id = customer_id
        self.__bank_id = bank_id

        self.__load_default_headers()

        if not self.__dpid:
            self.__dpid = self.__dmat[3:8]

        if not self.__username:
            self.__username = self.__dmat[-8:]

        if not self.__capital_id:
            if not self.__capitals:
                self.__capitals = self.get_capital_list()

            self.__capital_id = self.__capitals.get(self.__dpid)

            assert self.__capital_id, "DPID not on capital list!"

        self.get_details()

    def __load_default_headers(self):
        self.__session.headers = BASE_HEADERS

    @staticmethod
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2), reraise=True)
    def get_capital_list() -> dict:
        capitals = {}
        with requests.Session() as sess:
            sess.headers = BASE_HEADERS
            headers = {
                "Authorization": "null",
            }
            sess.headers.update(headers)
            cap_req = sess.get("https://backend.cdsc.com.np/api/meroShare/capital/")
            cap_list = cap_req.json()

            any(
                map(
                    lambda x: capitals.update({x.get("code"): x.get("id")}),
                    cap_list,
                )
            )

        return capitals

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(3), reraise=True)
    def login(self) -> str:
        assert (
            self.__username and self.__password and self.__dpid
        ), "Username, password and DPID required!"

        try:
            with self.__session as sess:
                data = {
                    "clientId": str(self.__capital_id),
                    "username": self.__username,
                    "password": self.__password,
                }

                headers = {
                    "Authorization": "null",
                    "Content-Type": "application/json",
                }
                sess.headers.update(headers)

                login_req = sess.post(f"{MS_API_BASE}/meroShare/auth/", json=data)

                if login_req.status_code != 200:
                    logging.warning(f"Login failed! {login_req.status_code}")
                    raise Exception("Login failed!")

                self.__auth_token = login_req.headers.get("Authorization")

                return self.__auth_token

        except Exception as error:
            logging.info(error)
            logging.error(
                f"Login request failed! Retrying ({self.login.retry.statistics.get('attempt_number')})!"
            )
            raise error

    @retry(stop=stop_after_attempt(5), wait=wait_fixed(3), reraise=True)
    def get_details(self) -> dict:
        if not self.__auth_token:
            self.login()

        with self.__session as sess:
            headers = {
                "Authorization": self.__auth_token,
            }
            sess.headers.update(headers)

            if (not self.__account) or (not self.__crn) or (not self.__name):
                account_details = sess.get(
                    f"{MS_API_BASE}/meroShareView/myDetail/{self.__dmat}"
                ).json()

                if not self.__name:
                    self.__name = account_details.get("name")

                if not self.__account:
                    self.__account = account_details.get("accountNumber")

                if not self.__crn:
                    bank_code = account_details.get("bankCode")
                    bank_req = sess.get(f"{MS_API_BASE}/bankRequest/{bank_code}").json()
                    self.__crn = bank_req.get("crnNumber")

            if not self.__bank_id:
                bank_req = sess.get(
                    f"{MS_API_BASE}/meroShare/bank/",
                )
                self.__bank_id = bank_req.json()[0].get("id")

            if (not self.__branch_id) or (not self.__customer_id):
                bank_specific_req = sess.get(
                    f"{MS_API_BASE}/meroShare/bank/{self.__bank_id}"
                )

                bank_specific_response_json = bank_specific_req.json()

                if not self.__branch_id:
                    self.__branch_id = bank_specific_response_json.get(
                        "accountBranchId"
                    )

                if not self.__customer_id:
                    self.__customer_id = bank_specific_response_json.get("id")

        return {
            "dmat": self.__dmat,
            "name": self.__name,
            "account": self.__account,
            "crn": self.__crn,
            "branch_id": self.__branch_id,
            "customer_id": self.__customer_id,
            "bank_id": self.__bank_id,
            "dpid": self.__dpid,
            "username": self.__username,
            "password": self.__password,
            "pin": str(self.__pin),
            "capital_id": self.__capital_id,
        }

    @retry(stop=stop_after_attempt(5), wait=wait_fixed(3), reraise=True)
    def logout(self) -> bool:
        assert self.__auth_token, "Not logged in!"

        try:
            with self.__session as sess:
                headers = {
                    "Authorization": self.__auth_token,
                }
                sess.headers.update(headers)
                logout_req = sess.get(
                    f"{MS_API_BASE}/meroShare/auth/logout/",
                )

                if logout_req.status_code != 201:
                    logging.warning("Logout failed!")
                    logging.warning(logout_req.content)
                    raise Exception("Logout failed!")

                self.__auth_token = None
                return True

        except Exception as error:
            logging.error(
                f"Logout request failed! Retrying ({self.logout.retry.statistics.get('attempt_number')})!"
            )
            logging.info(error)
            raise error

    @retry(stop=stop_after_attempt(5), wait=wait_fixed(3), reraise=True)
    def get_applicable_issues(self) -> list:
        try:
            with self.__session as sess:
                data = {
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

                headers = {
                    "Authorization": self.__auth_token,
                    "Content-Type": "application/json",
                }
                sess.headers.update(headers)
                issue_req = sess.post(
                    f"{MS_API_BASE}/meroShare/companyShare/applicableIssue/",
                    json=data,
                )
                assert issue_req.status_code == 200, "Applicable issues request failed!"

                self.__applicable_issues = issue_req.json().get("object")
                return self.__applicable_issues

        except Exception as error:
            logging.info(error)
            raise error

    @retry(stop=stop_after_attempt(5), wait=wait_fixed(3), reraise=True)
    def get_application_reports(self) -> list:
        with self.__session as sess:
            self.__load_default_headers()
            headers = {
                "Authorization": self.__auth_token,
                "Content-Type": "application/json",
            }
            sess.headers.update(headers)
            data = {
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

            recent_applied_req = sess.post(
                f"{MS_API_BASE}/meroShare/applicantForm/active/search/",
                json=data,
            )

            return recent_applied_req.json().get("object")

    @retry(stop=stop_after_attempt(5), wait=wait_fixed(3), reraise=True)
    def get_application_status(
        self, form_id: Optional[int] = None, share_id: Optional[int] = None
    ) -> dict:
        with self.__session as sess:
            if not form_id:
                recent_applied_response_json = self.get_application_reports()

                target_issue = None

                for issue in recent_applied_response_json:
                    if issue.get("companyShareId") == share_id:
                        target_issue = issue
                        form_id = target_issue.get("applicantFormId")
                        break

            if not form_id:
                logging.critical(
                    "No issue with provided id found in recent application history!"
                )
                raise Exception("Issue not found!")

            self.__load_default_headers()

            headers = {
                "Authorization": self.__auth_token,
            }
            sess.headers.update(headers)

            details_req = sess.get(
                f"{MS_API_BASE}/meroShare/applicantForm/report/detail/{form_id}",
            )

            details_response_json = details_req.json()

            return details_response_json

    def apply(self, share_id: int, quantity: int) -> dict:
        if not (
            self.__dmat
            and self.__account
            and self.__customer_id
            and self.__branch_id
            and self.__crn
            and self.__pin
            and self.__bank_id
        ):
            self.get_details()

        assert share_id and quantity, "Share ID and quantity must be provided!"

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
                    return {
                        "status": "CREATED",
                        "message": "Issue already applied!",
                    }

                self.__load_default_headers()

                headers = {
                    "Authorization": self.__auth_token,
                    "Content-Type": "application/json",
                    "Pragma": "no-cache",
                    "Cache-Control": "no-cache",
                }

                sess.headers.update(headers)

                data = {
                    "demat": self.__dmat,
                    "boid": self.__dmat[-8:],
                    "accountNumber": self.__account,
                    "customerId": self.__customer_id,
                    "accountBranchId": self.__branch_id,
                    "appliedKitta": str(quantity),
                    "crnNumber": self.__crn,
                    "transactionPIN": self.__pin,
                    "companyShareId": str(share_id),
                    "bankId": self.__bank_id,
                }

            except Exception as error:
                logging.critical(error)
                raise error

            apply_req = sess.post(
                f"{MS_API_BASE}/meroShare/applicantForm/share/apply",
                json=data,
            )

            if apply_req.status_code != 201:
                raise Exception(
                    f"Apply failed! Status code: {apply_req.status_code}, Message: {apply_req.content}"
                )

            return apply_req.json()

    @retry(stop=stop_after_attempt(5), wait=wait_fixed(3), reraise=True)
    def check_result(self, company: str):
        return MeroShare.check_result_with_dmat(company, self.__dmat)

    @retry(stop=stop_after_attempt(5), wait=wait_fixed(3), reraise=True)
    def get_edis_history(self):
        try:
            with self.__session as sess:
                headers = {
                    "Authorization": self.__auth_token,
                }
                sess.headers.update(headers)
                data = {
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

                details_json = sess.post(
                    f"{MS_API_BASE}/EDIS/report/search/",
                    json=data,
                ).json()

                for item in details_json.get("object"):
                    logging.info(
                        f'Script: {item.get("contract").get("obligation").get("scriptCode")}, Status: {item.get("statusName")}, for account: {self.__name}'
                    )

                return details_json.get("object")
        except Exception:
            logging.error(
                f"Details request failed! Retrying ({self.get_details.retry.statistics.get('attempt_number')})!"
            )

    @staticmethod
    @retry(stop=stop_after_attempt(5), wait=wait_fixed(3), reraise=True)
    def get_result_company_list() -> list:
        with requests.Session() as sess:
            headers = {
                "Connection": "keep-alive",
                "Pragma": "no-cache",
                "Cache-Control": "no-cache",
                "Accept": "application/json, text/plain, */*",
                "Authorization": "null",
                "User-Agent": USER_AGENT,
                "Sec-GPC": "1",
                "Sec-Fetch-Site": "same-origin",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Dest": "empty",
                "Referer": "https://iporesult.cdsc.com.np/",
                "Accept-Language": "en-US,en;q=0.9",
            }

            response = sess.get(
                "https://iporesult.cdsc.com.np/result/companyShares/fileUploaded",
                headers=headers,
            )

            assert response.status_code == 200
            result_company_list = response.json()

            return result_company_list

    @staticmethod
    @retry(stop=stop_after_attempt(5), wait=wait_fixed(3), reraise=True)
    def check_result_with_dmat(
        dmat,
        azcaptcha_token,
        company=None,
        company_id=None,
    ) -> dict:
        with requests.Session() as sess:
            while True:
                unseparated_resp = MeroShare.get_result_company_list()
                captcha_base64 = (
                    unseparated_resp.get("body").get("captchaData").get("captcha")
                )
                identifier = (
                    unseparated_resp.get("body")
                    .get("captchaData")
                    .get("captchaIdentifier")
                )
                result_company_list = unseparated_resp.get("body").get(
                    "companyShareList"
                )

                if not company_id:
                    company_id = [
                        item.get("id")
                        for item in result_company_list
                        if item.get("scrip").lower() == company.lower()
                    ]

                    company_id = company_id[0] if company_id else None

                if not company_id:
                    logging.error(msg=f"Result of {company} not found!")
                    raise Exception(f"Result of {company} not found!")

                url = "http://azcaptcha.com/in.php"

                payload = {
                    "key": azcaptcha_token,
                    "method": "base64",
                    "body": captcha_base64,
                }

                response = requests.post(url, data=payload)

                assert response.text[:3] == "OK|"

                cap_resp_id = response.text[3:]

                url = "http://azcaptcha.com/res.php"

                payload = {
                    "key": azcaptcha_token,
                    "id": cap_resp_id,
                    "action": "get",
                }

                tries = 0
                while True:
                    time.sleep(1)
                    response = requests.get(url, params=payload)
                    if response.text[:3] == "OK|" or tries > 3:
                        break
                    tries += 1

                captcha = response.text[3:]

                data = {
                    "boid": dmat,
                    "companyShareId": str(company_id),
                    "captchaIdentifier": identifier,
                    "userCaptcha": captcha or "34256",
                }

                headers = {
                    "Connection": "keep-alive",
                    "Pragma": "no-cache",
                    "Cache-Control": "no-cache",
                    "Accept": "application/json, text/plain, */*",
                    "Authorization": "null",
                    "User-Agent": USER_AGENT,
                    "Content-Type": "application/json",
                    "Sec-GPC": "1",
                    "Origin": "https://iporesult.cdsc.com.np",
                    "Sec-Fetch-Site": "same-origin",
                    "Sec-Fetch-Mode": "cors",
                    "Sec-Fetch-Dest": "empty",
                    "Referer": "https://iporesult.cdsc.com.np/",
                    "Accept-Language": "en-US,en;q=0.9",
                }
                sess.headers.update(headers)
                result_req = sess.post(
                    "https://iporesult.cdsc.com.np/result/result/check", json=data
                )
                logging.info(f"Result fetched for dmat {dmat}, {result_req.json()}")

                if "Invalid Captcha" in result_req.json()["message"]:
                    continue
                else:
                    return result_req.json()
