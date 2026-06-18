from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional

@dataclass()
class Transaction:


    date_op: datetime #дата операции
    amount: Decimal
    currency: str #валюта
    description: str
    raw_description: str
    source_bank: str

    card_last4: Optional[str] = None
    date_proc: Optional[datetime] = None
    amount_card: Optional[Decimal] = None # Сумма в валюте карты (при конвертации)
    currency_card: Optional[Decimal] = None
    mcc: Optional[str] = None
    category: Optional[str] = None

    def is_expense(self) -> bool:
        return self.amount<0

    def is_income(self) -> bool:
        return self.amount>0
