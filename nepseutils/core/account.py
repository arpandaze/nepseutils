import logging
from collections.abc import Callable
from typing import List, Optional

import requests
from tenacity import retry
from tenacity.retry import retry_if_exception_type
from tenacity.stop import stop_after_attempt
from tenacity.wait import wait_fixed

from nepseutils.constants import MS_API_BASE
from nepseutils.utils.decorators import autosave, login_required

from .errors import GlobalError, LocalException
from .issue import Issue
from .portfolio import Portfolio, PortfolioEntry


class Account:
    save: Callable
    dmat: str
    password: str
    pin: int
    crn: Optional[str]
    username: Optional[int] = None
    name: Optional[str] = None
    dpid: Optional[str] = None
    account: Optional[str] = None
    capital_id: Optional[int] = None
    branch_id: Optional[str] = None
    customer_id: Optional[str] = None
    bank_id: Optional[str] = None

    auth_token: Optional[str] = None

    portfolio: Portfolio
    issues: List[Issue]

    tag: Optional[str]

    save: Callable = lambda: None

    def __init__(
        self,
        dmat: str,
        password: str,
        pin: int,
        capital_id: int,
        crn: Optional[str],
        username: Optional[int] = None,
        name: Optional[str] = None,
        dpid: Optional[str] = None,
        account: Optional[str] = None,
        branch_id: Optional[str] = None,
        customer_id: Optional[str] = None,
        bank_id: Optional[str] = None,
        portfolio: Optional[Portfolio] = None,
        issues: Optional[List[Issue]] = None,
        tag: Optional[str] = None,
        save: Optional[Callable] = None,
        __auth_token: Optional[str] = None,
        send_telegram_message: Callable = lambda *args, **kwargs: None,
    ):
        self.send_telegram_message = send_telegram_message
        self.dmat = dmat
        self.password = password
        self.pin = pin
        self.username = username
        self.name = name
        self.dpid = dpid
        self.crn = crn
        self.account = account
        self.capital_id = capital_id
        self.branch_id = branch_id
        self.customer_id = customer_id
        self.bank_id = bank_id

        self.portfolio = portfolio or Portfolio([], 0, 0, 0)
        self.issues = issues or []

        self.tag = tag

        if save:
            self.save = save

        self.__session = requests.Session()
        self.auth_token = __auth_token

        if not self.dpid:
            self.dpid = dmat[3:8]

        if not self.username:
            self.username = int(dmat[-8:])

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(2),
        reraise=True,
        retry=retry_if_exception_type(LocalException),
    )
    def login(self) -> str:
        assert (
            self.username and self.password and self.dpid
        ), "Username, password and DPID required!"

        with self.__session as sess:
            data = {
                "clientId": str(self.capital_id),
                "username": self.username,
                "password": self.password,
            }

            headers = {
                "Authorization": "null",
                "Content-Type": "application/json",
            }
            sess.headers.update(headers)

            login_req = sess.post(f"{MS_API_BASE}/meroShare/auth/", json=data)

            response_data = login_req.json()

            if login_req.status_code != 200:
                logging.error(
                    f"Login failed for user: {self.name}! \n Status: {login_req.status_code} \n {response_data}"
                )
                raise LocalException(f"Login failed for user: {self.name}!")

            if response_data.get("passwordExpired"):
                logging.error(f"Password has expired for user: {self.name}")
                raise LocalException(f"Password has expired for user: {self.name}")

            if response_data.get("accountExpired"):
                logging.error(f"Account has expired for user: {self.name}")
                raise LocalException(f"Account has expired for user: {self.name}")

            if response_data.get("dematExpired"):
                logging.error(f"DMAT has expired for user: {self.name}")
                raise LocalException(f"DMAT has expired for user: {self.name}")

            self.auth_token = login_req.headers.get("Authorization")
            self.__session.headers.update({"Authorization": self.auth_token})  # type: ignore

            return self.auth_token  # type: ignore

    @login_required
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(2),
        reraise=True,
        retry=retry_if_exception_type(LocalException),
    )
    def get_details(self) -> dict:
        logging.info(f"Getting details for user: {self.name}")
        with self.__session as sess:
            if (not self.account) or (not self.name):
                account_details = sess.get(
                    f"{MS_API_BASE}/meroShareView/myDetail/{self.dmat}"
                )

                if account_details.status_code != 200:
                    logging.warning(
                        f"Failed to get account details!\n Status: {account_details.status_code}\n {account_details.json()}"
                    )
                    raise LocalException(
                        f"Failed to get account details for user: {self.name}!"
                    )

                account_details = account_details.json()

                if not self.name:
                    self.name = account_details.get("name")

                if not self.account:
                    bank_code = account_details.get("bankCode")
                    bank_req = sess.get(f"{MS_API_BASE}/bankRequest/{bank_code}")

                    if bank_req.status_code != 200:
                        logging.warning(
                            f"Failed to get bank details!\n Status: {bank_req.status_code}\n {bank_req.json()}"
                        )
                        raise LocalException(
                            f"Failed to get bank details for user: {self.name}!"
                        )

                    bank_req = bank_req.json()

                    self.account = bank_req.get("accountNumber")

            if not self.bank_id:
                bank_req = sess.get(
                    f"{MS_API_BASE}/meroShare/bank/",
                )

                if bank_req.status_code != 200:
                    logging.warning(
                        f"Failed to get bank details for account {self.name}!\n Status: {bank_req.status_code}\n {bank_req.json()}"
                    )
                    raise LocalException(
                        f"Failed to get bank details for user: {self.name}!"
                    )

                bank_req = bank_req.json()

                self.bank_id = bank_req[0].get("id")

            if (not self.branch_id) or (not self.customer_id):
                bank_specific_req = sess.get(
                    f"{MS_API_BASE}/meroShare/bank/{self.bank_id}"
                )

                if bank_specific_req.status_code != 200:
                    logging.warning(
                        f"Failed to get bank specific details for account {self.name}!\n Status: {bank_specific_req.status_code}\n {bank_specific_req.json()}"
                    )
                    raise LocalException(
                        f"Failed to get bank specific details for user: {self.name}!"
                    )

                bank_specific_response_json = bank_specific_req.json()

                if not self.branch_id:
                    self.branch_id = bank_specific_response_json.get("accountBranchId")

                if not self.customer_id:
                    self.customer_id = bank_specific_response_json.get("id")

        return {
            "dmat": self.dmat,
            "name": self.name,
            "account": self.account,
            "crn": self.crn,
            "branch_id": self.branch_id,
            "customer_id": self.customer_id,
            "bank_id": self.bank_id,
            "dpid": self.dpid,
            "username": self.username,
            "password": self.password,
            "pin": str(self.pin),
            "capital_id": self.capital_id,
        }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(2),
        reraise=True,
        retry=retry_if_exception_type(LocalException),
    )
    def logout(self) -> bool:
        if not self.auth_token:
            return True

        with self.__session as sess:
            logout_req = sess.get(
                f"{MS_API_BASE}/meroShare/auth/logout/",
            )

            if logout_req.status_code != 201:
                logging.warning(
                    f"Logout failed for user : {self.name}\n Status: {logout_req.status_code}\n {logout_req.content}"
                )
                raise LocalException(f"Logout failed for user: {self.name}!")

            self.auth_token = None
            return True

    @autosave
    @login_required
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(2),
        reraise=True,
        retry=retry_if_exception_type(LocalException),
    )
    def fetch_applicable_issues(self) -> list:
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
                "Content-Type": "application/json",
            }
            sess.headers.update(headers)

            logging.info(f"Fetching applicable issues for user: {self.name}")

            issue_req = sess.post(
                f"{MS_API_BASE}/meroShare/companyShare/applicableIssue/",
                json=data,
            )

            if issue_req.status_code != 200:
                logging.warning(
                    f"Applicable issues request failed for user: {self.name}\n {issue_req.content}"
                )
                raise LocalException(
                    f"Applicable issues request failed for user: {self.name}!"
                )

            return issue_req.json().get("object")

    @autosave
    @login_required
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(2),
        reraise=True,
        retry=retry_if_exception_type(LocalException),
    )
    def fetch_application_reports(self, active=True) -> list:
        with self.__session as sess:
            headers = {
                "Content-Type": "application/json",
            }
            sess.headers.update(headers)

            if active:
                search_role_view_constants = "VIEW_APPLICANT_FORM_COMPLETE"
                endpoint = "meroShare/applicantForm/active/search/"
            else:
                search_role_view_constants = "VIEW"
                endpoint = "meroShare/migrated/applicantForm/search/"

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
                "searchRoleViewConstants": search_role_view_constants,
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

            logging.info(f"Fetching application reports for user: {self.name}")
            recent_applied_req = sess.post(
                f"{MS_API_BASE}/{endpoint}",
                json=data,
            )

            if recent_applied_req.status_code != 200:
                logging.warning(
                    f"Recent application list request failed for user: {self.name}\n {recent_applied_req.content}"
                )
                raise LocalException(
                    f"Recent application list request failed for user: {self.name}!"
                )

            return recent_applied_req.json().get("object")

    @autosave
    @login_required
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(2),
        reraise=True,
        retry=retry_if_exception_type(LocalException),
    )
    def fetch_applied_issues(self, refetch=False) -> None:
        application_reports = self.fetch_application_reports()

        if refetch:
            self.issues = []

        existing_issues = [issue.symbol for issue in self.issues]

        for report in application_reports:
            if report.get("scrip") in existing_issues:
                continue

            self.issues.append(
                Issue(
                    name=report.get("companyName"),
                    symbol=report.get("scrip"),
                    status=report.get("statusName"),
                    share_type=report.get("shareTypeName"),
                    company_share_id=report.get("companyShareId"),
                    applicant_form_id=report.get("applicantFormId"),
                    old=False,
                )
            )

        application_reports = self.fetch_application_reports(active=False)

        for report in application_reports:
            found = False

            # Skip if already exists and mark as old
            for issue in self.issues:
                if issue.symbol == report.get("scrip"):
                    if issue.old == False:
                        issue.old = True
                    found = True
                    break

            if found:
                continue

            self.issues.append(
                Issue(
                    name=report.get("companyName"),
                    symbol=report.get("scrip"),
                    status=report.get("statusName"),
                    share_type=report.get("shareTypeName"),
                    company_share_id=report.get("companyShareId"),
                    applicant_form_id=report.get("applicantFormId"),
                    old=True,
                )
            )

        self.save()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(2),
        reraise=True,
        retry=retry_if_exception_type(LocalException),
    )
    def fetch_applied_issues_status(self, company_id: str | None = None) -> None:
        if company_id is None:
            issues = self.issues
        else:
            issues = [
                issue for issue in self.issues if issue.company_share_id == company_id
            ]

        for issue in issues:
            # Skip if allotion status already fetched
            if issue.alloted != None:
                continue

            with self.__session as sess:
                if not issue.old:
                    logging.info(
                        f"Fetching application status of issue {issue.symbol} for user: {self.name}"
                    )
                    details_req = sess.get(
                        f"{MS_API_BASE}/meroShare/applicantForm/report/detail/{issue.applicant_form_id}",
                    )
                else:
                    logging.info(
                        f"Fetching application status of issue {issue.symbol} (old) for user: {self.name}"
                    )
                    details_req = sess.get(
                        f"{MS_API_BASE}/meroShare/migrated/applicantForm/report/{issue.applicant_form_id}",
                    )

                if details_req.status_code != 200:
                    logging.warning(
                        f"Failed to fetch application status of issue {issue.symbol} for user: {self.name}\n {details_req.content} \n {MS_API_BASE}/migrated/applicantForm/report/{issue.applicant_form_id}"
                    )
                    continue

                details = details_req.json()

                if details.get("statusName") == "Alloted":
                    logging.info(
                        f"Application status of issue {issue.symbol} is ALLOTED for user: {self.name}"
                    )
                    issue.alloted = True
                elif details.get("statusName") == "Not Alloted":
                    logging.info(
                        f"Application status of issue {issue.symbol} is NOT Alloted for user: {self.name}"
                    )
                    issue.alloted = False
                elif details.get("statusName") == "Rejected":
                    logging.warn(
                        f"Application status of issue {issue.symbol} is REJECTED for user: {self.name}"
                    )
                    issue.alloted = False
                else:
                    issue.alloted = None

                issue.alloted_quantity = (
                    details.get("receivedKitta") if issue.alloted else 0
                )

                issue.applied_date = details.get("appliedDate")
                issue.applied_quantity = details.get("appliedKitta")
                issue.applied_amount = details.get("amount")
                issue.block_amount_status = details.get("meroshareRemark")
                self.save()

    @login_required
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(2),
        reraise=True,
        retry=retry_if_exception_type(LocalException),
    )
    def fetch_application_status(
        self, form_id: Optional[int] = None, share_id: Optional[int] = None
    ) -> dict:
        with self.__session as sess:
            if not form_id:
                recent_applied_response_json = self.fetch_application_reports()

                target_issue = None

                for issue in recent_applied_response_json:
                    if issue.get("companyShareId") == share_id:
                        target_issue = issue
                        form_id = target_issue.get("applicantFormId")
                        break

            if not form_id:
                logging.critical(
                    f"No issue with provided id found in recent application history for user: {self.name}"
                )
                raise LocalException("Issue not found!")

            details_req = sess.get(
                f"{MS_API_BASE}/meroShare/applicantForm/report/detail/{form_id}",
            )

            if details_req.status_code != 200:
                logging.warning(
                    f"Application status request failed for user: {self.name}\n {details_req.content}"
                )
                raise LocalException(
                    f"Application status request failed for user: {self.name}!"
                )

            details_response_json = details_req.json()

            return details_response_json

    @login_required
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(2),
        reraise=True,
        retry=retry_if_exception_type(LocalException),
    )
    def fetch_portfolio(self) -> Portfolio:
        with self.__session as sess:
            portfolio_req = sess.post(
                f"{MS_API_BASE}/meroShareView/myPortfolio/",
                json={
                    "sortBy": "script",
                    "demat": [self.dmat],
                    "clientCode": self.dpid,
                    "page": 1,
                    "size": 200,
                    "sortAsc": True,
                },
            )

            if portfolio_req.status_code != 200:
                logging.warning(
                    f"Portfolio request failed for user: {self.name}\n {portfolio_req.content}"
                )
                raise LocalException(f"Portfolio request failed for user: {self.name}!")

            portfolio_response_json = portfolio_req.json()

            entries: List[PortfolioEntry] = []

            for entry in portfolio_response_json.get("meroShareMyPortfolio"):
                entries.append(
                    PortfolioEntry(
                        current_balance=float(entry.get("currentBalance")),
                        last_transaction_price=float(entry.get("lastTransactionPrice")),
                        previous_closing_price=float(entry.get("previousClosingPrice")),
                        script=entry.get("script"),
                        script_desc=entry.get("scriptDesc"),
                        value_as_of_last_transaction_price=float(
                            entry.get("valueAsOfLastTransactionPrice")
                        ),
                        value_as_of_previous_closing_price=float(
                            entry.get("valueAsOfPreviousClosingPrice")
                        ),
                    )
                )

            new_portfolio = Portfolio(
                entries=entries,
                total_items=portfolio_response_json.get("totalItems"),
                total_value_as_of_last_transaction_price=float(
                    portfolio_response_json.get("totalValueAsOfLastTransactionPrice")
                ),
                total_value_as_of_previous_closing_price=float(
                    portfolio_response_json.get("totalValueAsOfPreviousClosingPrice")
                ),
            )

            self.portfolio = new_portfolio
            return new_portfolio

    @login_required
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(2),
        reraise=True,
        retry=retry_if_exception_type(LocalException),
    )
    def find_min_apply_unit(self, company_share_id) -> int:
        with self.__session as sess:
            min_apply_unit_req = sess.get(
                f"{MS_API_BASE}/meroShare/active/{company_share_id}",
            )

            if min_apply_unit_req.status_code != 200:
                logging.warning(
                    f"Min apply unit request failed for user: {self.name}\n {min_apply_unit_req.content}"
                )
                raise LocalException(
                    f"Min apply unit request failed for user: {self.name}!"
                )

            min_apply_unit_response_json = min_apply_unit_req.json()

            return int(min_apply_unit_response_json.get("minUnit"))

    @login_required
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(2),
        reraise=True,
        retry=retry_if_exception_type(LocalException),
    )
    def fetch_edis_history(self):
        with self.__session as sess:
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

            details_response = sess.post(
                f"{MS_API_BASE}/EDIS/report/search/",
                json=data,
            )

            if details_response.status_code != 200:
                logging.warning(
                    f"Apply failed! Status code: {details_response.status_code}, Message: {details_response.content}"
                )
                raise LocalException(f"Apply failed for user {self.name}!")

            details_json = details_response.json()

            for item in details_json.get("object"):
                logging.info(
                    f'Script: {item.get("contract").get("obligation").get("scriptCode")}, Status: {item.get("statusName")}, for account: {self.name}'
                )

            return details_json.get("object")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(2),
        reraise=True,
        retry=retry_if_exception_type(LocalException),
    )
    def apply(self, share_id: int, quantity: int) -> dict:
        if not (
            self.dmat
            and self.account
            and self.customer_id
            and self.branch_id
            and self.crn
            and self.pin
            and self.bank_id
        ):
            self.get_details()

        assert share_id and quantity, "Share ID and quantity must be provided!"

        with self.__session as sess:
            issue_to_apply = None

            logging.info(
                f"Applying {quantity} units of {share_id} for user: {self.name}"
            )

            applicable_issue = self.fetch_applicable_issues()

            for issue in applicable_issue:
                if issue.get("companyShareId") == share_id:
                    issue_to_apply = issue

            if not issue_to_apply:
                logging.warning(
                    "Provided ID doesn't match any of the applicable issues!"
                )
                raise GlobalError("No matching applicable issues!")

            if issue_to_apply.get("action"):
                logging.warning(
                    f"Issue already applied! {issue_to_apply} for user: {self.name}"
                )
                return {
                    "status": "CREATED",
                    "message": "Issue already applied!",
                }

            headers = {
                "Content-Type": "application/json",
                "Pragma": "no-cache",
                "Cache-Control": "no-cache",
            }

            sess.headers.update(headers)

            data = {
                "demat": self.dmat,
                "boid": self.dmat[-8:],
                "accountNumber": self.account,
                "customerId": self.customer_id,
                "accountBranchId": self.branch_id,
                "appliedKitta": str(quantity),
                "crnNumber": self.crn,
                "transactionPIN": self.pin,
                "companyShareId": str(share_id),
                "bankId": self.bank_id,
            }

            apply_req = sess.post(
                f"{MS_API_BASE}/meroShare/applicantForm/share/apply",
                json=data,
            )

            if apply_req.status_code != 201:
                logging.warning(
                    f"Apply failed! Status code: {apply_req.status_code}, Message: {apply_req.content}"
                )
                raise LocalException(f"Apply failed for user {self.name}!")

            logging.info(
                f"Applied {quantity} kitta of {issue_to_apply.get('companyName')} for {self.name}!"
            )

            self.fetch_applied_issues()

            return apply_req.json()

    def to_json(self):
        return {
            "dmat": self.dmat,
            "password": self.password,
            "pin": self.pin,
            "username": self.username,
            "name": self.name,
            "dpid": self.dpid,
            "crn": self.crn,
            "account": self.account,
            "capital_id": self.capital_id,
            "branch_id": self.branch_id,
            "customer_id": self.customer_id,
            "bank_id": self.bank_id,
            "portfolio": self.portfolio.to_json(),
            "issues": [issue.to_json() for issue in self.issues or []],
            "tag": self.tag,
        }

    @staticmethod
    def from_json(json: dict, save: Callable = lambda: None):
        return Account(
            save=save,
            dmat=str(json.get("dmat")),
            password=str(json.get("password")),
            pin=int(json.get("pin") or 0),
            username=json.get("username"),
            name=json.get("name"),
            dpid=json.get("dpid"),
            crn=json.get("crn"),
            account=json.get("account"),
            capital_id=int(json.get("capital_id") or 0),
            branch_id=json.get("branch_id"),
            customer_id=json.get("customer_id"),
            bank_id=json.get("bank_id"),
            portfolio=Portfolio.from_json(json.get("portfolio") or {}),
            issues=[Issue.from_json(issue) for issue in json.get("issues") or []],
            tag=json.get("tag"),
        )
