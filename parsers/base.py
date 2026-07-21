from abc import ABC, abstractmethod
from pathlib import Path
from typing import Union

from .transaction import Transaction

class BankParser(ABC):
    BANK_ID: str = ""

    @abstractmethod
    def parse(self, file_path: Union[str, Path]) -> list[Transaction]:
        ...

    def supports(self, file_path: Union[str, Path]) -> bool:
        return True
