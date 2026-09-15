"""Slot grid generation for a space on a given date."""
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.models.reservation import Reservation, ReservationStatus
from app.models.space import Space
from app.services.cache import cache_get, cache_set
from app.services.settings import get_app_settings

# Use KST for university campus hours
KST = ZoneInfo("Asia/Seoul")


def _combine(d: date, t, tz=KST) -> datetime:
    return datetime(d.year, d.month, d.day, t.hour, t.minute, t.second, tzinfo=tz)


def _as_kst(dt: datetime) -> datetime:
    """Interpret a naive datetime as KST, or convert an aware one to KST."""
    return dt.astimezone(KST) if dt.tzinfo else dt.replace(tzinfo=KST)


def generate_slots(db: Session, space: Space, day: date) -> list[dict]:
    settings = get_app_settings(db)
    cache_key = f"slots:{space.id}:{day.isoformat()}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    step = timedelta(minutes=settings.slot_minutes)
    start = _combine(day, space.open_time)
    end = _combine(day, space.close_time)
    if end <= start:
        return []

    day_start = start
    day_end = end
    active = (
        db.query(Reservation)
        .filter(
            Reservation.space_id == space.id,
            Reservation.status.in_(ReservationStatus.ACTIVE),
            Reservation.start_at < day_end,
            Reservation.end_at > day_start,
        )
        .all()
    )

    slots: list[dict] = []
    cursor = start
    now = datetime.now(KST)
    while cursor + step <= end:
        slot_end = cursor + step
        available = True
        if slot_end <= now:
            available = False
        else:
            for r in active:
                # half-open [start, end)
                if cursor < _as_kst(r.end_at) and slot_end > _as_kst(r.start_at):
                    available = False
                    break
        slots.append(
            {
                "start_at": cursor.isoformat(),
                "end_at": slot_end.isoformat(),
                "available": available,
            }
        )
        cursor = slot_end

    cache_set(cache_key, slots, ttl=15)
    return slots
