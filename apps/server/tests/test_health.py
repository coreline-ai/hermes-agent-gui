def test_health_open(client):
    status, body = client("GET", "/api/health")
    assert status == 200
    assert body["status"] == "ok"
    assert body["phase"] == "1"
