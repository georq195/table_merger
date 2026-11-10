"""Общие помощники для тестов."""
from __future__ import annotations

import pandas as pd

from sales_merger.columns import FILE_COL, REQUIRED, ROW_COL

GOOD = {
    "Номер заказа": "1001",
    "Дата": "2026-10-15",
    "Товар": "Keyboard",
    "Категория": "Electronics",
    "Количество": "2",
    "Цена": "3500.00",
    "Менеджер": "Alex",
}


def make_frame(rows: list[dict], file: str = "a.csv") -> pd.DataFrame:
    """Очищенная текстовая таблица из словарей; пропущенные поля это пустая строка."""
    records = []
    for pos, row in enumerate(rows):
        record = {col: row.get(col, "") for col in REQUIRED}
        record[FILE_COL] = file
        record[ROW_COL] = row.get(ROW_COL, pos + 2)
        records.append(record)
    return pd.DataFrame(records, columns=REQUIRED + [FILE_COL, ROW_COL])


HEADER = ["Номер заказа", "Дата", "Товар", "Категория", "Количество", "Цена", "Менеджер"]


def write_csv(folder, name: str, body: str):
    """CSV в UTF-8: стандартный заголовок и затем `body`."""
    from pathlib import Path

    path = Path(folder) / name
    path.write_text(",".join(HEADER) + "\n" + body, encoding="utf-8")
    return path


def write_xlsx(folder, name: str, rows: list[list]):
    """XLSX: стандартный заголовок плюс строки."""
    from pathlib import Path

    import openpyxl

    path = Path(folder) / name
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(HEADER)
    for row in rows:
        ws.append(row)
    wb.save(path)
    return path


def make_typed_frame(price=None, qty=None) -> pd.DataFrame:
    """Типизированная таблица в формате выхода `validate_rows`.

    Без параметров: три заказа (Alex 2026-10-15 2x3500, Maria 2026-10-20 1x1000,
    Alex 2026-12-01 3x500). `price`/`qty` заменяют цену и количество единственной строки.
    """
    if price is not None or qty is not None:
        rows = [("1001", "2026-10-15", 2 if qty is None else qty, 3500.0 if price is None else price, "Alex")]
    else:
        rows = [
            ("1001", "2026-10-15", 2, 3500.0, "Alex"),
            ("1002", "2026-10-20", 1, 1000.0, "Maria"),
            ("1003", "2026-12-01", 3, 500.0, "Alex"),
        ]
    df = pd.DataFrame({
        "Номер заказа": [r[0] for r in rows],
        "Дата": pd.to_datetime([r[1] for r in rows]).astype("datetime64[ns]"),
        "Товар": "Keyboard",
        "Категория": "Electronics",
        "Количество": pd.Series([r[2] for r in rows], dtype="int64"),
        "Цена": pd.Series([r[3] for r in rows], dtype="float64"),
        "Менеджер": [r[4] for r in rows],
    })
    df[FILE_COL] = "a.csv"
    df[ROW_COL] = pd.Series(range(2, len(df) + 2), dtype="int64")
    return df


def make_typed_frame_with_revenue() -> pd.DataFrame:
    """Типизированная таблица из `make_typed_frame` плюс «Выручка» и служебные `_file`/`_row`."""
    from sales_merger.metrics import add_revenue

    return add_revenue(make_typed_frame())


def sample_metrics():
    """Метрики набора из `make_typed_frame`."""
    from sales_merger.metrics import add_revenue, compute_metrics

    return compute_metrics(add_revenue(make_typed_frame()))


def sample_stats():
    """Два `FileStat`: принятый и отклонённый целиком."""
    from sales_merger.models import FileStat

    return [
        FileStat("a.csv", read=5, accepted=3, invalid=1, duplicates=1),
        FileStat("old.xls", problem="Нет столбцов: Цена"),
    ]
