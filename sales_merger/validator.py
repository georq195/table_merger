"""Разбор значений и проверка строк."""
from __future__ import annotations

import datetime as dt
import re

import pandas as pd

from sales_merger.columns import FILE_COL, REQUIRED, ROW_COL, map_columns
from sales_merger.errors import BAD_FORMAT, BAD_VALUE, EMPTY_FIELD, ErrorCollector


class ParseError(ValueError):
    """Значение не разобрано; `kind` это BAD_FORMAT или BAD_VALUE."""

    def __init__(self, kind: str, message: str) -> None:
        super().__init__(message)
        self.kind = kind


_ISO = re.compile(r"^(\d{4})-(\d{2})-(\d{2})(?: \d{2}:\d{2}:\d{2})?$")
_DOT = re.compile(r"^(\d{2})\.(\d{2})\.(\d{4})$")
_SLASH = re.compile(r"^(\d{2})/(\d{2})/(\d{4})$")
_NUMBER = re.compile(r"^-?\d+(\.\d+)?$")
_WHITESPACE = re.compile(r"\s+")  # \s в Python 3 включает неразрывные пробелы
MIN_YEAR, MAX_YEAR = 1900, 2100
MAX_QUANTITY = 10**9
MAX_PRICE = 10**12


def parse_date(text: str) -> dt.date:
    s = str(text).strip()
    if m := _ISO.match(s):
        y, mo, d = (int(g) for g in m.groups())
    elif m := _DOT.match(s):
        d, mo, y = (int(g) for g in m.groups())
    elif m := _SLASH.match(s):
        d, mo, y = (int(g) for g in m.groups())
    else:
        raise ParseError(BAD_FORMAT, f"не дата: «{text}»")
    try:
        date = dt.date(y, mo, d)
    except ValueError:
        raise ParseError(BAD_FORMAT, f"несуществующая дата: «{text}»") from None
    if not MIN_YEAR <= date.year <= MAX_YEAR:
        raise ParseError(BAD_VALUE, f"дата вне допустимого диапазона {MIN_YEAR}–{MAX_YEAR}: «{text}»")
    return date


def _number(text: str) -> float:
    s = _WHITESPACE.sub("", str(text)).replace(",", ".")
    if not _NUMBER.match(s):
        raise ParseError(BAD_FORMAT, f"не число: «{text}»")
    return float(s)


def parse_price(text: str) -> float:
    value = _number(text)
    if value < 0:
        raise ParseError(BAD_VALUE, f"цена отрицательная: «{text}»")
    if value > MAX_PRICE:
        raise ParseError(BAD_VALUE, f"цена слишком велика: «{text[:30]}»")
    return value


def parse_quantity(text: str) -> int:
    value = _number(text)
    if not value.is_integer():
        raise ParseError(BAD_FORMAT, f"количество не целое: «{text}»")
    if value <= 0:
        raise ParseError(BAD_VALUE, f"количество должно быть больше нуля: «{text}»")
    if value > MAX_QUANTITY:
        raise ParseError(BAD_VALUE, f"количество слишком велико: «{text[:30]}»")
    return int(value)


class MissingColumnsError(Exception):
    """В файле нет обязательных столбцов; `missing` в порядке REQUIRED."""

    def __init__(self, missing: list[str]) -> None:
        super().__init__("Нет столбцов: " + ", ".join(missing))
        self.missing = missing


def select_columns(raw: pd.DataFrame, file: str) -> pd.DataFrame:
    """Канонические столбцы REQUIRED + служебные FILE_COL и ROW_COL (позиция + 2)."""
    mapping, missing = map_columns(list(raw.columns))
    if missing:
        raise MissingColumnsError(missing)
    source = {field: original for original, field in mapping.items()}
    df = pd.DataFrame({field: raw[source[field]].to_numpy() for field in REQUIRED})
    df[FILE_COL] = file
    df[ROW_COL] = range(2, len(df) + 2)
    return df


_PARSERS = {"Дата": parse_date, "Количество": parse_quantity, "Цена": parse_price}


def validate_rows(df: pd.DataFrame, errors: ErrorCollector) -> pd.DataFrame:
    """Оставляет корректные строки, приводит типы, каждое нарушение пишет в `errors`."""
    keep: list[int] = []
    parsed: dict[str, list] = {field: [] for field in _PARSERS}
    for pos, row in enumerate(df.to_dict("records")):
        ok = True
        values = {}
        for field in REQUIRED:
            raw_value = row[field]
            if raw_value == "":
                errors.add(row[FILE_COL], row[ROW_COL], row["Номер заказа"], EMPTY_FIELD,
                           f"Поле «{field}» не заполнено", "")
                ok = False
                continue
            parser = _PARSERS.get(field)
            if parser is None:
                continue
            try:
                values[field] = parser(raw_value)
            except ParseError as exc:
                errors.add(row[FILE_COL], row[ROW_COL], row["Номер заказа"], exc.kind,
                           f"Поле «{field}»: {exc}", raw_value)
                ok = False
        if ok:
            keep.append(pos)
            for field in _PARSERS:
                parsed[field].append(values[field])
    out = df.iloc[keep].reset_index(drop=True).copy()
    out["Дата"] = pd.to_datetime(pd.Series(parsed["Дата"], dtype="object")).astype("datetime64[ns]")
    out["Количество"] = pd.Series(parsed["Количество"], dtype="int64")
    out["Цена"] = pd.Series(parsed["Цена"], dtype="float64")
    out[ROW_COL] = out[ROW_COL].astype("int64")
    return out
