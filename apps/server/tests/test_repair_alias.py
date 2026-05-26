from api.sessions.compression import register_alias, alias_resolve
from api.sessions.lifecycle import Message, Session
from api.sessions.recovery import session_health, _has_tool_evidence


def _mk(messages):
    return Session(
        id="s1", title="t", profile="default",
        created_at=0, updated_at=0, messages=messages,
    )


def test_drift_browser_ahead_detected():
    s = _mk([Message(role="user", content="a"), Message(role="assistant", content="b")])
    browser = [
        Message(role="user", content="a"),
        Message(role="assistant", content="b"),
        Message(role="user", content="c"),
    ]
    rpt = session_health(s, browser, compact_context_count=1)
    assert rpt.drift is True
    assert rpt.drift_kind == "browser_ahead"


def test_drift_server_ahead_detected():
    s = _mk([
        Message(role="user", content="a"),
        Message(role="assistant", content="b"),
        Message(role="user", content="c"),
    ])
    browser = [Message(role="user", content="a"), Message(role="assistant", content="b")]
    rpt = session_health(s, browser, compact_context_count=None)
    assert rpt.drift is True
    assert rpt.drift_kind == "server_ahead"


def test_drift_compact_stale():
    s = _mk([Message(role="user", content="a"), Message(role="user", content="c")])
    rpt = session_health(s, browser_messages=None, compact_context_count=0)
    assert rpt.drift is True
    assert rpt.drift_kind == "compact_stale"


def test_tool_evidence_helper():
    assert _has_tool_evidence([Message(role="tool", content="t")])
    assert _has_tool_evidence([Message(role="assistant", content="x", tool_calls=[{"name": "f"}])])
    assert not _has_tool_evidence([Message(role="user", content="x")])


def test_compression_alias_resolves():
    register_alias("old-1", "new-1")
    register_alias("new-1", "new-2")
    assert alias_resolve("old-1") == "new-2"
    # Unknown ids pass through unchanged.
    assert alias_resolve("unknown") == "unknown"
