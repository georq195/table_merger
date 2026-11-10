"""Поиск входных файлов по списку файлов и папок."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

SUPPORTED_SUFFIXES = (".csv", ".xlsx", ".xls")
LOCK_PREFIX = "~$"


@dataclass
class Discovery:
    files: list[Path] = field(default_factory=list)
    problems: list[tuple[str, str]] = field(default_factory=list)  # (путь как указан, причина)


def _supported(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_SUFFIXES


def discover(paths: Sequence[str]) -> Discovery:
    result = Discovery()
    seen: set[Path] = set()

    def add(path: Path) -> None:
        key = path.resolve()
        if key not in seen:
            seen.add(key)
            result.files.append(path)

    for raw in paths:
        path = Path(raw)
        if path.is_dir():
            children = [
                p for p in path.iterdir()
                if p.is_file() and _supported(p) and not p.name.startswith(LOCK_PREFIX)
            ]
            for child in sorted(children, key=lambda p: p.name.casefold()):
                add(child)
        elif path.is_file():
            if _supported(path):
                add(path)
            else:
                result.problems.append((raw, "неподдерживаемый формат файла"))
        else:
            result.problems.append((raw, "путь не найден"))
    return result
