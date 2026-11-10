import zipfile

import openpyxl

from sales_merger.writer import write_report
from tests.helpers import sample_metrics, sample_stats


def test_report_sheets_and_summary(tmp_path):
    write_report(tmp_path / "r.xlsx", sample_metrics(), sample_stats())
    wb = openpyxl.load_workbook(tmp_path / "r.xlsx")
    assert wb.sheetnames == ["Сводка", "По менеджерам", "По месяцам"]
    s = {r[0].value: r[1].value for r in wb["Сводка"].iter_rows() if r[0].value}
    assert s["Общая выручка"] == 9500.0 and s["Количество заказов"] == 3 and s["Средний чек"] == 3166.67
    assert s["Период данных"] == "2026-10-15 — 2026-12-01"
    assert (s["Обработано файлов"], s["Строк принято"], s["Строк отклонено"]) == (1, 3, 2)


def test_report_money_formats_in_summary(tmp_path):
    write_report(tmp_path / "r.xlsx", sample_metrics(), sample_stats())
    ws = openpyxl.load_workbook(tmp_path / "r.xlsx")["Сводка"]
    cells = {r[0].value: r[1] for r in ws.iter_rows() if r[0].value}
    assert cells["Общая выручка"].number_format == "#,##0.00" and cells["Средний чек"].number_format == "#,##0.00"


def test_report_tables(tmp_path):
    write_report(tmp_path / "r.xlsx", sample_metrics(), sample_stats())
    wb = openpyxl.load_workbook(tmp_path / "r.xlsx")
    assert [c.value for c in wb["По менеджерам"][1]][:5] == ["Менеджер", "Заказы", "Выручка", "Средний чек", "Доля выручки, %"]
    months = [r[0].value for r in wb["По месяцам"].iter_rows(min_row=2) if r[0].value]
    assert months == ["2026-10", "2026-11", "2026-12"]


def test_report_has_two_native_charts(tmp_path):
    write_report(tmp_path / "r.xlsx", sample_metrics(), sample_stats())
    names = zipfile.ZipFile(tmp_path / "r.xlsx").namelist()
    assert len([n for n in names if n.startswith("xl/charts/chart")]) == 2
