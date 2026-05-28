def test_health_open(client):
    status, body = client("GET", "/api/health")
    assert status == 200
    assert body["status"] == "ok"
    assert body["phase"] == "1"


def test_build_router_is_idempotent(monkeypatch, tmp_path):
    monkeypatch.setenv("HERMES_GUI_PASSWORD", "test-pass")
    monkeypatch.setenv("HERMES_GUI_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("HERMES_GUI_FAKE_BACKEND", "echo")

    from api import config
    from server import build_router

    cfg = config.load()
    first = build_router(cfg)
    second = build_router(cfg)
    assert len(list(first.routes())) == len(list(second.routes()))
