"""Общие типы данных конвейера."""
from __future__ import annotations

import datetime
from dataclasses import dataclass

import pandas as pd

from sales_merger.errors import ErrorCollector


@dataclass
class FileStat:
    """Итоги по одному файлу; `problem` не пуст, если файл отклонён целиком."""

    name: str
    read: int = 0
    empty_removed: int = 0
    invalid: int = 0
    duplicates: int = 0
    accepted: int = 0
    problem: str = ""


@dataclass
class PipelineResult:
    data: pd.DataFrame
    errors: ErrorCollector
    file_stats: list[FileStat]


@dataclass
class Metrics:
    total_revenue: float
    orders: int
    avg_check: float
    by_manager: pd.DataFrame
    by_month: pd.DataFrame
    period_start: datetime.date
    period_end: datetime.date
