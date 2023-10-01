import base64
import json
import logging
import os
from pathlib import Path
from typing import List, Optional

import requests
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from tenacity import retry
from tenacity.stop import stop_after_attempt
from tenacity.wait import wait_fixed

from nepseutils.constants import BASE_HEADERS, MS_API_BASE
from nepseutils.core.account import Account
from nepseutils.core.errors import LocalException
from nepseutils.utils.logging import TelegramLoggingHandler
from nepseutils.version import __version__

DEFAULT_CONFIG_FILENAME = "config.json"


class MeroShare:
    _accounts: List[Account]
    tag_selections: List[str]
    password: str
    capitals: dict
    config_version: str
    logging_level: int
    telegram_bot_token: str | None
    telegram_chat_id: str | None

    config_path: Path
    fernet: Fernet

    logging_handler: TelegramLoggingHandler

    @property
    def accounts(self) -> List[Account]:
        if self.tag_selections != []:
            return [
                account
                for account in self._accounts
                if account.tag in self.tag_selections
            ]
        else:
            return self._accounts

    def __init__(
        self,
        fernet: Fernet,
        accounts: Optional[List[Account]],
        capitals: Optional[dict],
        config_version: str = __version__,
        logging_level: int = logging.ERROR,
        config_path: Optional[Path] = None,
        telegram_bot_token: str | None = None,
        telegram_chat_id: str | None = None,
    ):
        self.logging_level = logging_level
        self.config_version = config_version

        self.telegram_bot_token = telegram_bot_token
        self.telegram_chat_id = telegram_chat_id

        if telegram_bot_token and telegram_chat_id:
            self.logging_handler = TelegramLoggingHandler(
                telegram_bot_token, telegram_chat_id
            )
            logging.basicConfig(
                format="%(asctime)s %(message)s",
                level=self.logging_level,
                force=True,
                handlers=[self.logging_handler],
            )
        else:
            if not os.path.exists(MeroShare.default_config_directory()):
                os.makedirs(MeroShare.default_config_directory())
            logging.basicConfig(
                filename=f"{MeroShare.default_config_directory()}/nepseutils.log",
                filemode="a",
                format="%(asctime)s %(message)s",
                level=self.logging_level,
                force=True,
            )

        self._accounts = accounts or []
        self.tag_selections = []

        if config_path:
            self.config_path = MeroShare.default_config_path()

        if fernet:
            self.fernet = fernet

        if capitals:
            self.capitals = capitals
        else:
            self.update_capital_list()

    @staticmethod
    def fernet_init(password):
        logging.info("Initializing Fernet!")
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=password.encode("UTF-8"),
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode("UTF-8")))
        return Fernet(key)

    @staticmethod
    def default_config_directory() -> Path:
        if os.name == "nt":
            return Path(os.getenv("APPDATA"), "nepseutils")
        else:
            return Path(os.getenv("HOME") or "~", ".config", "nepseutils")

    @staticmethod
    def default_config_path() -> Path:
        if os.name == "nt":
            return Path(
                os.path.join(
                    os.getenv("APPDATA"),
                    "nepseutils",
                    DEFAULT_CONFIG_FILENAME,
                )
            )
        else:
            return Path(
                os.path.join(
                    os.getenv("HOME") or "~",
                    ".config",
                    "nepseutils",
                    DEFAULT_CONFIG_FILENAME,
                )
            )

    @staticmethod
    def new(password: str, path: Optional[Path] = None):
        path = path or MeroShare.default_config_path()

        if path.exists():
            logging.error("Config file already exists!")
            exit()

        fernet = MeroShare.fernet_init(password)

        ms = MeroShare(
            fernet=fernet,
            accounts=[],
            capitals={},
            logging_level=logging.ERROR,
            config_version=__version__,
            config_path=path,
        )

        ms.save_data()

        try:
            ms.update_capital_list()
        except LocalException:
            logging.error("Failed to update capital list while creating new datafile!")
            exit()

        return ms

    @staticmethod
    def load(password: str, path: Optional[Path] = None):
        path = path or MeroShare.default_config_path()

        with open(path, "r") as config_file:
            config = json.load(config_file)

            config_version = config.get("config_version")
            logging_level = config.get("logging_level")
            telegram_bot_token = config.get("telegram_bot_token")
            telegram_chat_id = config.get("telegram_chat_id")
            capitals = config.get("capitals")

            fernet = MeroShare.fernet_init(password)

            encrypted_bytes = base64.b64decode(config.get("data"))
            decrypted_data = fernet.decrypt(encrypted_bytes)
            accounts = json.loads(decrypted_data)

            ms = MeroShare(
                fernet=fernet,
                accounts=[],
                capitals=capitals,
                config_version=config_version,
                logging_level=logging_level,
                config_path=path,
                telegram_bot_token=telegram_bot_token,
                telegram_chat_id=telegram_chat_id,
            )
            accounts = [
                Account.from_json(account, ms.save_data) for account in accounts
            ]

            ms._accounts = accounts

            return ms

    def save_data(self):
        logging.info("Saving data!")
        with open(self.config_path, "w") as data_file:
            data = [account.to_json() for account in self.accounts]
            encrypted_data = self.fernet.encrypt(json.dumps(data).encode())

            data_file.write(
                json.dumps(
                    {
                        "config_version": self.config_version,
                        "logging_level": self.logging_level,
                        "telegram_bot_token": self.telegram_bot_token,
                        "telegram_chat_id": self.telegram_chat_id,
                        "capitals": self.capitals,
                        "data": base64.b64encode(encrypted_data).decode(),
                    }
                )
            )

    def create_new_data(self, password):
        logging.info("Did not find any data file, creating new data!")
        self.fernet_init(password)
        self.update_capital_list()

    @property
    def default_account(self) -> Account:
        if not self.accounts:
            logging.error(
                "Cannot choose default account since no account has been added!."
            )
            raise ValueError("No accounts found.")

        return self.accounts[0]

    def update_capital_list(self) -> dict:
        capitals = self.fetch_capital_list()

        self.capitals = capitals

        self.save_data()

        logging.info("Capital list updated!")
        return capitals

    @staticmethod
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2), reraise=True)
    def fetch_capital_list() -> dict:
        capitals = {}
        with requests.Session() as sess:
            sess.headers = BASE_HEADERS  # type: ignore
            headers = {
                "Authorization": "null",
            }
            sess.headers.update(headers)

            logging.info("Fetching capital list!")
            cap_req = sess.get(f"{MS_API_BASE}/meroShare/capital/")

            if cap_req.status_code != 200:
                raise LocalException("Failed to fetch capital list!")

            cap_list = cap_req.json()

            for cap in cap_list:
                capitals.update({cap.get("code"): cap.get("id")})

        return capitals

    @staticmethod
    # @retry(stop=stop_after_attempt(5), wait=wait_fixed(3), reraise=True)
    def fetch_result_company_list() -> list:
        with requests.Session() as sess:
            sess.headers = BASE_HEADERS  # type: ignore

            requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)  # type: ignore

            response = sess.get(
                "https://iporesult.cdsc.com.np/result/companyShares/fileUploaded",
                verify=False,
            )

            if response.status_code != 200:
                raise LocalException("Failed to fetch result company list!")

            result_company_list = response.json()

            return result_company_list.get("body").get("companyShareList")
