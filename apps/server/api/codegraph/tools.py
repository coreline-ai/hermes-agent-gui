from __future__ import annotations

from .store import file_outline, find_symbols


def find_definition(symbol: str) -> dict | None:
    rows = find_symbols(symbol, limit=10)
    exact = [r for r in rows if r["name"] == symbol]
    return (exact or rows or [None])[0]


def find_references(symbol: str) -> list[dict]:
    return find_symbols(symbol, limit=50)


def find_implementations(symbol: str) -> list[dict]:
    return find_symbols(symbol, limit=50)


def get_file_outline(file: str) -> list[dict]:
    return file_outline(file)
