import datetime
from pathlib import Path

import openpyxl
import pytest

from sales_merger.loader import load_file, LoadError

HEAD = "Номер заказа,Дата,Товар,Категория,Количество,Цена,Менеджер\n"

def test_csv_utf8_bom_comma(tmp_path):
    p = tmp_path/"a.csv"; p.write_text(HEAD + "00123,2026-10-15,Keyboard,Electronics,2,3500.00,Alex\n", encoding="utf-8-sig")
    df = load_file(p)
    assert df.iloc[0]["Номер заказа"] == "00123" and df.iloc[0]["Цена"] == "3500.00"

def test_csv_russian_excel_cp1251_semicolon(tmp_path):
    p = tmp_path/"a.csv"
    p.write_bytes((HEAD.replace(",", ";") + "1001;15.10.2026;Клавиатура;Электроника;2;3 500,00;Алекс\n").encode("cp1251"))
    df = load_file(p)
    assert df.iloc[0]["Товар"] == "Клавиатура" and df.iloc[0]["Цена"] == "3 500,00"

def test_csv_blank_line_keeps_row_positions(tmp_path):
    p = tmp_path/"a.csv"; p.write_text(HEAD + "1,2026-10-15,a,b,1,1,A\n\n2,2026-10-16,a,b,1,1,A\n", encoding="utf-8")
    df = load_file(p)
    assert len(df) == 3 and df.iloc[1].tolist() == [""] * 7

def test_xlsx_numeric_id_and_real_date_and_first_sheet_only(tmp_path):
    wb = openpyxl.Workbook(); ws = wb.active
    ws.append(["Номер заказа","Дата","Товар","Категория","Количество","Цена","Менеджер"])
    ws.append([1001, datetime.datetime(2026,10,15), "Keyboard", "Electronics", 2, 3500.5, "Alex"])
    wb.create_sheet("Second").append(["junk"]); p = tmp_path/"a.xlsx"; wb.save(p)
    df = load_file(p)
    assert df.iloc[0]["Номер заказа"] == "1001" and df.iloc[0]["Дата"].startswith("2026-10-15")
    assert list(df.columns)[0] == "Номер заказа" and len(df) == 1

def test_xls_fixture():
    df = load_file(Path("tests/data/sample.xls"))
    assert len(df) == 2 and df.iloc[0]["Номер заказа"] == "1001" and float(df.iloc[0]["Цена"]) == 3500.0

def test_header_only_and_empty_file(tmp_path):
    (tmp_path/"h.csv").write_text(HEAD, encoding="utf-8"); (tmp_path/"e.csv").write_text("", encoding="utf-8")
    assert len(load_file(tmp_path/"h.csv")) == 0
    assert len(load_file(tmp_path/"e.csv")) == 0

def test_corrupt_xlsx_raises_load_error(tmp_path):
    p = tmp_path/"bad.xlsx"; p.write_bytes(b"not a zip")
    with pytest.raises(LoadError): load_file(p)


def test_xlsx_datetime_with_fraction_loads_as_plain_date(tmp_path):
    wb = openpyxl.Workbook(); ws = wb.active
    ws.append(["Номер заказа","Дата","Товар","Категория","Количество","Цена","Менеджер"])
    ws.append([1, datetime.datetime(2026, 10, 17, 13, 45, 12, 345000), "K", "E", 1, 1, "A"]); p = tmp_path/"a.xlsx"; wb.save(p)
    assert load_file(p).iloc[0]["Дата"] == "2026-10-17"
