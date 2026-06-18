import re
from collections import defaultdict
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Union

import pdfplumber

from .base import BankParser
from .transaction import Transaction


# Границы колонок в PDF (x-координаты, в поинтах)
# Значения берутся из оригинального parc_tb.py, вынесены как константы
_COL_BOUNDS = {
    "date_op":     (0,   100),
    "date_proc":   (100, 180),
    "amount":      (180, 280),
    "amount_card": (280, 370),
    "description": (370, 490),
    "card":        (490, float("inf")),
}

_DATE_FMT = "%d.%m.%Y"          # формат дат в Т-Банк PDF
_DATE_RE  = re.compile(r"\d{2}\.\d{2}\.\d{4}")
_PAGE_NUM_RE = re.compile(r"^\d+$")   # строки-номера страниц

# Строки суммы длиннее этого — точно не сумма, а заголовок/мусор
_AMOUNT_MAX_LEN = 30


def _col_for_x(x: float) -> str:
    for col, (lo, hi) in _COL_BOUNDS.items():
        if lo <= x < hi:
            return col
    return "card"


def _parse_date(s: str) -> datetime | None:
    """Дата из строки вида '01.01.2024'. Возвращает None при ошибке."""
    try:
        # Берём только первые 10 символов — дата без возможного хвоста
        return datetime.strptime(s.strip()[:10], _DATE_FMT)
    except ValueError:
        return None


def _parse_amount(s: str) -> Decimal | None:
    """
    Парсит суммы вида '−1 234,56', '+ 500.00', '1234.56 ₽'.
    Возвращает None при ошибке.
    """
    if not s:
        return None
    # Убираем пробелы-разделители тысяч, символ валюты, неразрывные пробелы
    cleaned = (
        s.replace("\xa0", "")
         .replace(" ", "")
         .replace("₽", "")
         .replace("$", "")
         .replace("€", "")
         .replace(",", ".")
    )
    # Т-Банк использует '−' (U+2212) для минуса, а не обычный '-'
    cleaned = cleaned.replace("−", "-").replace("–", "-")
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def _detect_currency(amount_str: str) -> str:
    """Определяет валюту по символу в строке суммы."""
    if "₽" in amount_str or "руб" in amount_str.lower():
        return "RUB"
    if "$" in amount_str:
        return "USD"
    if "€" in amount_str:
        return "EUR"
    return "RUB"   # дефолт для Т-Банк RU


def _extract_card_last4(s: str) -> str | None:
    """Извлекает последние 4 цифры карты из строки вида '•••• 1234'."""
    m = re.search(r"\d{4}$", s.strip())
    return m.group() if m else None


def _group_words_into_rows(words: list[dict]) -> list[tuple[int, list[dict]]]:
    """Группирует слова по y-координате (с округлением до целых поинтов)."""
    rows: dict[int, list] = defaultdict(list)
    for w in words:
        y = round(w["top"])
        rows[y].append(w)
    return sorted(rows.items())


def _row_to_cols(words_in_row: list[dict]) -> dict[str, str]:
    """Распределяет слова строки по колонкам и склеивает в строки."""
    cols: dict[str, list[str]] = defaultdict(list)
    for w in words_in_row:
        col = _col_for_x(w["x0"])
        cols[col].append(w["text"])
    return {col: " ".join(parts) for col, parts in cols.items()}


def _merge_continuation(current: dict, cols: dict) -> None:
    """Дописывает строку продолжения в текущую транзакцию (multi-line)."""
    for field in ("date_op", "date_proc", "amount", "amount_card", "description", "card"):
        extra = cols.get(field, "")
        if extra:
            current[field] = (current.get(field, "") + " " + extra).strip()


class TBankParser(BankParser):
    """
    Парсер выписок Т-Банка (бывший Тинькофф) в формате PDF.

    Логика: извлекаем слова с координатами через pdfplumber,
    раскладываем по колонкам на основе x-позиции, собираем
    многострочные записи, нормализуем типы.
    """

    BANK_ID = "tbank"

    def supports(self, file_path: Union[str, Path]) -> bool:
        return Path(file_path).suffix.lower() == ".pdf"

    def parse(self, file_path: Union[str, Path]) -> list[Transaction]:
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Файл не найден: {file_path}")

        raw_records = self._extract_raw(file_path)
        transactions = []
        for r in raw_records:
            try:
                transactions.append(self._normalize(r))
            except ValueError:
                pass  # пропускаем заголовки и мусорные строки
        return transactions

    # ------------------------------------------------------------------
    # Внутренние методы
    # ------------------------------------------------------------------

    def _extract_raw(self, pdf_path: Path) -> list[dict]:
        """Шаг 1: Извлекаем сырые словари из PDF (строки как строки)."""
        results: list[dict] = []
        current: dict | None = None

        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                words = page.extract_words()
                rows = _group_words_into_rows(words)

                for _y, words_in_row in rows:
                    texts = [w["text"] for w in words_in_row]

                    # Пропускаем строки-номера страниц
                    if len(texts) == 1 and _PAGE_NUM_RE.fullmatch(texts[0]):
                        continue

                    cols = _row_to_cols(words_in_row)
                    date_op_str = cols.get("date_op", "")

                    amount_str = cols.get("amount", "")
                    # Пропускаем строки-заголовки: дата есть, но amount — длинный текст
                    if _DATE_RE.match(date_op_str) and len(amount_str) > _AMOUNT_MAX_LEN:
                        current = None
                        continue

                    if _DATE_RE.match(date_op_str):
                        # Новая транзакция
                        if current is not None:
                            results.append(current)
                        current = {
                            "date_op":     cols.get("date_op", ""),
                            "date_proc":   cols.get("date_proc", ""),
                            "amount":      cols.get("amount", ""),
                            "amount_card": cols.get("amount_card", ""),
                            "description": cols.get("description", ""),
                            "card":        cols.get("card", ""),
                        }
                    elif current is not None:
                        # Продолжение предыдущей транзакции (перенос строки)
                        _merge_continuation(current, cols)

        if current is not None:
            results.append(current)

        return results

    def _normalize(self, raw: dict) -> Transaction:
        """Шаг 2: Нормализуем сырой словарь в типизированный Transaction."""
        date_op = _parse_date(raw.get("date_op", ""))
        if date_op is None:
            raise ValueError(f"Не удалось разобрать дату операции: {raw.get('date_op')!r}")

        amount_str = raw.get("amount", "")
        amount = _parse_amount(amount_str)
        if amount is None:
            # Некоторые строки (заголовки и т.п.) могут попасть сюда — пропускаем
            raise ValueError(f"Не удалось разобрать сумму: {amount_str!r}")

        currency = _detect_currency(amount_str)

        amount_card_str = raw.get("amount_card", "")
        amount_card = _parse_amount(amount_card_str)
        currency_card = _detect_currency(amount_card_str) if amount_card_str else None

        raw_desc = raw.get("description", "")
        description = raw_desc.strip()

        card_str = raw.get("card", "")
        card_last4 = _extract_card_last4(card_str)

        return Transaction(
            date_op=date_op,
            date_proc=_parse_date(raw.get("date_proc", "")),
            amount=amount,
            currency=currency,
            amount_card=amount_card,
            currency_card=currency_card,
            description=description,
            raw_description=raw_desc,
            card_last4=card_last4,
            source_bank=self.BANK_ID,
        )