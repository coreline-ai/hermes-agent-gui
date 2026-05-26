from types import SimpleNamespace

from api.config import Config
from api.exec_policy import require_exec
from api.router import Request


def _cfg(*, enabled: bool, allow_remote: bool = False) -> Config:
    return Config(
        password="test-pass",
        bearer_token=None,
        secret=b"secret",
        fake_backend="echo",
        hermes_api_url=None,
        hermes_api_token=None,
        hermes_dashboard_url=None,
        fail_open=False,
        exec_enabled=enabled,
        exec_allow_remote=allow_remote,
    )


def _req(bind_host: str) -> Request:
    raw = SimpleNamespace(
        server=SimpleNamespace(server_address=(bind_host, 8800)),
        client_address=("127.0.0.1", 12345),
    )
    return Request(method="POST", path="/api/terminal/exec", query={}, headers={}, raw=raw)


def test_exec_policy_disabled_blocks_even_loopback():
    blocked = require_exec(_req("127.0.0.1"), _cfg(enabled=False))
    assert blocked is not None
    assert blocked.body["error"] == "exec_disabled"


def test_exec_policy_enabled_allows_loopback():
    assert require_exec(_req("127.0.0.1"), _cfg(enabled=True)) is None


def test_exec_policy_remote_bind_needs_second_opt_in():
    blocked = require_exec(_req("0.0.0.0"), _cfg(enabled=True, allow_remote=False))
    assert blocked is not None
    assert blocked.body["error"] == "exec_remote_bind_disabled"

    assert require_exec(_req("0.0.0.0"), _cfg(enabled=True, allow_remote=True)) is None
