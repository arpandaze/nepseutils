import base64
import json
from getpass import getpass
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from nepseutils.core.account import Account
from nepseutils.core.errors import LocalException
from nepseutils.core.meroshare import MeroShare


def pre_versioning_to_current():
    old_config_path = Path.home() / ".nepseutils" / "data.db"

    if not old_config_path.exists():
        return

    print("Old config file found. Converting to new format.")

    password = getpass(f"Enter password for old config file: ")

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=password.encode("UTF-8"),
        iterations=100000,
    )

    key = base64.urlsafe_b64encode(kdf.derive(password.encode("UTF-8")))
    fernet = Fernet(key)

    with open(old_config_path, "r") as f:
        encrypted_data = f.read()
        try:
            data = json.loads(fernet.decrypt(encrypted_data).decode("UTF-8"))
        except InvalidToken:
            print("Password Incorrect!")
            exit()

    ms = MeroShare.new(password)

    for account in data["accounts"]:
        dmat = account["dmat"]
        password = account["password"]
        pin = account["pin"]
        crn = account["crn"]
        capital_id = account["capital_id"]
        ms.accounts.append(Account(dmat, password, int(pin), int(capital_id), crn))

    ms.save_data()

    for account in ms.accounts:
        try:
            account.get_details()
        except LocalException as _:
            pass

    ms.save_data()
    print(f"New config has been created. Run nepseutils again to use it.")
    exit()
