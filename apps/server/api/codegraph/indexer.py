from __future__ import annotations

import os
import time
from pathlib import Path

from .parsers import parse_file
from .store import replace_file_symbols

SUPPORTED = {".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs"}
MAX_FILE_BYTES = 1_000_000


def index_path(root: str) -> dict:
    start = time.time()
    root_path = Path(root).expanduser().resolve()
    files = 0
    symbols = 0
    skipped = 0
    for path in root_path.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED:
            continue
        if any(part in {"node_modules", "dist", ".git", "__pycache__"} for part in path.parts):
            continue
        try:
            if path.stat().st_size > MAX_FILE_BYTES:
                skipped += 1
                continue
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            skipped += 1
            continue
        rel = os.fspath(path)
        found = parse_file(rel, text)
        replace_file_symbols(rel, found)
        files += 1
        symbols += len(found)
    return {"root": str(root_path), "files": files, "symbols": symbols, "skipped": skipped, "elapsed_ms": int((time.time() - start) * 1000)}
