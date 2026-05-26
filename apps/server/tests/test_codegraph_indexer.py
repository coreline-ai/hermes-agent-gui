from __future__ import annotations

from api.codegraph.parsers import parse_file
from api.codegraph.watcher import Debouncer


def test_python_symbols_extracted():
    symbols = parse_file("x.py", "CONST = 1\nclass Foo:\n    def bar(self):\n        pass\ndef baz():\n    pass\n")
    names = {(s.name, s.kind) for s in symbols}
    assert ("Foo", "class") in names
    assert ("bar", "function") in names
    assert ("baz", "function") in names
    assert ("CONST", "const") in names


def test_typescript_interface_type_function():
    symbols = parse_file("x.ts", "interface User {}\ntype ID = string\nexport function run() {}\nconst useIsMobile = () => true\n")
    names = {s.name for s in symbols}
    assert {"User", "ID", "run", "useIsMobile"}.issubset(names)


def test_codegraph_routes_find_definition(client, tmp_path, monkeypatch):
    ws = tmp_path / "ws"
    ws.mkdir(exist_ok=True)
    (ws / "app.py").write_text("def useIsMobile():\n    return False\n", encoding="utf-8")
    client("POST", "/api/auth/login", body={"password": "test-pass"})
    status, body = client("POST", "/api/codegraph/index", body={"root": "."})
    assert status == 200
    assert body["symbols"] >= 1
    status, body = client("GET", "/api/codegraph/definition?symbol=useIsMobile")
    assert status == 200
    assert body["name"] == "useIsMobile"


def test_watcher_debounce():
    d = Debouncer(delay_ms=500)
    assert d.touch() is True
    assert d.touch() is False
