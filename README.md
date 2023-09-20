<div align="center">

# NEPSE Utils

![Release Pipeline](https://github.com/arpandaze/nepseutils/actions/workflows/release.yml/badge.svg)
![PyPI - Version](https://img.shields.io/pypi/v/nepseutils)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/nepseutils)

CLI Application written in Python to automatically apply IPO openings from multiple accounts at once!

</div>

## Commands:

| Command         | Description                                                        |
| --------------- | ------------------------------------------------------------------ |
| `add`           | Add an account                                                     |
| `apply`         | Apply open issues                                                  |
| `result`        | Check IPO result                                                   |
| `status`        | Check IPO application status                                       |
| `tag`           | Tag an account to group them                                       |
| `select`        | Selects accounts with specific tag to be used for further commands |
| `portfolio`     | List portfolio of an account                                       |
| `sync`          | Syncs unfetched portfolio and application status from MeroShare    |
| `stats`         | Shows overall statistics of accounts                               |
| `remove`        | Remove an account                                                  |
| `change lock`   | Change unlock password                                             |
| `list accounts` | Show list of accounts                                              |
| `list results`  | Show list of results                                               |
| `loglevel`      | Set log level                                                      |
| `telegram`      | Enable or disable telegram notification                            |
| `help`          | Shows list of commands                                             |
| `exit`          | Exit the shell                                                     |

**Note: Use `help {command}` for help regarding commands!**

## Installation instruction

- Install Python (Version greater than 3.9) using your package manager.
- Install nepseutils using pipx (recommended): `pipx install nepseutils`
- Launch from command line with `nepseutils`

_Note: If pipx is not available, use pip to install using `pip3 install nepseutils` and launch using `python -m nepseutils`_

## Basic Usage

You can launch nepseutils by entering `nepseutils` in your command line. On the first launch, it will ask you to set a new password for nepseutils (Not MeroShare). You will have to enter this next time you launch nepseutils.

### Launching nepseutils

```
nepseutils
```
OR
```
python -m nepseutils
```

### Adding an account

#### Command:

```
add {16_digit_dmat_number} {meroshare_password} {crn} {meroshare_pin}
```

_You don't need to enter other infos. It will be automatically obtained._

#### Example:

```
NepseUtils > add 1234567891234567 myp@ssw0rd 02-R00222224 1234
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
