from __future__ import annotations

import ast

from .common import Symbol


def parse(path: str, text: str) -> list[Symbol]:
    out: list[Symbol] = []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return out
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            out.append(Symbol(node.name, "class", path, node.lineno, node.col_offset + 1))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out.append(Symbol(node.name, "function", path, node.lineno, node.col_offset + 1))
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.isupper():
                    out.append(Symbol(target.id, "const", path, node.lineno, node.col_offset + 1))
    return out
