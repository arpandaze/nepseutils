from typing import List


class PortfolioEntry:
    current_balance: float
    last_transaction_price: float
    previous_closing_price: float
    script: str
    script_desc: str
    value_as_of_last_transaction_price: float
    value_as_of_previous_closing_price: float

    def __init__(
        self,
        current_balance: float,
        last_transaction_price: float,
        previous_closing_price: float,
        script: str,
        script_desc: str,
        value_as_of_last_transaction_price: float,
        value_as_of_previous_closing_price: float,
    ) -> None:
        self.current_balance = current_balance
        self.last_transaction_price = last_transaction_price
        self.previous_closing_price = previous_closing_price
        self.script = script
        self.script_desc = script_desc
        self.value_as_of_last_transaction_price = value_as_of_last_transaction_price
        self.value_as_of_previous_closing_price = value_as_of_previous_closing_price

    def to_json(self):
        return {
            "current_balance": self.current_balance,
            "last_transaction_price": self.last_transaction_price,
            "previous_closing_price": self.previous_closing_price,
            "script": self.script,
            "script_desc": self.script_desc,
            "value_as_of_last_transaction_price": self.value_as_of_last_transaction_price,
            "value_as_of_previous_closing_price": self.value_as_of_previous_closing_price,
        }

    @staticmethod
    def from_json(json: dict):
        return PortfolioEntry(
            json["current_balance"],
            json["last_transaction_price"],
            json["previous_closing_price"],
            json["script"],
            json["script_desc"],
            json["value_as_of_last_transaction_price"],
            json["value_as_of_previous_closing_price"],
        )


class Portfolio:
    entries: List[PortfolioEntry]

    total_items: int
    total_value_as_of_last_transaction_price: float
    total_value_as_of_previous_closing_price: float

    def __init__(
        self,
        entries: List[PortfolioEntry],
        total_items: int,
        total_value_as_of_last_transaction_price: float,
        total_value_as_of_previous_closing_price: float,
    ) -> None:
        self.entries = entries
        self.total_items = total_items
        self.total_value_as_of_last_transaction_price = (
            total_value_as_of_last_transaction_price
        )
        self.total_value_as_of_previous_closing_price = (
            total_value_as_of_previous_closing_price
        )

    def to_json(self):
        return {
            "entries": [entry.to_json() for entry in self.entries],
            "total_items": self.total_items,
            "total_value_as_of_last_transaction_price": self.total_value_as_of_last_transaction_price,
            "total_value_as_of_previous_closing_price": self.total_value_as_of_previous_closing_price,
        }

    @staticmethod
    def from_json(json: dict):
        return Portfolio(
            [PortfolioEntry.from_json(entry) for entry in json["entries"]],
            json["total_items"],
            json["total_value_as_of_last_transaction_price"],
            json["total_value_as_of_previous_closing_price"],
        )
