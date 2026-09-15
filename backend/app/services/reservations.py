"""Reservation business logic: create, cancel, check-in, daily limit."""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.models.reservation import Reservation, ReservationStatus
from app.models.space import Space
from app.models.user import User
from app.services.cache import cache_delete_pattern
from app.services.settings import get_app_settings

KST = ZoneInfo("Asia/Seoul")


def _ensure_aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=KST)
    return dt.astimezone(KST)


def _hours(start: datetime, end: datetime) -> float:
    return (end - start).total_seconds() / 3600.0


def _ensure_within_operating_hours(space: Space, start_at: datetime, end_at: datetime) -> None:
    open_dt = start_at.replace(
        hour=space.open_time.hour, minute=space.open_time.minute, second=0, microsecond=0
    )
    close_dt = start_at.replace(
        hour=space.close_time.hour, minute=space.close_time.minute, second=0, microsecond=0
    )
    if start_at < open_dt or end_at > close_dt:
        raise HTTPException(status_code=400, detail="Outside space operating hours")


def _daily_used_hours(db: Session, user_id: int, day_local: datetime) -> float:
    day_start = day_local.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)
    rows = (
        db.query(Reservation)
        .filter(
            Reservation.user_id == user_id,
            Reservation.status.in_(ReservationStatus.COUNTS_TOWARD_DAILY_LIMIT),
            Reservation.is_admin_block.is_(False),
            Reservation.start_at >= day_start,
            Reservation.start_at < day_end,
        )
        .all()
    )
    return sum(_hours(r.start_at, r.end_at) for r in rows)


def create_reservation(
    db: Session,
    user: User,
    space_id: int,
    start_at: datetime,
    end_at: datetime,
    party_size: int = 1,
    note: str | None = None,
) -> Reservation:
    settings = get_app_settings(db)
    start_at = _ensure_aware(start_at)
    end_at = _ensure_aware(end_at)

    if end_at <= start_at:
        raise HTTPException(status_code=400, detail="end_at must be after start_at")

    duration_h = _hours(start_at, end_at)
    if duration_h <= 0 or duration_h > settings.daily_limit_hours:
        raise HTTPException(
            status_code=400,
            detail=f"Reservation duration must be between 0 and {settings.daily_limit_hours} hours",
        )

    space = db.get(Space, space_id)
    if not space or not space.is_active:
        raise HTTPException(status_code=404, detail="Space not found")

    if party_size < 1 or party_size > space.capacity:
        raise HTTPException(
            status_code=400,
            detail=f"party_size must be between 1 and this space's capacity ({space.capacity})",
        )

    _ensure_within_operating_hours(space, start_at, end_at)

    # Serialize this user's daily-limit check + insert: without this, two concurrent
    # bookings for different (non-overlapping) times could each read the same "used
    # hours so far" before either commits, and both pass the limit check even though
    # combined they exceed it. Held until this transaction commits or rolls back.
    db.execute(text("SELECT pg_advisory_xact_lock(:uid)"), {"uid": user.id})

    used = _daily_used_hours(db, user.id, start_at)
    if used + duration_h > settings.daily_limit_hours + 1e-9:
        raise HTTPException(
            status_code=400,
            detail=f"Daily limit of {settings.daily_limit_hours}h exceeded (used {used:.1f}h)",
        )

    reservation = Reservation(
        user_id=user.id,
        space_id=space_id,
        start_at=start_at,
        end_at=end_at,
        status=ReservationStatus.CONFIRMED,
        party_size=party_size,
        note=note,
    )
    db.add(reservation)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Time slot already reserved (overlap excluded by DB constraint)",
        ) from None

    db.refresh(reservation)
    db.get(Reservation, reservation.id, options=[joinedload(Reservation.space), joinedload(Reservation.user)])
    cache_delete_pattern(f"slots:{space_id}:*")
    return reservation


def create_admin_block(
    db: Session,
    admin: User,
    space_id: int,
    start_at: datetime,
    end_at: datetime,
    reason: str | None = None,
) -> Reservation:
    """Block off a time range on a space (e.g. a school class) instead of a real booking.

    Unlike create_reservation, this skips the per-user daily-hour limit and party size —
    neither makes sense for an admin closing off the room to everyone else.
    """
    start_at = _ensure_aware(start_at)
    end_at = _ensure_aware(end_at)

    if end_at <= start_at:
        raise HTTPException(status_code=400, detail="end_at must be after start_at")

    space = db.get(Space, space_id)
    if not space or not space.is_active:
        raise HTTPException(status_code=404, detail="Space not found")

    _ensure_within_operating_hours(space, start_at, end_at)

    block = Reservation(
        user_id=admin.id,
        space_id=space_id,
        start_at=start_at,
        end_at=end_at,
        status=ReservationStatus.CONFIRMED,
        party_size=1,
        is_admin_block=True,
        note=reason,
    )
    db.add(block)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Time slot already reserved (overlap excluded by DB constraint)",
        ) from None

    db.refresh(block)
    db.get(Reservation, block.id, options=[joinedload(Reservation.space), joinedload(Reservation.user)])
    cache_delete_pattern(f"slots:{space_id}:*")
    return block


def cancel_reservation(db: Session, user: User, reservation_id: int) -> Reservation:
    # Lock the row so a concurrent check-in/check-out/cancel on the same reservation
    # can't race past this status check with a stale read (lost-update).
    r = db.get(Reservation, reservation_id, with_for_update=True)
    if not r:
        raise HTTPException(status_code=404, detail="Reservation not found")
    if r.user_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="Not your reservation")
    if r.status not in ReservationStatus.ACTIVE:
        raise HTTPException(status_code=400, detail=f"Cannot cancel status={r.status}")
    r.status = ReservationStatus.CANCELLED
    db.commit()
    db.refresh(r)
    cache_delete_pattern(f"slots:{r.space_id}:*")
    return r


def check_in(db: Session, user: User, reservation_id: int) -> Reservation:
    r = db.get(Reservation, reservation_id, with_for_update=True)
    if not r:
        raise HTTPException(status_code=404, detail="Reservation not found")
    if r.user_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="Not your reservation")
    if r.is_admin_block:
        raise HTTPException(status_code=400, detail="Cannot check in to an admin block")
    if r.status != ReservationStatus.CONFIRMED:
        raise HTTPException(status_code=400, detail=f"Cannot check in status={r.status}")
    now = datetime.now(timezone.utc)
    start = r.start_at if r.start_at.tzinfo else r.start_at.replace(tzinfo=timezone.utc)
    grace = timedelta(minutes=get_app_settings(db).checkin_grace_minutes)
    if now < start - grace:
        raise HTTPException(status_code=400, detail="Too early to check in")
    if now > start + grace:
        raise HTTPException(status_code=400, detail="Check-in window expired")
    r.status = ReservationStatus.CHECKED_IN
    r.checked_in_at = now
    db.commit()
    db.refresh(r)
    return r


def check_out(db: Session, user: User, reservation_id: int) -> Reservation:
    """End a checked-in reservation early, freeing the remaining time for others to book."""
    r = db.get(Reservation, reservation_id, with_for_update=True)
    if not r:
        raise HTTPException(status_code=404, detail="Reservation not found")
    if r.user_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="Not your reservation")
    if r.status != ReservationStatus.CHECKED_IN:
        raise HTTPException(status_code=400, detail=f"Cannot check out status={r.status}")
    r.status = ReservationStatus.COMPLETED
    db.commit()
    db.refresh(r)
    cache_delete_pattern(f"slots:{r.space_id}:*")
    return r


def list_my_reservations(db: Session, user: User) -> list[Reservation]:
    """A user's own bookings — excludes admin blocks, which aren't personal reservations."""
    return (
        db.query(Reservation)
        .options(joinedload(Reservation.space))
        .filter(Reservation.user_id == user.id, Reservation.is_admin_block.is_(False))
        .order_by(Reservation.start_at.desc())
        .all()
    )


def list_reservations_for_day(
    db: Session, day_local: datetime, space_id: int | None = None
) -> list[Reservation]:
    """All reservations (any status) starting on the given KST calendar day — for the admin dashboard."""
    day_start = day_local.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)
    query = (
        db.query(Reservation)
        .options(joinedload(Reservation.space), joinedload(Reservation.user))
        .filter(Reservation.start_at >= day_start, Reservation.start_at < day_end)
    )
    if space_id is not None:
        query = query.filter(Reservation.space_id == space_id)
    return query.order_by(Reservation.start_at).all()


def auto_cancel_no_shows(db: Session) -> int:
    """Mark confirmed reservations past grace as no_show and free the slot.

    Admin blocks are excluded — nobody "shows up" to a block, and flipping it to
    no_show would free the room again after the grace period, defeating the block.
    """
    settings = get_app_settings(db)
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(minutes=settings.checkin_grace_minutes)
    rows = (
        db.query(Reservation)
        .filter(
            Reservation.status == ReservationStatus.CONFIRMED,
            Reservation.is_admin_block.is_(False),
            Reservation.start_at < cutoff,
        )
        .all()
    )
    count = 0
    for r in rows:
        r.status = ReservationStatus.NO_SHOW
        count += 1
        cache_delete_pattern(f"slots:{r.space_id}:*")
    if count:
        db.commit()
    return count
