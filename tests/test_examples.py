"""Проверка на готовых таблицах из examples/sales (те же файлы описаны в README)."""
from pathlib import Path

import openpyxl

from sales_merger.cli import main

EXAMPLES = Path(__file__).resolve().parent.parent / "examples" / "sales"


def test_example_tables(tmp_path):
    out = tmp_path / "out"
    code = main([str(EXAMPLES), "-o", str(out), "--no-color"])
    assert code == 1
    merged = next(out.glob("merged_sales_*.xlsx"))
    errors = next(out.glob("errors_*.xlsx"))
    assert openpyxl.load_workbook(merged).active.max_row == 1 + 43
    errors_ws = openpyxl.load_workbook(errors).active
    assert errors_ws.max_row == 1 + 8
    assert sorted(row[0].value for row in errors_ws.iter_rows(min_row=2)) == sorted(
        ["1_aleksey.csv"] * 3 + ["2_maria.xlsx"] * 3 + ["3_ivan.csv"] * 2)
    summary = {r[0].value: r[1].value for r in openpyxl.load_workbook(next(out.glob("report_*.xlsx")))["Сводка"].iter_rows() if r[0].value}
    assert summary["Общая выручка"] == 744050.0 and summary["Количество заказов"] == 43
