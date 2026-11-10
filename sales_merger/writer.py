"""Запись выходных файлов Excel: имена, таблицы, отчёт."""
from __future__ import annotations

import datetime
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd
from openpyxl import Workbook
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from sales_merger.columns import REQUIRED
from sales_merger.errors import ERROR_COLUMNS, ErrorCollector
from sales_merger.models import FileStat, Metrics

MERGED_COLUMNS = REQUIRED + ["Выручка"]

MONEY_FORMAT = "#,##0.00"
INTEGER_FORMAT = "#,##0"
PERCENT_FORMAT = "0.00"
DATE_FORMAT = "yyyy-mm-dd"
HEADER_FILL = PatternFill("solid", fgColor="D9E1F2")
MAX_WIDTH = 60


@dataclass(frozen=True)
class OutputPaths:
    merged: Path
    report: Path
    errors: Path


def resolve_output_paths(out_dir: Path, today: datetime.date) -> OutputPaths:
    """Общий суффикс `_2`, `_3`, ... для трёх файлов: наименьший, при котором ни одного нет.

    Ничего не создаёт на диске.
    """
    out_dir = Path(out_dir)
    stamp = today.isoformat()
    number = 1
    while True:
        suffix = "" if number == 1 else f"_{number}"
        paths = OutputPaths(
            merged=out_dir / f"merged_sales_{stamp}{suffix}.xlsx",
            report=out_dir / f"report_{stamp}{suffix}.xlsx",
            errors=out_dir / f"errors_{stamp}{suffix}.xlsx",
        )
        if not (paths.merged.exists() or paths.report.exists() or paths.errors.exists()):
            return paths
        number += 1


def _to_python(value):
    """numpy/pandas значения в обычные типы Python; NaN и NaT в None."""
    if value is None or value is pd.NaT:
        return None
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    if hasattr(value, "item") and not isinstance(value, (str, bytes)):
        value = value.item()
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def _display_length(value, number_format: str | None) -> int:
    if value is None:
        return 0
    if isinstance(value, datetime.datetime):
        return 10
    if isinstance(value, float) and number_format in (MONEY_FORMAT, PERCENT_FORMAT):
        return len(f"{value:,.2f}")
    if isinstance(value, (int, float)) and not isinstance(value, bool) and number_format == INTEGER_FORMAT:
        return len(f"{value:,.0f}")
    return len(str(value))


def write_table(ws, df: pd.DataFrame, *, money: Iterable[str] = (), integer: Iterable[str] = (),
                percent: Iterable[str] = (), dates: Iterable[str] = (), start_row: int = 1) -> None:
    """Шапка и строки таблицы с форматированием; автоширина (не уже уже заданной)."""
    formats: dict[str, str] = {}
    formats.update({c: MONEY_FORMAT for c in money})
    formats.update({c: INTEGER_FORMAT for c in integer})
    formats.update({c: PERCENT_FORMAT for c in percent})
    formats.update({c: DATE_FORMAT for c in dates})

    columns = list(df.columns)
    widths = [len(str(c)) for c in columns]
    for idx, name in enumerate(columns, start=1):
        cell = ws.cell(start_row, idx, name)
        cell.font = Font(name="Calibri", size=11, bold=True)
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="left")

    for offset, record in enumerate(df.itertuples(index=False, name=None), start=1):
        for idx, (name, raw) in enumerate(zip(columns, record), start=1):
            value = _to_python(raw)
            if isinstance(value, str):
                value = ILLEGAL_CHARACTERS_RE.sub("", value)
            cell = ws.cell(start_row + offset, idx, value)
            if isinstance(value, str):
                cell.data_type = "s"  # «=1+1» из данных не должно стать формулой
            fmt = formats.get(name)
            if fmt:
                cell.number_format = fmt
            numeric = isinstance(value, (int, float, datetime.datetime)) and not isinstance(value, bool)
            cell.alignment = Alignment(horizontal="right" if numeric else "left")
            widths[idx - 1] = max(widths[idx - 1], _display_length(value, fmt))

    for idx, width in enumerate(widths, start=1):
        letter = get_column_letter(idx)
        current = ws.column_dimensions[letter].width if letter in ws.column_dimensions else None
        ws.column_dimensions[letter].width = max(min(width + 2, MAX_WIDTH), current or 0)

    if start_row == 1:
        ws.freeze_panes = "A2"


def write_merged(path: Path, df: pd.DataFrame) -> None:
    """Лист «Продажи» со столбцами MERGED_COLUMNS (служебные столбцы отбрасываются)."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Продажи"
    write_table(ws, df[MERGED_COLUMNS], money=("Цена", "Выручка"), integer=("Количество",), dates=("Дата",))
    wb.save(path)


def write_errors(path: Path, errors: ErrorCollector) -> None:
    """Лист «Ошибки»; без ошибок единственная строка «Ошибок нет» в столбце «Описание»."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Ошибки"
    df = errors.to_dataframe()
    if df.empty:
        df = pd.DataFrame([["", "", "", "", "Ошибок нет", ""]], columns=ERROR_COLUMNS)
    write_table(ws, df)
    wb.save(path)


def _add_chart(ws, chart, df: pd.DataFrame, anchor: str, title: str, x_title: str) -> None:
    """Общая настройка графика выручки: данные из столбца «Выручка», подписи из первого столбца."""
    last = len(df) + 1
    value_col = list(df.columns).index("Выручка") + 1
    chart.title = title
    chart.x_axis.title = x_title
    chart.y_axis.title = "Выручка"
    chart.x_axis.delete = False
    chart.y_axis.delete = False
    chart.add_data(Reference(ws, min_col=value_col, min_row=1, max_row=last), titles_from_data=True)
    chart.set_categories(Reference(ws, min_col=1, min_row=2, max_row=last))
    chart.legend = None
    chart.width, chart.height = 18, 9
    ws.add_chart(chart, anchor)


def write_report(path: Path, metrics: Metrics, file_stats: list[FileStat]) -> None:
    """Листы «Сводка», «По менеджерам» (график-столбцы), «По месяцам» (линейный график)."""
    wb = Workbook()

    summary = wb.active
    summary.title = "Сводка"
    rows = [
        ("Общая выручка", metrics.total_revenue, MONEY_FORMAT),
        ("Количество заказов", metrics.orders, INTEGER_FORMAT),
        ("Средний чек", metrics.avg_check, MONEY_FORMAT),
        ("Период данных", f"{metrics.period_start.isoformat()} — {metrics.period_end.isoformat()}", None),
        ("Обработано файлов", sum(1 for s in file_stats if not s.problem), INTEGER_FORMAT),
        ("Строк принято", sum(s.accepted for s in file_stats), INTEGER_FORMAT),
        ("Строк отклонено", sum(s.invalid + s.duplicates for s in file_stats), INTEGER_FORMAT),
    ]
    frame = pd.DataFrame({"Показатель": [r[0] for r in rows], "Значение": pd.Series([r[1] for r in rows], dtype="object")})
    write_table(summary, frame)
    for offset, (_, _, fmt) in enumerate(rows, start=2):
        if fmt:
            summary.cell(offset, 2).number_format = fmt

    by_manager = wb.create_sheet("По менеджерам")
    write_table(by_manager, metrics.by_manager, money=("Выручка", "Средний чек"), integer=("Заказы",),
                percent=("Доля выручки, %",))
    _add_chart(by_manager, BarChart(), metrics.by_manager, "H2", "Выручка по менеджерам", "Менеджер")

    by_month = wb.create_sheet("По месяцам")
    write_table(by_month, metrics.by_month, money=("Выручка", "Средний чек"), integer=("Заказы",))
    _add_chart(by_month, LineChart(), metrics.by_month, "G2", "Выручка по месяцам", "Месяц")

    wb.save(path)
