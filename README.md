# NEPSE Utils
Collection of scripts to interact with NEPSE related sites.
## Installation
`pip install nepseutils`


### Class: MeroShare
#### Constructor \_\_init__()
- `name` Your name
- `dpid` Depository Participants
- `username` MeroShare Username
- `password` MeroShare Password
- `account` Bank Account Number
- `dmat` DMAT Account Number
- `crn` CRN Number
- `pin` Transaction PIN
- `capital_id` (Optional)

#### _update_capital_list()
Updates list of capitals and saves a local copy.

#### login()
Logs into the account.

#### logout()
Logs out of the account

#### get_applicable_issues()
Gets the list of currently open applicable issues.

#### get_my_details()
Gets details of currently logged in acount

#### get_application_status(share_id: str)
Gets the status of applied application.
- `share_id` ID of applied issue

#### apply(share_id: str, quantity: str)
Applies for issues.
- `share_id` ID of issue to apply
- `quantity` Quantity to apply


## Basic Usage:
```
from nepseutils import MeroShare

if __name__=="__main__":
    login_info = {
            "name": "Jane Doe",
            "username": "01111111",
            "password": "janedoe1",
            "dpid": "13700",
            "dmat": "1301370001233333",
            "crn": "01-R00122222",
            "pin": "1234",
            "account": "0075750611112222",
    }

    ms = MeroShare(**login_info)
    ms.login()
    ms.apply(share_id="342",quantity="10")
    ms.logout()


```

## FAQ
#### Why do I need to provide inputs other than Username, Password, and DPID?
I haven't implemented the feature to extract client details from meroshare so you need to provide it. But it will be implemented in future releases.


## Known Issues
These are known issues that I plan to fix in future versions:
- Data types of some arguments like quantity and price is string
- Retrying failed attempts is not implemented for some functions
- Remove unnecessary inputs
