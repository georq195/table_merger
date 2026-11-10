import shutil
from datetime import date

import openpyxl
import pytest

from sales_merger.cli import main
from tests.helpers import write_csv, write_xlsx


def test_end_to_end_mixed_inputs(tmp_path, capsys):
    folder = tmp_path / "sales"; folder.mkdir()
    write_csv(folder, "alex.csv", "1001,2026-10-15,K,E,2,3500,Alex\n1002,2026-10-16,M,E,1,,Alex\n")
    write_xlsx(folder, "maria.xlsx", [[1003, "2026-11-02", "P", "E", 1, 1000, "Maria"], [1001, "2026-11-03", "K", "E", 1, 1, "Maria"]])
    shutil.copy("tests/data/sample.xls", tmp_path / "old.xls")
    out = tmp_path / "out"
    code = main([str(folder), str(tmp_path / "old.xls"), "-o", str(out), "--no-color"])
    names = sorted(p.name for p in out.iterdir()); today = date.today().isoformat()
    assert code == 1 and names == [f"errors_{today}.xlsx", f"merged_sales_{today}.xlsx", f"report_{today}.xlsx"]
    merged = openpyxl.load_workbook(out / f"merged_sales_{today}.xlsx").active
    assert merged.max_row == 1 + 3          # принято: 1001 (alex.csv), 1003 (maria.xlsx), 1002 (sample.xls)
    errs = openpyxl.load_workbook(out / f"errors_{today}.xlsx").active
    assert errs.max_row == 1 + 3            # пустая цена 1002 (alex.csv), дубли 1001 в maria.xlsx и sample.xls
    assert "Общая выручка" in capsys.readouterr().out


def test_second_run_same_day_gets_suffix(tmp_path):
    write_csv(tmp_path, "a.csv", "1,2026-10-15,K,E,1,1,A\n")
    main([str(tmp_path / "a.csv"), "-o", str(tmp_path / "o")]); main([str(tmp_path / "a.csv"), "-o", str(tmp_path / "o")])
    assert len([p for p in (tmp_path / "o").iterdir() if p.stem.endswith("_2")]) == 3


def test_clean_run_returns_zero_and_empty_errors_file(tmp_path):
    write_csv(tmp_path, "a.csv", "1,2026-10-15,K,E,1,1,A\n")
    assert main([str(tmp_path / "a.csv"), "-o", str(tmp_path / "o")]) == 0
    errs = openpyxl.load_workbook(next((tmp_path / "o").glob("errors_*.xlsx"))).active
    assert errs.cell(2, 5).value == "Ошибок нет"


def test_no_valid_rows_returns_two_and_only_errors_file(tmp_path):
    write_csv(tmp_path, "a.csv", "1,2026-10-15,K,E,-1,1,A\n"); write_csv(tmp_path, "h.csv", "")
    code = main([str(tmp_path / "a.csv"), str(tmp_path / "h.csv"), "-o", str(tmp_path / "o")])
    assert code == 2 and [p.name.split("_")[0] for p in (tmp_path / "o").iterdir()] == ["errors"]


def test_no_files_found_returns_two(tmp_path):
    assert main([str(tmp_path), "-o", str(tmp_path / "o")]) == 2 and not (tmp_path / "o").exists()


def test_unwritable_output_returns_two(tmp_path, capsys):
    write_csv(tmp_path, "a.csv", "1,2026-10-15,K,E,1,1,A\n"); blocker = tmp_path / "file"; blocker.write_text("x")
    assert main([str(tmp_path / "a.csv"), "-o", str(blocker / "sub")]) == 2
    assert "Traceback" not in capsys.readouterr().out


def test_help_is_russian(capsys):
    with pytest.raises(SystemExit): main(["-h"])
    assert "Файлы" in capsys.readouterr().out


def test_strict_cp1251_stdout_does_not_crash_on_unencodable_text(tmp_path, monkeypatch):
    import io, sys
    folder = tmp_path / "café"; folder.mkdir()
    write_csv(folder, "café.csv", "1,2026-10-15,K,E,1,3500 ₽,Al€x\n2,2026-10-16,K,E,1,1,A\n")
    buf = io.BytesIO(); f = io.TextIOWrapper(buf, encoding="cp1251")
    monkeypatch.setattr(sys, "stdout", f)
    code = main([str(folder), "-o", str(tmp_path / "o"), "--no-color"])
    f.flush()
    assert code == 1 and b"OK" in buf.getvalue()
