"""Типы ошибок и сборщик ошибок обработки."""
from __future__ import annotations

from collections import Counter

import pandas as pd

NO_COLUMNS = "Нет столбцов"
UNREADABLE = "Файл не прочитан"
EMPTY_FIELD = "Пустое поле"
BAD_FORMAT = "Неверный формат"
BAD_VALUE = "Недопустимое значение"
DUPLICATE = "Дубликат"

ERROR_COLUMNS = ["Файл", "Строка", "Номер заказа", "Тип ошибки", "Описание", "Исходное значение"]


class ErrorCollector:
    """Копит ошибки в порядке добавления."""

    def __init__(self) -> None:
        self._items: list[list] = []

    def add(self, file: str, row: int | None, order_id: str, kind: str,
            description: str, value: str = "") -> None:
        self._items.append([file, "" if row is None else row, order_id, kind, description, value])

    def __len__(self) -> int:
        return len(self._items)

    def counts_by_type(self) -> dict[str, int]:
        counts = Counter(item[3] for item in self._items)
        return dict(sorted(counts.items(), key=lambda kv: -kv[1]))

    def to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame(self._items, columns=ERROR_COLUMNS)
