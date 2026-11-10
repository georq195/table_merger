"""Оркестрация обработки без вывода в консоль."""
from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Callable

import pandas as pd

from sales_merger.cleaner import clean_text, drop_duplicates, drop_empty_rows, unify_managers
from sales_merger.columns import FILE_COL, REQUIRED, ROW_COL
from sales_merger.discovery import Discovery
from sales_merger.errors import NO_COLUMNS, UNREADABLE, ErrorCollector
from sales_merger.loader import LoadError, load_file
from sales_merger.models import FileStat, PipelineResult
from sales_merger.validator import MissingColumnsError, select_columns, validate_rows


def _labels(files: list[Path]) -> list[str]:
    """Имя файла; если имена совпадают, `папка/имя`."""
    counts = Counter(path.name for path in files)
    return [f"{p.parent.name}/{p.name}" if counts[p.name] > 1 else p.name for p in files]


def process(discovery: Discovery, on_file: Callable[[FileStat], None] | None = None) -> PipelineResult:
    errors = ErrorCollector()
    stats: list[FileStat] = []

    def finish(stat: FileStat) -> None:
        stats.append(stat)
        if on_file is not None:
            on_file(stat)

    for raw, reason in discovery.problems:
        errors.add(raw, None, "", UNREADABLE, reason)
        finish(FileStat(name=raw, problem=reason))

    data: pd.DataFrame | None = None
    for path, label in zip(discovery.files, _labels(discovery.files)):
        stat = FileStat(name=label)
        try:
            raw_table = load_file(path)
            table = select_columns(raw_table, label)
        except LoadError as exc:
            errors.add(label, None, "", UNREADABLE, str(exc))
            stat.problem = str(exc)
            finish(stat)
            continue
        except MissingColumnsError as exc:
            errors.add(label, None, "", NO_COLUMNS, str(exc))
            stat.problem = str(exc)
            finish(stat)
            continue

        stat.read = len(table)
        table, stat.empty_removed = drop_empty_rows(clean_text(table))
        before = len(table)
        valid = validate_rows(table, errors)
        stat.invalid = before - len(valid)

        if data is None:
            merged = valid
        elif valid.empty:
            merged = data
        else:
            merged = pd.concat([data, valid], ignore_index=True)
        previous = 0 if data is None else len(data)
        data = drop_duplicates(merged, errors)
        stat.accepted = len(data) - previous
        stat.duplicates = len(valid) - stat.accepted
        finish(stat)

    if data is None:
        empty = pd.DataFrame(columns=REQUIRED + [FILE_COL, ROW_COL])
        data = validate_rows(empty, ErrorCollector())
    return PipelineResult(data=unify_managers(data), errors=errors, file_stats=stats)
