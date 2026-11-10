"""Чтение .csv / .xlsx / .xls в таблицу из текстов."""
from __future__ import annotations

import csv
import datetime
import io
import math
from pathlib import Path

import pandas as pd

CSV_ENCODINGS = ("utf-8-sig", "cp1251")


class LoadError(Exception):
    """Файл не удалось прочитать; сообщение пригодно для таблицы ошибок."""


def _decode(path: Path) -> str:
    data = path.read_bytes()
    for encoding in CSV_ENCODINGS:
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise LoadError("Не удалось определить кодировку файла (ожидается UTF-8 или cp1251)")


def _sniff_delimiter(text: str) -> str:
    try:
        return csv.Sniffer().sniff(text[:4096], delimiters=",;").delimiter
    except csv.Error:
        return ","


def _read_csv(path: Path) -> pd.DataFrame:
    text = _decode(path)
    try:
        df = pd.read_csv(
            io.StringIO(text),
            sep=_sniff_delimiter(text),
            dtype=str,
            keep_default_na=False,
            skip_blank_lines=False,
        )
    except pd.errors.EmptyDataError:
        return pd.DataFrame()
    return df


def _cell_to_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        if math.isnan(value):
            return ""
        if value.is_integer():
            return str(int(value))
        return str(value)
    if isinstance(value, bool):
        return str(value)
    if value is pd.NaT:
        return ""
    if isinstance(value, (datetime.datetime, datetime.date, pd.Timestamp)):
        return value.strftime("%Y-%m-%d")  # время и доли секунды в продажах не нужны
    return str(value)


def _read_excel(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name=0, dtype=object, keep_default_na=False)
    return df.apply(lambda col: col.map(_cell_to_text))


def load_file(path: Path) -> pd.DataFrame:
    """Все значения текстом, пустые ячейки "", заголовки `str`.

    Строка `i` (с нуля) соответствует строке `i + 2` файла.
    """
    path = Path(path)
    try:
        if path.suffix.lower() == ".csv":
            df = _read_csv(path)
        else:
            df = _read_excel(path)
    except LoadError:
        raise
    except Exception as exc:  # любое исключение pandas/xlrd/openpyxl
        raise LoadError(f"Не удалось прочитать файл: {exc}") from exc
    df.columns = [str(c) for c in df.columns]
    return df
