from __future__ import annotations

from pathlib import Path

from .common import Symbol
from . import go, javascript, python, rust, typescript


def parse_file(path: str, text: str) -> list[Symbol]:
    suffix = Path(path).suffix.lower()
    if suffix == ".py":
        return python.parse(path, text)
    if suffix in {".ts", ".tsx"}:
        return typescript.parse(path, text)
    if suffix in {".js", ".jsx"}:
        return javascript.parse(path, text)
    if suffix == ".go":
        return go.parse(path, text)
    if suffix == ".rs":
        return rust.parse(path, text)
    return []


__all__ = ["Symbol", "parse_file"]
