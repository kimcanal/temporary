"""party_size validation + the admin reservations dashboard (list + arbitrary cancel)."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from tests.conftest import auth_header

KST = ZoneInfo("Asia/Seoul")


def _tomorrow_at(hour: int, minute: int = 0) -> datetime:
    base = datetime.now(KST).date() + timedelta(days=1)
    return datetime(base.year, base.month, base.day, hour, minute, tzinfo=KST)


def test_party_size_defaults_to_one(client):
    h1 = auth_header(client, "u1@test.com")
    start, end = _tomorrow_at(9, 0), _tomorrow_at(10, 0)
    r = client.post(
        "/api/reservations",
        json={"space_id": client.space_id, "start_at": start.isoformat(), "end_at": end.isoformat()},
        headers=h1,
    )
    assert r.status_code == 201, r.text
    assert r.json()["party_size"] == 1


def test_party_size_over_capacity_rejected(client):
    """Test Room's capacity is 4 (see conftest.py)."""
    h1 = auth_header(client, "u1@test.com")
    start, end = _tomorrow_at(9, 0), _tomorrow_at(10, 0)
    r = client.post(
        "/api/reservations",
        json={
            "space_id": client.space_id,
            "start_at": start.isoformat(),
            "end_at": end.isoformat(),
            "party_size": 5,
        },
        headers=h1,
    )
    assert r.status_code == 400, r.text


def test_party_size_zero_rejected_by_schema(client):
    h1 = auth_header(client, "u1@test.com")
    start, end = _tomorrow_at(9, 0), _tomorrow_at(10, 0)
    r = client.post(
        "/api/reservations",
        json={
            "space_id": client.space_id,
            "start_at": start.isoformat(),
            "end_at": end.isoformat(),
            "party_size": 0,
        },
        headers=h1,
    )
    assert r.status_code == 422


def test_admin_reservations_list_requires_admin(client):
    h1 = auth_header(client, "u1@test.com")
    day = _tomorrow_at(0, 0).date().isoformat()
    r = client.get(f"/api/admin/reservations?date={day}", headers=h1)
    assert r.status_code == 403


def test_admin_reservations_list_shows_name_and_party_size(client):
    h1 = auth_header(client, "u1@test.com")
    h_admin = auth_header(client, "admin", "admin")
    start, end = _tomorrow_at(13, 0), _tomorrow_at(14, 0)
    booked = client.post(
        "/api/reservations",
        json={
            "space_id": client.space_id,
            "start_at": start.isoformat(),
            "end_at": end.isoformat(),
            "party_size": 3,
        },
        headers=h1,
    )
    assert booked.status_code == 201, booked.text

    day = start.date().isoformat()
    listing = client.get(f"/api/admin/reservations?date={day}", headers=h_admin)
    assert listing.status_code == 200, listing.text
    rows = listing.json()
    row = next(r for r in rows if r["id"] == booked.json()["id"])
    assert row["party_size"] == 3
    assert row["user_name"] == "User One"
    assert row["space_name"] == "Test Room"


def test_admin_can_cancel_any_users_reservation(client):
    h1 = auth_header(client, "u1@test.com")
    h_admin = auth_header(client, "admin", "admin")
    start, end = _tomorrow_at(15, 0), _tomorrow_at(16, 0)
    booked = client.post(
        "/api/reservations",
        json={"space_id": client.space_id, "start_at": start.isoformat(), "end_at": end.isoformat()},
        headers=h1,
    )
    rid = booked.json()["id"]

    cancelled = client.post(f"/api/reservations/{rid}/cancel", headers=h_admin)
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["status"] == "cancelled"
