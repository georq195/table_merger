import io

from rich.console import Console

from sales_merger.cli import (fmt_money, marks, render_cleanup, render_discovery, render_errors,
                              render_file_line, render_metrics, render_outputs)
from sales_merger.discovery import Discovery
from sales_merger.errors import EMPTY_FIELD, ErrorCollector
from sales_merger.models import FileStat
from sales_merger.writer import OutputPaths
from tests.helpers import sample_metrics, sample_stats
from pathlib import Path


def console():
    return Console(record=True, width=140, color_system=None)


def test_fmt_money():
    assert fmt_money(1234567.5) == "1 234 567,50" and fmt_money(0) == "0,00"


def test_render_metrics_text():
    c = console(); render_metrics(c, sample_metrics())
    t = c.export_text()
    assert "9 500,00" in t and "Alex" in t and "2026-11" in t


def test_render_errors_limit_and_summary():
    e = ErrorCollector()
    for i in range(12): e.add("a.csv", i + 2, str(i), EMPTY_FIELD, "Поле «Цена» не заполнено")
    c = console(); render_errors(c, e)
    t = c.export_text()
    assert "Пустое поле: 12" in t and "Показаны первые 10 из 12" in t and t.count("Поле «Цена» не заполнено") == 10


def test_render_errors_none():
    c = console(); render_errors(c, ErrorCollector())
    assert "Ошибок не найдено" in c.export_text()


def test_render_errors_no_overflow_note_when_within_limit():
    e = ErrorCollector(); e.add("a.csv", 2, "1", EMPTY_FIELD, "x")
    c = console(); render_errors(c, e)
    assert "Показаны первые" not in c.export_text()


def test_file_lines():
    c = console()
    render_file_line(c, FileStat("a.csv", read=5, accepted=3, invalid=2))
    render_file_line(c, FileStat("old.xls", problem="Нет столбцов: Цена"))
    t = c.export_text()
    assert "a.csv: принято 3, отклонено 2" in t and "old.xls: Нет столбцов: Цена" in t


def test_brackets_in_file_names_are_not_markup():
    c = console(); render_file_line(c, FileStat("[red]x[/red].csv", accepted=1))
    assert "[red]x[/red].csv" in c.export_text()


def test_render_cleanup_sums_only_files_without_problem():
    c = console(); render_cleanup(c, sample_stats())
    t = c.export_text()
    assert "Принято" in t and "3" in t


def test_render_discovery_and_outputs():
    c = console()
    render_discovery(c, Discovery(files=[Path("a.csv"), Path("b.xlsx")]))
    render_outputs(c, OutputPaths(Path("o/m.xlsx"), Path("o/r.xlsx"), Path("o/e.xlsx")))
    t = c.export_text()
    assert "a.csv" in t and "b.xlsx" in t and "o/m.xlsx" in t and "o/r.xlsx" in t and "o/e.xlsx" in t


def test_cp1251_console_does_not_crash():
    buf = io.BytesIO(); f = io.TextIOWrapper(buf, encoding="cp1251")
    c = Console(file=f, width=140, color_system=None)
    render_file_line(c, FileStat("a.csv", read=1, accepted=1)); f.flush()
    assert b"OK" in buf.getvalue() and marks(c) == ("OK", "ERR")


def test_cp1251_console_tables_do_not_crash():
    buf = io.BytesIO(); f = io.TextIOWrapper(buf, encoding="cp1251")
    c = Console(file=f, width=140, color_system=None)
    e = ErrorCollector(); e.add("a.csv", 2, "1", EMPTY_FIELD, "Поле «Цена» не заполнено")
    render_metrics(c, sample_metrics()); render_cleanup(c, sample_stats()); render_errors(c, e); f.flush()
    assert buf.getvalue()


def test_render_outputs_without_data_lists_only_errors_file():
    c = console()
    render_outputs(c, OutputPaths(Path("o/m.xlsx"), Path("o/r.xlsx"), Path("o/e.xlsx")), with_data=False)
    t = c.export_text()
    assert "o/e.xlsx" in t and "o/m.xlsx" not in t and "o/r.xlsx" not in t
