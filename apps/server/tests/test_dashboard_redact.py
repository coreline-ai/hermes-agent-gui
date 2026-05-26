from api.dashboard import _redact


def test_redact_openai_style_key():
    out = _redact("found token sk-abc123def456ghi789 in logs")
    assert "sk-abc123" not in out
    assert "***" in out


def test_redact_bearer():
    out = _redact("Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.abc.def")
    assert "eyJhbGciOiJIUzI1NiJ9.abc.def" not in out
    assert "***" in out


def test_redact_api_key_assignment():
    out = _redact('api_key: "abcdefghijklmnop"')
    assert "abcdefghijklmnop" not in out


def test_redact_aws_access_key():
    out = _redact("creds: AKIAIOSFODNN7EXAMPLE rest")
    assert "AKIAIOSFODNN7EXAMPLE" not in out


def test_redact_jwt():
    out = _redact("token=eyJabc12345.payload12345.signature12345 next")
    assert "eyJabc12345" not in out


def test_redact_github_pat():
    out = _redact("env: GH_TOKEN=ghp_abcdefghijklmnopqrstuv12345")
    assert "ghp_abcdefghijklmnopqrstuv12345" not in out


def test_redact_anthropic_key():
    key = "sk-ant-api03-abcdefghij1234567890_KLMNOPQRST-uvwxyz"
    out = _redact(f"anthropic {key} done")
    assert key not in out


def test_redact_pem_block():
    pem = (
        "-----BEGIN PRIVATE KEY-----\n"
        "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAxyz\n"
        "-----END PRIVATE KEY-----\n"
    )
    out = _redact("before " + pem + "after")
    assert "MIIBIjAN" not in out
    assert "before" in out and "after" in out


def test_redact_db_connection_string():
    out = _redact("dsn: postgres://user:supersecret@host:5432/db")
    assert "supersecret" not in out
    assert "postgres://user" in out


def test_dashboard_endpoints(client):
    client("POST", "/api/auth/login", body={"password": "test-pass"})
    for path in ("/api/dashboard", "/api/health/agent", "/api/health/system", "/api/inspector/logs"):
        status, body = client("GET", path)
        assert status == 200, path
        assert isinstance(body, dict)
