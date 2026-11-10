"""Консольный интерфейс: отрисовка результатов (rich), аргументы и коды возврата."""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path
from typing import Sequence

from rich.console import Console
from rich.progress import BarColumn, Progress, TextColumn
from rich.table import Table
from rich.text import Text

from sales_merger.discovery import Discovery, discover
from sales_merger.errors import ErrorCollector
from sales_merger.metrics import add_revenue, compute_metrics
from sales_merger.models import FileStat, Metrics
from sales_merger.pipeline import process
from sales_merger.writer import (OutputPaths, resolve_output_paths, write_errors, write_merged,
                                 write_report)

TOP_MANAGERS = 5


def fmt_money(value: float) -> str:
    """`1234567.5` -> `1 234 567,50` (обычный пробел как разделитель тысяч)."""
    return f"{value:,.2f}".replace(",", " ").replace(".", ",")


def marks(console: Console) -> tuple[str, str]:
    """Галочки для UTF-консоли, `OK`/`ERR` для остальных кодировок (например cp1251)."""
    if (console.encoding or "").lower().startswith("utf"):
        return "✔", "✘"
    return "OK", "ERR"


def _say(console: Console, text: str, style: str | None = None) -> None:
    """Печать без разбора разметки rich (в именах файлов бывают квадратные скобки)."""
    console.print(text, style=style, markup=False, highlight=False, soft_wrap=True)


def _table(title: str, columns: Sequence[tuple[str, bool]]) -> Table:
    table = Table(title=title, title_justify="left")
    for name, right in columns:
        table.add_column(name, justify="right" if right else "left", overflow="fold")
    return table


def _cell(value: object) -> Text:
    return Text(str(value))


def render_discovery(console: Console, discovery: Discovery) -> None:
    _say(console, f"Найдено файлов: {len(discovery.files)}", "bold")
    for path in discovery.files:
        _say(console, f"  {path}")


def render_file_line(console: Console, stat: FileStat) -> None:
    ok, err = marks(console)
    if stat.problem:
        _say(console, f"{err} {stat.name}: {stat.problem}", "red")
    else:
        _say(console, f"{ok} {stat.name}: принято {stat.accepted}, отклонено {stat.invalid + stat.duplicates}", "green")


def render_cleanup(console: Console, file_stats: Sequence[FileStat]) -> None:
    good = [s for s in file_stats if not s.problem]
    table = _table("Очистка данных", [("Прочитано", True), ("Пустых удалено", True), ("С ошибками", True),
                                      ("Дублей", True), ("Принято", True)])
    table.add_row(*(_cell(sum(getattr(s, field) for s in good))
                    for field in ("read", "empty_removed", "invalid", "duplicates", "accepted")))
    console.print(table)


def render_metrics(console: Console, metrics: Metrics) -> None:
    _say(console, f"Общая выручка: {fmt_money(metrics.total_revenue)}", "bold")
    _say(console, f"Количество заказов: {metrics.orders}", "bold")
    _say(console, f"Средний чек: {fmt_money(metrics.avg_check)}", "bold")

    top = _table("Топ менеджеров", [("Менеджер", False), ("Заказы", True), ("Выручка", True), ("Доля, %", True)])
    for row in metrics.by_manager.head(TOP_MANAGERS).itertuples(index=False):
        top.add_row(_cell(row[0]), _cell(row[1]), _cell(fmt_money(row[2])), _cell(fmt_money(row[4])))
    console.print(top)

    months = _table("По месяцам", [("Месяц", False), ("Заказы", True), ("Выручка", True)])
    for row in metrics.by_month.itertuples(index=False):
        months.add_row(_cell(row[0]), _cell(row[1]), _cell(fmt_money(row[2])))
    console.print(months)


def render_errors(console: Console, errors: ErrorCollector, limit: int = 10) -> None:
    total = len(errors)
    if total == 0:
        _say(console, "Ошибок не найдено", "green")
        return
    summary = ", ".join(f"{kind}: {count}" for kind, count in errors.counts_by_type().items())
    _say(console, f"Ошибок: {total} ({summary})", "red")
    df = errors.to_dataframe().head(limit)
    table = _table("Ошибки", [(name, name == "Строка") for name in df.columns])
    for column in table.columns:
        if column.header in ("Тип ошибки", "Описание"):
            column.min_width = 13  # самое длинное слово («Недопустимое») не режется на узком терминале
    for row in df.itertuples(index=False):
        table.add_row(*(_cell(v) for v in row))
    console.print(table)
    if total > limit:
        _say(console, f"Показаны первые {limit} из {total}, остальные в файле ошибок", "yellow")


def render_outputs(console: Console, paths: OutputPaths, with_data: bool = True) -> None:
    """Пути результатов; без принятых данных создан только файл ошибок."""
    _say(console, "Результат:", "bold")
    if with_data:
        _say(console, f"  Объединённая таблица: {paths.merged}")
        _say(console, f"  Отчёт: {paths.report}")
    _say(console, f"  Ошибки: {paths.errors}")


class _Parser(argparse.ArgumentParser):
    def error(self, message: str):  # русский префикс вместо английского
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: ошибка: {message}\n")


def build_parser() -> argparse.ArgumentParser:
    parser = _Parser(
        prog="merge.py",
        usage="merge.py [-h] [-o ПАПКА] [--no-color] ПУТЬ [ПУТЬ ...]",
        description="Объединяет таблицы продаж менеджеров (.csv, .xlsx, .xls), проверяет данные "
                    "и сохраняет объединённую таблицу, отчёт с графиками и таблицу ошибок.",
        add_help=False,
    )
    args = parser.add_argument_group("Аргументы")
    args.add_argument("paths", nargs="+", metavar="ПУТЬ",
                      help="Файлы и папки с таблицами продаж (можно вперемешку)")
    options = parser.add_argument_group("Параметры")
    options.add_argument("-o", "--output", default="output", metavar="ПАПКА",
                         help="папка для результатов (по умолчанию: output)")
    options.add_argument("--no-color", action="store_true", help="не использовать цвета в консоли")
    options.add_argument("-h", "--help", action="help", help="показать эту справку и выйти")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Коды возврата: 0 всё принято, 1 что-то отклонено, 2 критическая проблема."""
    args = build_parser().parse_args(argv)
    for stream in (sys.stdout, sys.stderr):  # cp1251-консоль или файл: ₽, é и т.п. заменяются на «?»
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")
    console = Console(color_system=None if args.no_color else "auto")

    discovery = discover(args.paths)
    if not discovery.files and not discovery.problems:
        _say(console, "Файлы не найдены", "red")
        return 2
    render_discovery(console, discovery)

    total = len(discovery.files) + len(discovery.problems)
    with Progress(TextColumn("Обработка"), BarColumn(), TextColumn("{task.completed}/{task.total}"),
                  console=console, transient=True) as progress:
        task = progress.add_task("files", total=total)

        def on_file(stat: FileStat) -> None:
            render_file_line(console, stat)
            progress.advance(task)

        result = process(discovery, on_file)

    render_cleanup(console, result.file_stats)
    has_data = not result.data.empty

    try:
        out_dir = Path(args.output)
        out_dir.mkdir(parents=True, exist_ok=True)
        paths = resolve_output_paths(out_dir, date.today())
        write_errors(paths.errors, result.errors)
        if has_data:
            data = add_revenue(result.data)
            metrics = compute_metrics(data)
            write_merged(paths.merged, data)
            write_report(paths.report, metrics, result.file_stats)
    except OSError as exc:
        _say(console, f"Не удалось записать результат: {exc}", "red")
        return 2

    if has_data:
        render_metrics(console, metrics)
    else:
        _say(console, "Принятых строк нет: объединённая таблица и отчёт не созданы", "red")
    render_errors(console, result.errors)
    render_outputs(console, paths, with_data=has_data)

    if not has_data:
        return 2
    return 1 if len(result.errors) else 0
