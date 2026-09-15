"""Domain tests: boundary overlaps must 409; adjacent slots OK."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from tests.conftest import auth_header

KST = ZoneInfo("Asia/Seoul")


def _tomorrow_at(hour: int, minute: int = 0) -> datetime:
    # Pick a weekday tomorrow so slots are in the future relative to "now"
    base = datetime.now(KST).date() + timedelta(days=1)
    return datetime(base.year, base.month, base.day, hour, minute, tzinfo=KST)


def test_exact_overlap_returns_409(client):
    h1 = auth_header(client, "u1@test.com")
    h2 = auth_header(client, "u2@test.com")
    start = _tomorrow_at(10, 0)
    end = _tomorrow_at(11, 0)
    body = {"space_id": client.space_id, "start_at": start.isoformat(), "end_at": end.isoformat()}
    r1 = client.post("/api/reservations", json=body, headers=h1)
    assert r1.status_code == 201, r1.text
    r2 = client.post("/api/reservations", json=body, headers=h2)
    assert r2.status_code == 409, r2.text


def test_partial_overlap_returns_409(client):
    h1 = auth_header(client, "u1@test.com")
    h2 = auth_header(client, "u2@test.com")
    start1 = _tomorrow_at(10, 0)
    end1 = _tomorrow_at(11, 0)
    start2 = _tomorrow_at(10, 30)
    end2 = _tomorrow_at(11, 30)
    r1 = client.post(
        "/api/reservations",
        json={"space_id": client.space_id, "start_at": start1.isoformat(), "end_at": end1.isoformat()},
        headers=h1,
    )
    assert r1.status_code == 201
    r2 = client.post(
        "/api/reservations",
        json={"space_id": client.space_id, "start_at": start2.isoformat(), "end_at": end2.isoformat()},
        headers=h2,
    )
    assert r2.status_code == 409


def test_adjacent_half_open_allowed(client):
    """[10:00,11:00) and [11:00,12:00) must both succeed (half-open range)."""
    h1 = auth_header(client, "u1@test.com")
    h2 = auth_header(client, "u2@test.com")
    a0, a1 = _tomorrow_at(10, 0), _tomorrow_at(11, 0)
    b0, b1 = _tomorrow_at(11, 0), _tomorrow_at(12, 0)
    r1 = client.post(
        "/api/reservations",
        json={"space_id": client.space_id, "start_at": a0.isoformat(), "end_at": a1.isoformat()},
        headers=h1,
    )
    r2 = client.post(
        "/api/reservations",
        json={"space_id": client.space_id, "start_at": b0.isoformat(), "end_at": b1.isoformat()},
        headers=h2,
    )
    assert r1.status_code == 201, r1.text
    assert r2.status_code == 201, r2.text


def test_cancel_frees_slot(client):
    h1 = auth_header(client, "u1@test.com")
    h2 = auth_header(client, "u2@test.com")
    start, end = _tomorrow_at(14, 0), _tomorrow_at(15, 0)
    body = {"space_id": client.space_id, "start_at": start.isoformat(), "end_at": end.isoformat()}
    r1 = client.post("/api/reservations", json=body, headers=h1)
    assert r1.status_code == 201
    rid = r1.json()["id"]
    c = client.post(f"/api/reservations/{rid}/cancel", headers=h1)
    assert c.status_code == 200
    assert c.json()["status"] == "cancelled"
    r2 = client.post("/api/reservations", json=body, headers=h2)
    assert r2.status_code == 201, r2.text


def test_check_out_frees_remaining_time(client):
    """Checking out of a checked-in reservation early lets someone else book that time."""
    from app.models.reservation import Reservation, ReservationStatus
    from tests.conftest import TestingSessionLocal

    h1 = auth_header(client, "u1@test.com")
    h2 = auth_header(client, "u2@test.com")
    start, end = _tomorrow_at(16, 0), _tomorrow_at(17, 0)
    body = {"space_id": client.space_id, "start_at": start.isoformat(), "end_at": end.isoformat()}
    r1 = client.post("/api/reservations", json=body, headers=h1)
    assert r1.status_code == 201
    rid = r1.json()["id"]

    # Simulate an already-checked-in reservation (bypassing the check-in time window for this test).
    s = TestingSessionLocal()
    row = s.get(Reservation, rid)
    row.status = ReservationStatus.CHECKED_IN
    s.commit()
    s.close()

    out = client.post(f"/api/reservations/{rid}/check-out", headers=h1)
    assert out.status_code == 200, out.text
    assert out.json()["status"] == "completed"

    r2 = client.post("/api/reservations", json=body, headers=h2)
    assert r2.status_code == 201, r2.text


def test_check_out_requires_checked_in_status(client):
    h1 = auth_header(client, "u1@test.com")
    start, end = _tomorrow_at(18, 0), _tomorrow_at(19, 0)
    body = {"space_id": client.space_id, "start_at": start.isoformat(), "end_at": end.isoformat()}
    r1 = client.post("/api/reservations", json=body, headers=h1)
    rid = r1.json()["id"]
    out = client.post(f"/api/reservations/{rid}/check-out", headers=h1)
    assert out.status_code == 400


def test_different_spaces_can_overlap(client):
    from sqlalchemy.orm import Session
    from app.database import SessionLocal
    from app.models.space import Space
    from datetime import time

    session = SessionLocal()
    # Use same engine as tests – SessionLocal may point to main DB; insert via raw
    from tests.conftest import TestingSessionLocal

    s = TestingSessionLocal()
    other = Space(
        name="Other Room",
        description="x",
        capacity=2,
        location="Y",
        open_time=time(9, 0),
        close_time=time(22, 0),
    )
    s.add(other)
    s.commit()
    other_id = other.id
    s.close()

    h1 = auth_header(client, "u1@test.com")
    h2 = auth_header(client, "u2@test.com")
    start, end = _tomorrow_at(10, 0), _tomorrow_at(11, 0)
    r1 = client.post(
        "/api/reservations",
        json={"space_id": client.space_id, "start_at": start.isoformat(), "end_at": end.isoformat()},
        headers=h1,
    )
    r2 = client.post(
        "/api/reservations",
        json={"space_id": other_id, "start_at": start.isoformat(), "end_at": end.isoformat()},
        headers=h2,
    )
    assert r1.status_code == 201
    assert r2.status_code == 201
