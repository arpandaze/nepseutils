# NEPSE Utils
Collection of scripts to interact with NEPSE related sites.

## Installation instruction

### For Windows:
* **Step 1:** Download Python installer from [here](http://python.org/downloads). Choose version greater than 3.9.
* **Step 2:** Launch the installer, tick "Add Python 3.10 to PATH" on the first page and complete the installation.
* **Step 3:** Search for command prompt and open it.
* **Step 4:** Verify that you have python version greater than 3.9 by typing `python --version`
* **Step 5:** Verify that you have pip installed by entering `pip --version`
* **Step 6:** Install nepseutils by entering: `pip install nepseutils`
* **Step 7:** Launch nepseutils by entering: `python -m nepseutils`

### For Linux and Mac:
* **Step 1:** Install Python (Version greater than 3.9) using your package manager.
* **Step 2:** Pip might not come with python in some of the distros. To install it, you can use your package manager or enter the following command `curl https://bootstrap.pypa.io/get-pip.py | python`
* **Step 3:** Verify that you have python version greater than 3.9 by typing `python --version`
* **Step 4:** Verify that you have pip installed by entering `pip --version`
* **Step 5:** Install nepseutils by entering: `pip install nepseutils`
* **Step 6:** Launch nepseutils by entering: `python -m nepseutils`

*Note: Some distros might default to python2 when both python2 and python3 are installed so you might need to enter python3 and pip3 instead of python and pip.*

## Commands:
|  Command      |  Description                 |
|---------------|------------------------------|
|`add`          | Add an account               |
|`remove`       | Remove an account            |
|`change lock`  | Change unlock password       |
|`list accounts`| Show list of accounts        |
|`list results` | Show list of results         |
|`apply`        | Apply open issues            |
|`status`       | Check IPO application status |
|`result`       | Check IPO result             |
|`exit`         | Exit the shell               |

## Usage

You can launch nepseutils by entering `python -m nepseutils` in your command line. On the first launch, it will ask you to set a new password for nepseutils (Not MeroShare). You will have to enter this next time you launch nepseutils.
### Launching nepseutils:
```
python -m nepseutils
```

### Adding an account
#### Command:
```
add {16_digit_dmat_number} {meroshare_password} {meroshare_pin}
```
*You don't need to enter other infos. It will be automatically obtained.*
#### Example:
```
NepseUtils > add 1234567891234567 myp@ssw0rd 1234
```
#### Sample Output:
```
Successfully obtained details for account: Ram Bahadur
```

### Applying for IPO
#### Command:
```
apply
```

Then you will see this kind of output:
```
NepseUtils > apply
+----------+----------------+-------+------------+
| Share ID | Company Name   | Scrip | Close Date |
+----------+----------------+-------+------------+
|   401    | Sample Company |  SMPL | 2021-01-01 |
+----------+--------------+-------+--------------+
Enter Share ID:
```
Enter share ID of company that you want to apply for.

```
Enter Share ID: 401
Units to Apply:
```
Enter number of units (Not rupees) that you want to apply. This will apply IPO for all the added accounts.

### Checking IPO Result
#### Command:
```
result
```
#### Sample Output:
```
NepseUtils > result
+----+------------+-------------------------------------------------+
| ID |   Scrip    |                      Name                       |
+----+------------+-------------------------------------------------+
| 1  |   MLBSL    |     MAHILA LAGHUBITTA BITTIYA SANSTHA LTD.      |
| 2  |    SBCF    |              Sunrise Bluechip Fund              |
| 3  |    JLIC    |            Jyoti Life Insurance Ltd             |
| 4  | NIBLSFUND  |             NIBL Samriddhi Fund -2              |
| 5  |    CHDC    |     CEDB Hydropower Development Company Ltd     |
| 6  |   PSFUND   |               Prabhu Select Fund                |
| 7  | NMBD209293 |           4% NMB Energy Bond 2092/93            |
| 8  | PRVUD2087  |            8.5 % PRVU Debenture 2087            |
| 10 |   MKJCL    |     Mailung Khola Jal Vidhyut Company Ltd.      |
| 11 |    SLIL    |          Sanima Life Insurance Limited          |
| 12 | NABILD2085 |             8% Nabil Debenture 2085             |
| 13 |   MALBSL   |   Manushi Laghubitta Bittiya Sanstha Limited    |
| 14 |   MEGAMF   |               Mega Mutual Fund -1               |
| 15 |    TPCL    |           Terhathum Power Company Ltd           |
| 16 |  NMBSBFE   |            NMB Saral Bachat Fund - E            |
| 17 |    NBF3    |              Nabil Balanced Fund 3              |
| 18 |    SUL     |                 Sahas Urja Ltd.                 |
| 19 |   BBNHCL   |     Buddhabhumi Nepal Hydro Power Co. Ltd.      |
| 20 |   NYADI    |            Nyadi Hydropower Limited             |
| 21 |   MBKJCL   |   Madhya Bhotekoshi Jalabidhyut Company Ltd.    |
| 22 |    SPCL    |           Samling Power Company Ltd.            |
| 23 |  CBLD2088  |            Civil Bank Debenture 2088            |
| 24 |   JSLBS    | Jalpa Samudayik Laghubitta Bittiya Sanstha Ltd. |
| 25 |    ENL     |             Emerging Nepal Limited              |
+----+------------+-------------------------------------------------+
Choose a company ID:
```

Enter ID of company that you want to check result for.

```
Choose a company ID: 21
+----------------------------+---------+----------+
|            Name            | Alloted | Quantity |
+----------------------------+---------+----------+
|       Ram  Bahadur         |  False  |   None   |
|       Hari  Bahadur        |  True   |    10    |
|       Shyam  Prasad        |  False  |   None   |
+----------------------------+---------+----------+
```


### Removing account
#### Command:
```
remove
```
#### Sample Output
```
+----+----------------------------+------------------+------------------+--------------+
| ID |            Name            |       DMAT       |     Account      |     CRN      |
+----+----------------------------+------------------+------------------+--------------+
| 1  |       Ram  Bahadur         | 1201970008888888 | 0075757575757575 | 07-819284939 |
| 2  |      Hari  Bahadur         | 1201970007878887 |  8758752835478   |  M52394589   |
| 3  |      Shyam  Prasad         | 1201970002278282 | 5923459259243594 |  F59824935   |
+----+----------------------------+------------------+------------------+--------------+
Choose an account ID:
```
Then choose account to remove.

### Show added accounts
#### Command:
```
list accounts
```
#### Sample Output
```
+----+----------------------------+------------------+------------------+--------------+
| ID |            Name            |       DMAT       |     Account      |     CRN      |
+----+----------------------------+------------------+------------------+--------------+
| 1  |       Ram  Bahadur         | 1201970008888888 | 0075757575757575 | 07-819284939 |
| 2  |      Hari  Bahadur         | 1201970007878887 |  8758752835478   |  M52394589   |
| 3  |      Shyam  Prasad         | 1201970002278282 | 5923459259243594 |  F59824935   |
+----+----------------------------+------------------+------------------+--------------+
```
