"""Канонические столбцы, синонимы заголовков и сопоставление столбцов."""
from __future__ import annotations

import re
from typing import Sequence

REQUIRED: list[str] = [
    "Номер заказа",
    "Дата",
    "Товар",
    "Категория",
    "Количество",
    "Цена",
    "Менеджер",
]

FILE_COL = "_file"
ROW_COL = "_row"

# Английское имя всегда последнее. Спецификация (раздел 4.2) недоступна: списки для
# «Номер заказа» и «Менеджер» зафиксированы тестами плана, остальные выбраны так,
# чтобы не пересекаться между полями.
SYNONYMS: dict[str, list[str]] = {
    "Номер заказа": ["Номер заказа", "№ заказа", "ID заказа", "order_id"],
    "Дата": ["Дата", "Дата заказа", "date"],
    "Товар": ["Товар", "Наименование", "Название товара", "product"],
    "Категория": ["Категория", "category"],
    "Количество": ["Количество", "Кол-во", "quantity"],
    "Цена": ["Цена", "Цена за единицу", "price"],
    "Менеджер": ["Менеджер", "Сотрудник", "manager"],
}

_SPACES = re.compile(r"\s+")


def normalize_header(text: str) -> str:
    """Без краевых пробелов, без регистра, «ё» как «е», пробелы схлопнуты."""
    text = str(text).strip().casefold().replace("ё", "е")
    return _SPACES.sub(" ", text)


_LOOKUP: dict[str, str] = {
    normalize_header(name): field
    for field, names in SYNONYMS.items()
    for name in names
}


def map_columns(columns: Sequence[str]) -> tuple[dict[str, str], list[str]]:
    """(исходный заголовок -> каноническое имя, недостающие имена в порядке REQUIRED).

    Если одно поле встретилось в нескольких столбцах, побеждает первый.
    """
    mapping: dict[str, str] = {}
    seen: set[str] = set()
    for col in columns:
        field = _LOOKUP.get(normalize_header(col))
        if field is None or field in seen:
            continue
        mapping[col] = field
        seen.add(field)
    missing = [f for f in REQUIRED if f not in seen]
    return mapping, missing
