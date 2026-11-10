"""Очистка данных: пробелы, пустые строки, дубли, имена менеджеров."""
from __future__ import annotations

import pandas as pd

from sales_merger.columns import FILE_COL, REQUIRED, ROW_COL
from sales_merger.errors import DUPLICATE, ErrorCollector


def clean_text(df: pd.DataFrame) -> pd.DataFrame:
    """Обрезает пробелы по краям (в том числе неразрывные) и схлопывает повторные."""
    out = df.copy()
    for col in REQUIRED:
        out[col] = out[col].astype(str).str.replace(r"\s+", " ", regex=True).str.strip()
    return out


def drop_empty_rows(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Удаляет строки, где все столбцы REQUIRED пусты; возвращает таблицу и число удалённых."""
    empty = (df[REQUIRED] == "").all(axis=1)
    return df[~empty].reset_index(drop=True), int(empty.sum())


def drop_duplicates(df: pd.DataFrame, errors: ErrorCollector) -> pd.DataFrame:
    """Остаётся первая строка по номеру заказа, остальные уходят в ошибки «Дубликат»."""
    first: dict[str, tuple[str, int]] = {}
    keep: list[int] = []
    for pos, row in enumerate(df.to_dict("records")):
        order_id = row["Номер заказа"]
        source = (row[FILE_COL], int(row[ROW_COL]))
        if order_id not in first:
            first[order_id] = source
            keep.append(pos)
            continue
        kept_file, kept_row = first[order_id]
        errors.add(source[0], source[1], order_id, DUPLICATE,
                   f"Номер заказа уже есть: оставлена строка {kept_row} файла {kept_file}", order_id)
    return df.iloc[keep].reset_index(drop=True)


def unify_managers(df: pd.DataFrame) -> pd.DataFrame:
    """Имя менеджера заменяется первым встреченным написанием среди совпадающих без учёта регистра."""
    out = df.copy()
    first: dict[str, str] = {}
    for name in out["Менеджер"]:
        first.setdefault(name.casefold(), name)
    out["Менеджер"] = [first[name.casefold()] for name in out["Менеджер"]]
    return out
