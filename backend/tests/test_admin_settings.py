"""Admin-tunable business rules: auth gating + that changes actually take effect."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from tests.conftest import auth_header

KST = ZoneInfo("Asia/Seoul")


def _tomorrow_at(hour: int, minute: int = 0) -> datetime:
    base = datetime.now(KST).date() + timedelta(days=1)
    return datetime(base.year, base.month, base.day, hour, minute, tzinfo=KST)


def test_get_settings_requires_auth(client):
    r = client.get("/api/admin/settings")
    assert r.status_code == 401


def test_get_settings_returns_seeded_defaults(client):
    h1 = auth_header(client, "u1@test.com")
    r = client.get("/api/admin/settings", headers=h1)
    assert r.status_code == 200, r.text
    assert r.json() == {"daily_limit_hours": 2.0, "slot_minutes": 30, "checkin_grace_minutes": 15}


def test_update_settings_requires_admin(client):
    h1 = auth_header(client, "u1@test.com")
    r = client.put(
        "/api/admin/settings",
        json={"daily_limit_hours": 1.0, "slot_minutes": 30, "checkin_grace_minutes": 15},
        headers=h1,
    )
    assert r.status_code == 403


def test_update_settings_validation_rejects_bad_values(client):
    h_admin = auth_header(client, "admin", "admin")
    r = client.put(
        "/api/admin/settings",
        json={"daily_limit_hours": 0, "slot_minutes": 30, "checkin_grace_minutes": 15},
        headers=h_admin,
    )
    assert r.status_code == 422


def test_admin_changing_daily_limit_is_enforced_on_new_bookings(client):
    h_admin = auth_header(client, "admin", "admin")
    h1 = auth_header(client, "u1@test.com")

    r = client.put(
        "/api/admin/settings",
        json={"daily_limit_hours": 1.0, "slot_minutes": 30, "checkin_grace_minutes": 15},
        headers=h_admin,
    )
    assert r.status_code == 200, r.text
    assert r.json()["daily_limit_hours"] == 1.0

    start, end = _tomorrow_at(10, 0), _tomorrow_at(11, 30)  # 1.5h > new 1h limit
    over = client.post(
        "/api/reservations",
        json={"space_id": client.space_id, "start_at": start.isoformat(), "end_at": end.isoformat()},
        headers=h1,
    )
    assert over.status_code == 400, over.text

    ok = client.post(
        "/api/reservations",
        json={
            "space_id": client.space_id,
            "start_at": start.isoformat(),
            "end_at": _tomorrow_at(11, 0).isoformat(),
        },
        headers=h1,
    )
    assert ok.status_code == 201, ok.text
