from __future__ import annotations

from api.marketplace.store import load_catalog


def test_catalog_has_30_to_50_presets():
    items = load_catalog()
    assert 30 <= len(items) <= 50
    assert all({"id", "label", "category", "soul_md", "skills", "tags"}.issubset(item) for item in items)


def test_install_creates_profile_and_conflict(client):
    client("POST", "/api/auth/login", body={"password": "test-pass"})
    status, body = client("GET", "/api/marketplace/catalog")
    assert status == 200
    preset_id = body["items"][0]["id"]
    status, body = client("POST", f"/api/marketplace/{preset_id}/install", body={})
    assert status == 201
    assert body["profile"].startswith("market-")
    status, body = client("POST", f"/api/marketplace/{preset_id}/install", body={})
    assert status == 409
    assert body["error"] == "already_installed"
