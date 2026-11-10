import datetime as dt

from sales_merger.writer import resolve_output_paths

D = dt.date(2026, 11, 9)


def test_first_run_no_suffix(tmp_path):
    p = resolve_output_paths(tmp_path, D)
    assert p.report.name == "report_2026-11-09.xlsx" and p.merged.name == "merged_sales_2026-11-09.xlsx" and p.errors.name == "errors_2026-11-09.xlsx"


def test_existing_file_bumps_all_three(tmp_path):
    (tmp_path / "report_2026-11-09.xlsx").write_text("x")
    p = resolve_output_paths(tmp_path, D)
    assert {p.merged.name, p.report.name, p.errors.name} == {"merged_sales_2026-11-09_2.xlsx", "report_2026-11-09_2.xlsx", "errors_2026-11-09_2.xlsx"}


def test_smallest_free_number(tmp_path):
    (tmp_path / "merged_sales_2026-11-09.xlsx").write_text("x"); (tmp_path / "errors_2026-11-09_2.xlsx").write_text("x")
    assert resolve_output_paths(tmp_path, D).report.name == "report_2026-11-09_3.xlsx"


def test_missing_folder_not_created(tmp_path):
    resolve_output_paths(tmp_path / "new", D)
    assert not (tmp_path / "new").exists()
