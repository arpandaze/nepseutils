from typing import Optional


class Issue:
    name: str
    symbol: str
    status: str
    share_type: str
    company_share_id: str
    applicant_form_id: str
    alloted: Optional[bool]
    alloted_quantity: Optional[float]
    applied_date: Optional[str]
    applied_quantity: Optional[float]
    applied_amount: Optional[float]
    block_amount_status: Optional[str]
    old: Optional[bool] = None

    def __init__(
        self,
        name: str,
        symbol: str,
        status: str,
        share_type: str,
        company_share_id: str,
        applicant_form_id: str,
        alloted: Optional[bool] = None,
        alloted_quantity: Optional[float] = None,
        applied_date: Optional[str] = None,
        applied_quantity: Optional[float] = None,
        applied_amount: Optional[float] = None,
        block_amount_status: Optional[str] = None,
        old: Optional[bool] = None,
    ) -> None:
        self.name = name
        self.symbol = symbol
        self.status = status
        self.share_type = share_type
        self.company_share_id = company_share_id
        self.applicant_form_id = applicant_form_id
        self.alloted = alloted
        self.alloted_quantity = alloted_quantity
        self.applied_date = applied_date
        self.applied_quantity = applied_quantity
        self.applied_amount = applied_amount
        self.block_amount_status = block_amount_status
        self.old = old

    def to_json(self):
        return {
            "name": self.name,
            "symbol": self.symbol,
            "status": self.status,
            "share_type": self.share_type,
            "company_share_id": self.company_share_id,
            "applicant_form_id": self.applicant_form_id,
            "alloted": self.alloted,
            "alloted_quantity": self.alloted_quantity,
            "applied_date": self.applied_date,
            "applied_quantity": self.applied_quantity,
            "applied_amount": self.applied_amount,
            "block_amount_status": self.block_amount_status,
            "old": self.old,
        }

    @staticmethod
    def from_json(json: dict):
        return Issue(
            json["name"],
            json["symbol"],
            json["status"],
            json["share_type"],
            json["company_share_id"],
            json["applicant_form_id"],
            json["alloted"],
            json["alloted_quantity"],
            json["applied_date"],
            json["applied_quantity"],
            json["applied_amount"],
            json["block_amount_status"],
            json["old"],
        )
