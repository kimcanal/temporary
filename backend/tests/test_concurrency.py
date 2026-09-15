"""Concurrent booking: exactly one success, others 409, no duplicate rows."""
import concurrent.futures
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import text

from tests.conftest import TestingSessionLocal, auth_header, engine

KST = ZoneInfo("Asia/Seoul")


def _tomorrow_at(hour: int, minute: int = 0) -> datetime:
    base = datetime.now(KST).date() + timedelta(days=1)
    return datetime(base.year, base.month, base.day, hour, minute, tzinfo=KST)


def test_concurrent_bookings_one_winner(client):
    start = _tomorrow_at(16, 0)
    end = _tomorrow_at(17, 0)
    body = {
        "space_id": client.space_id,
        "start_at": start.isoformat(),
        "end_at": end.isoformat(),
    }

    tokens = [
        auth_header(client, "u1@test.com"),
        auth_header(client, "u2@test.com"),
        auth_header(client, "u3@test.com"),
    ]

    def book(headers):
        # Each thread needs its own client connection; TestClient is sync & thread-ok enough
        return client.post("/api/reservations", json=body, headers=headers)

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(book, h) for h in tokens]
        results = [f.result() for f in futures]

    statuses = sorted(r.status_code for r in results)
    assert statuses.count(201) == 1, [(r.status_code, r.text) for r in results]
    assert statuses.count(409) == 2, [(r.status_code, r.text) for r in results]

    with engine.connect() as conn:
        n = conn.execute(
            text(
                """
                SELECT COUNT(*) FROM reservations
                WHERE space_id = :sid
                  AND status IN ('confirmed', 'checked_in')
                  AND start_at = :s AND end_at = :e
                """
            ),
            {"sid": client.space_id, "s": start, "e": end},
        ).scalar()
    assert n == 1


def test_concurrent_bookings_respect_daily_limit(client):
    """Two different (non-overlapping) times racing past the exclusion constraint
    must still not both succeed if, combined, they'd exceed the daily hour limit."""
    h1 = auth_header(client, "u1@test.com")
    a0, a1 = _tomorrow_at(9, 0), _tomorrow_at(10, 30)  # 1.5h
    b0, b1 = _tomorrow_at(11, 0), _tomorrow_at(12, 30)  # 1.5h; combined 3h > 2h daily limit

    def book(start, end):
        return client.post(
            "/api/reservations",
            json={"space_id": client.space_id, "start_at": start.isoformat(), "end_at": end.isoformat()},
            headers=h1,
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        f1 = pool.submit(book, a0, a1)
        f2 = pool.submit(book, b0, b1)
        r1, r2 = f1.result(), f2.result()

    codes = sorted([r1.status_code, r2.status_code])
    assert codes == [201, 400], [(r1.status_code, r1.text), (r2.status_code, r2.text)]


def test_concurrent_cancel_is_serialized(client):
    """Two concurrent cancels of the same reservation must not both report success."""
    h1 = auth_header(client, "u1@test.com")
    start, end = _tomorrow_at(20, 0), _tomorrow_at(21, 0)
    body = {"space_id": client.space_id, "start_at": start.isoformat(), "end_at": end.isoformat()}
    r1 = client.post("/api/reservations", json=body, headers=h1)
    assert r1.status_code == 201
    rid = r1.json()["id"]

    def cancel():
        return client.post(f"/api/reservations/{rid}/cancel", headers=h1)

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        results = [f.result() for f in [pool.submit(cancel) for _ in range(2)]]

    codes = sorted(r.status_code for r in results)
    assert codes == [200, 400], [(r.status_code, r.text) for r in results]
