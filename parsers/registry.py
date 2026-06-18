from pathlib import Path
from typing import Union

from .base import BankParser
from .transaction import Transaction
from .tbank import TBankParser

_REGISTRY: list[BankParser] = [
        TBankParser(),
        # SberParser(),   # будет добавлен позже
        # AlfaParser(),
    ]

def get_parser(bank_id) -> BankParser:

    for parser in _REGISTRY:
        if parser.BANK_ID == bank_id:
            return parser
    raise ValueError(f"Bank ID {bank_id} not found in registry")

def auto_parse(file_path: Union[str,Path], bank_id: str | None = None)-> list[Transaction]:
    """
        Удобная функция: разобрать файл, опционально указав банк.

        Если bank_id не указан — перебирает все парсеры и берёт первый,
        который говорит supports() = True. Подходит для случаев, когда
        банк определяется автоматически (по заголовку файла и т.п.).
        """
    path = Path(file_path)
    if bank_id:
        return get_parser(bank_id).parse(path)
    for parser in _REGISTRY:
        if parser.supports(path):
            return parser.parse(path)

    raise ValueError(f"Не найден подходящий парсер для файла: {path.name}")