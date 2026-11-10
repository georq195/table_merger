import openpyxl

from sales_merger.discovery import discover
from sales_merger.errors import *
from sales_merger.pipeline import process
from tests.helpers import write_csv, write_xlsx


def run(tmp_path, *files, on_file=None):
    return process(discover([str(tmp_path / f) for f in files]), on_file)


def test_merge_clean_and_counters(tmp_path):
    write_csv(tmp_path, "a.csv", "1001,2026-10-15,K,E,2,3500,Alex\n\n1002,2026-10-16,M,E,1,,Maria\n1003,2026-10-17,M,E,1,10,alex\n")
    write_csv(tmp_path, "b.csv", "1003,2026-10-18,M,E,1,10,Bob\n1004,15.10.2026,P,E,1,5,Alex\n")
    res = run(tmp_path, "a.csv", "b.csv")
    assert res.data["Номер заказа"].tolist() == ["1001", "1003", "1004"]
    assert res.data["Менеджер"].tolist() == ["Alex", "Alex", "Alex"]
    a, b = res.file_stats
    assert (a.read, a.empty_removed, a.invalid, a.accepted) == (4, 1, 1, 2) and (b.duplicates, b.accepted) == (1, 1)
    assert res.errors.counts_by_type() == {EMPTY_FIELD: 1, DUPLICATE: 1}


def test_missing_columns_file_rejected_others_continue(tmp_path):
    write_csv(tmp_path, "a.csv", "1001,2026-10-15,K,E,2,3500,Alex\n")
    (tmp_path / "c.csv").write_text("Дата,Цена\n2026-10-15,5\n", encoding="utf-8")
    res = run(tmp_path, "c.csv", "a.csv")
    assert len(res.data) == 1 and res.file_stats[0].problem.startswith("Нет столбцов")
    assert res.errors.to_dataframe().iloc[0]["Тип ошибки"] == NO_COLUMNS


def test_unreadable_and_missing_path_reported(tmp_path):
    (tmp_path / "bad.xlsx").write_bytes(b"nope")
    res = process(discover([str(tmp_path / "bad.xlsx"), str(tmp_path / "nope.csv")]))
    assert res.data.empty and res.errors.counts_by_type() == {UNREADABLE: 2}


def test_header_only_and_blank_files_do_not_crash(tmp_path):
    write_csv(tmp_path, "h.csv", ""); (tmp_path / "e.csv").write_text("", encoding="utf-8")
    write_csv(tmp_path, "b.csv", "\n\n")
    res = run(tmp_path, "h.csv", "e.csv", "b.csv")
    assert res.data.empty and all(s.accepted == 0 for s in res.file_stats)


def test_numeric_excel_id_equals_csv_text_id(tmp_path):
    write_csv(tmp_path, "a.csv", "1001,2026-10-15,K,E,2,3500,Alex\n00123,2026-10-15,K,E,1,1,Alex\n")
    wb = openpyxl.Workbook(); ws = wb.active
    ws.append(["Номер заказа", "Дата", "Товар", "Категория", "Количество", "Цена", "Менеджер"])
    ws.append([1001, "2026-10-16", "K", "E", 1, 1, "Alex"]); wb.save(tmp_path / "b.xlsx")
    res = run(tmp_path, "a.csv", "b.xlsx")
    assert res.data["Номер заказа"].tolist() == ["1001", "00123"] and res.errors.counts_by_type() == {DUPLICATE: 1}


def test_same_file_name_in_two_folders_gets_folder_prefix(tmp_path):
    for d in ("x", "y"):
        (tmp_path / d).mkdir(); write_csv(tmp_path / d, "s.csv", "1,2026-10-15,K,E,1,1,A\n")
    res = run(tmp_path, "x/s.csv", "y/s.csv")
    assert [s.name for s in res.file_stats] == ["x/s.csv", "y/s.csv"]


def test_on_file_called_per_file_in_order(tmp_path):
    write_csv(tmp_path, "a.csv", "1,2026-10-15,K,E,1,1,A\n"); write_csv(tmp_path, "b.csv", "2,2026-10-15,K,E,1,1,A\n")
    seen = []; run(tmp_path, "a.csv", "b.csv", on_file=lambda s: seen.append(s.name))
    assert seen == ["a.csv", "b.csv"]
