from abc import ABC, abstractmethod
from pathlib import Path
from typing import Union

from .transaction import Transaction

class BankParser(ABC):
    """
        Абстрактный базовый класс для всех парсеров банков.

        Контракт: каждая реализация получает путь к файлу и возвращает
        список нормализованных транзакций. Всё специфичное для банка
        (координаты колонок, форматы дат, кодировки) — внутри реализации.
    """

    BANK_ID: str = ""

    @abstractmethod
    def parse(self, file_path: Union[str, Path]) -> list[Transaction]:
        """
           Разобрать файл выписки и вернуть список транзакций.

           Args:
               file_path: Путь к файлу выписки (PDF, CSV, XLSX и т.д.)

           Returns:
               Список нормализованных транзакций. Пустой список, если
               транзакций не найдено.

           Raises:
               FileNotFoundError: файл не существует
               ValueError: файл повреждён или не соответствует шаблону банка
        """
        ...

    def supports(self, file_path: Union[str, Path]) -> bool:
        """
        Эвристическая проверка: может ли этот парсер обработать файл.
        По умолчанию — всегда True. Переопределите для авто-определения банка.
        """
        return True
