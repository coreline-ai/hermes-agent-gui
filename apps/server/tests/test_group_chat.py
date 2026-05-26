from __future__ import annotations

from api.groups.models import Group, GroupParticipant
from api.groups.routing import route_message


def test_mention_routing():
    group = Group("g", "room", "ABCDEFGH", 9999999999, 0, [GroupParticipant("Researcher"), GroupParticipant("Coder")])
    assert route_message(group, "@Researcher please") is not None
    assert route_message(group, "@Researcher please").name == "Researcher"  # type: ignore[union-attr]
    assert route_message(group, "@Unknown please").name == "Researcher"  # type: ignore[union-attr]
    assert route_message(group, "no mention").name == "Researcher"  # type: ignore[union-attr]


def test_group_routes_and_participant_limit(client):
    client("POST", "/api/auth/login", body={"password": "test-pass"})
    too_many = [{"name": f"P{i}"} for i in range(11)]
    status, body = client("POST", "/api/groups", body={"name": "too", "participants": too_many})
    assert status == 400
    assert body["error"] == "too_many_participants"

    status, group = client("POST", "/api/groups", body={"name": "room", "participants": [{"name": "Researcher"}, {"name": "Coder"}]})
    assert status == 201
    status, routed = client("POST", f"/api/groups/{group['id']}/messages", body={"content": "@Coder implement"})
    assert status == 200
    assert routed["routed_to"]["name"] == "Coder"
