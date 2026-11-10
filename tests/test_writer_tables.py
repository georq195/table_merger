import datetime

import openpyxl

from sales_merger.columns import REQUIRED
from sales_merger.errors import BAD_FORMAT, ERROR_COLUMNS, EMPTY_FIELD, ErrorCollector
from sales_merger.writer import MERGED_COLUMNS, write_errors, write_merged
from tests.helpers import make_typed_frame_with_revenue


def test_merged_columns_constant():
    assert MERGED_COLUMNS == REQUIRED + ["Выручка"]


def test_merged_layout_and_formats(tmp_path):
    write_merged(tmp_path / "m.xlsx", make_typed_frame_with_revenue())
    ws = openpyxl.load_workbook(tmp_path / "m.xlsx").active
    assert [c.value for c in ws[1]] == MERGED_COLUMNS and ws.freeze_panes == "A2"
    assert ws["B1"].font.bold and ws["B1"].fill.fgColor.rgb not in (None, "00000000")
    price = ws.cell(2, 6); assert price.number_format == "#,##0.00" and price.alignment.horizontal == "right"
    d = ws.cell(2, 2); assert d.number_format == "yyyy-mm-dd" and isinstance(d.value, datetime.datetime)
    assert ws.cell(2, 3).alignment.horizontal in ("left", None)
    assert ws.column_dimensions["D"].width >= len("Категория")


def test_merged_sheet_name_and_internal_columns_dropped(tmp_path):
    write_merged(tmp_path / "m.xlsx", make_typed_frame_with_revenue())
    wb = openpyxl.load_workbook(tmp_path / "m.xlsx")
    assert wb.sheetnames == ["Продажи"] and wb.active.max_column == len(MERGED_COLUMNS)
    assert wb.active.cell(2, 5).number_format == "#,##0"


def test_errors_sheet_with_rows(tmp_path):
    e = ErrorCollector(); e.add("a.csv", 3, "1001", EMPTY_FIELD, "Поле «Цена» не заполнено", "")
    write_errors(tmp_path / "e.xlsx", e)
    wb = openpyxl.load_workbook(tmp_path / "e.xlsx")
    ws = wb.active
    assert wb.sheetnames == ["Ошибки"]
    assert [c.value for c in ws[1]] == ERROR_COLUMNS and ws.cell(2, 2).value == 3


def test_errors_sheet_without_errors_has_marker_row(tmp_path):
    write_errors(tmp_path / "e.xlsx", ErrorCollector())
    ws = openpyxl.load_workbook(tmp_path / "e.xlsx").active
    assert ws.cell(2, 5).value == "Ошибок нет" and ws.max_row == 2


def test_header_font_is_named_like_body_font(tmp_path):
    write_merged(tmp_path / "m.xlsx", make_typed_frame_with_revenue())
    ws = openpyxl.load_workbook(tmp_path / "m.xlsx").active
    assert ws["A1"].font.name == "Calibri" and ws["A1"].font.sz == 11 and ws["A1"].font.bold


def test_text_starting_with_equals_stays_text_and_control_chars_are_stripped(tmp_path):
    e = ErrorCollector()
    e.add("a.csv", 2, "1", BAD_FORMAT, "x", "=1+1"); e.add("a.csv", 3, "2", BAD_FORMAT, "x", "Key\x07board")
    write_errors(tmp_path/"e.xlsx", e)
    ws = openpyxl.load_workbook(tmp_path/"e.xlsx").active
    assert ws.cell(2, 6).value == "=1+1" and ws.cell(2, 6).data_type == "s"
    assert ws.cell(3, 6).value == "Keyboard"
