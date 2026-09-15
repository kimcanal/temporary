"""Admin time-blocking: occupies the slot like a real booking, but isn't one."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from tests.conftest import auth_header

KST = ZoneInfo("Asia/Seoul")


def _tomorrow_at(hour: int, minute: int = 0) -> datetime:
    base = datetime.now(KST).date() + timedelta(days=1)
    return datetime(base.year, base.month, base.day, hour, minute, tzinfo=KST)


def test_create_block_requires_admin(client):
    h1 = auth_header(client, "u1@test.com")
    start, end = _tomorrow_at(9, 0), _tomorrow_at(10, 0)
    r = client.post(
        "/api/admin/blocks",
        json={"space_id": client.space_id, "start_at": start.isoformat(), "end_at": end.isoformat()},
        headers=h1,
    )
    assert r.status_code == 403


def test_admin_block_occupies_slot_and_blocks_student_booking(client):
    h_admin = auth_header(client, "admin", "admin")
    h1 = auth_header(client, "u1@test.com")
    start, end = _tomorrow_at(9, 0), _tomorrow_at(11, 0)

    block = client.post(
        "/api/admin/blocks",
        json={
            "space_id": client.space_id,
            "start_at": start.isoformat(),
            "end_at": end.isoformat(),
            "reason": "학교 수업",
        },
        headers=h_admin,
    )
    assert block.status_code == 201, block.text
    body = block.json()
    assert body["is_admin_block"] is True
    assert body["status"] == "confirmed"
    assert body["note"] == "학교 수업"

    overlap = client.post(
        "/api/reservations",
        json={
            "space_id": client.space_id,
            "start_at": _tomorrow_at(9, 30).isoformat(),
            "end_at": _tomorrow_at(10, 30).isoformat(),
        },
        headers=h1,
    )
    assert overlap.status_code == 409, overlap.text


def test_admin_block_skips_daily_limit(client):
    """A block can span more than the (2h default) per-user daily limit."""
    h_admin = auth_header(client, "admin", "admin")
    start, end = _tomorrow_at(9, 0), _tomorrow_at(14, 0)  # 5h
    r = client.post(
        "/api/admin/blocks",
        json={"space_id": client.space_id, "start_at": start.isoformat(), "end_at": end.isoformat()},
        headers=h_admin,
    )
    assert r.status_code == 201, r.text


def test_admin_blocks_excluded_from_my_reservations(client):
    h_admin = auth_header(client, "admin", "admin")
    start, end = _tomorrow_at(9, 0), _tomorrow_at(10, 0)
    block = client.post(
        "/api/admin/blocks",
        json={"space_id": client.space_id, "start_at": start.isoformat(), "end_at": end.isoformat()},
        headers=h_admin,
    )
    block_id = block.json()["id"]

    mine = client.get("/api/reservations/mine", headers=h_admin)
    assert mine.status_code == 200
    assert all(r["id"] != block_id for r in mine.json())


def test_admin_block_does_not_count_toward_admins_own_daily_limit(client):
    """A block the admin creates shouldn't eat into the admin's own 2h/day booking limit."""
    h_admin = auth_header(client, "admin", "admin")
    block = client.post(
        "/api/admin/blocks",
        json={
            "space_id": client.space_id,
            "start_at": _tomorrow_at(9, 0).isoformat(),
            "end_at": _tomorrow_at(12, 0).isoformat(),  # 3h — already over the 2h default limit
        },
        headers=h_admin,
    )
    assert block.status_code == 201, block.text

    own_booking = client.post(
        "/api/reservations",
        json={
            "space_id": client.space_id,
            "start_at": _tomorrow_at(13, 0).isoformat(),
            "end_at": _tomorrow_at(14, 0).isoformat(),
        },
        headers=h_admin,
    )
    assert own_booking.status_code == 201, own_booking.text


def test_admin_block_not_auto_marked_no_show(client):
    """The no-show worker must skip admin blocks — they have no one to "show up"."""
    from app.models.reservation import Reservation
    from tests.conftest import TestingSessionLocal

    h_admin = auth_header(client, "admin", "admin")
    block = client.post(
        "/api/admin/blocks",
        json={
            "space_id": client.space_id,
            "start_at": _tomorrow_at(9, 0).isoformat(),
            "end_at": _tomorrow_at(10, 0).isoformat(),
        },
        headers=h_admin,
    )
    block_id = block.json()["id"]

    # Simulate the block's start time already being well in the past.
    s = TestingSessionLocal()
    row = s.get(Reservation, block_id)
    row.start_at = datetime.now(KST) - timedelta(hours=1)
    s.commit()
    s.close()

    worker = client.post("/api/admin/run-no-show-worker", headers=h_admin)
    assert worker.status_code == 200, worker.text

    day = _tomorrow_at(0, 0).date().isoformat()
    # The block's start_at was moved to today, so look it up via the direct DB check instead.
    s = TestingSessionLocal()
    refreshed = s.get(Reservation, block_id)
    status = refreshed.status
    s.close()
    assert status == "confirmed"


def test_cannot_check_in_to_admin_block(client):
    h_admin = auth_header(client, "admin", "admin")
    block = client.post(
        "/api/admin/blocks",
        json={
            "space_id": client.space_id,
            "start_at": _tomorrow_at(9, 0).isoformat(),
            "end_at": _tomorrow_at(10, 0).isoformat(),
        },
        headers=h_admin,
    )
    block_id = block.json()["id"]
    r = client.post(f"/api/reservations/{block_id}/check-in", headers=h_admin)
    assert r.status_code == 400


def test_admin_blocks_appear_in_dashboard_and_can_be_unblocked(client):
    h_admin = auth_header(client, "admin", "admin")
    h1 = auth_header(client, "u1@test.com")
    start, end = _tomorrow_at(9, 0), _tomorrow_at(10, 0)
    block = client.post(
        "/api/admin/blocks",
        json={"space_id": client.space_id, "start_at": start.isoformat(), "end_at": end.isoformat()},
        headers=h_admin,
    )
    block_id = block.json()["id"]

    day = start.date().isoformat()
    listing = client.get(f"/api/admin/reservations?date={day}", headers=h_admin)
    row = next(r for r in listing.json() if r["id"] == block_id)
    assert row["is_admin_block"] is True

    cancelled = client.post(f"/api/reservations/{block_id}/cancel", headers=h_admin)
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"

    now_available = client.post(
        "/api/reservations",
        json={"space_id": client.space_id, "start_at": start.isoformat(), "end_at": end.isoformat()},
        headers=h1,
    )
    assert now_available.status_code == 201, now_available.text
