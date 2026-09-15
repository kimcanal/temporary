from datetime import date, datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.reservations import to_reservation_out
from app.core.deps import get_admin_user, get_current_user
from app.database import get_db
from app.models.reservation import Reservation, ReservationStatus
from app.models.user import User
from app.schemas.reservation import AdminBlockCreate, ReservationOut
from app.schemas.settings import AppSettingsOut, AppSettingsUpdate
from app.services.cache import cache_delete_pattern
from app.services.reservations import auto_cancel_no_shows, create_admin_block, list_reservations_for_day
from app.services.settings import get_app_settings, update_app_settings

router = APIRouter(prefix="/admin", tags=["admin"])
KST = ZoneInfo("Asia/Seoul")


@router.get("/stats")
def stats(db: Session = Depends(get_db), _: User = Depends(get_admin_user)):
    from app.models.space import Space

    return {
        "users": db.query(User).count(),
        "spaces": db.query(Space).count(),
        "reservations": db.query(Reservation).count(),
        "active": db.query(Reservation).filter(Reservation.status.in_(ReservationStatus.ACTIVE)).count(),
    }


@router.get("/reservations", response_model=list[ReservationOut])
def list_reservations_route(
    day: date = Query(..., alias="date", description="YYYY-MM-DD (campus local KST)"),
    space_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user),
):
    day_local = datetime(day.year, day.month, day.day, tzinfo=KST)
    rows = list_reservations_for_day(db, day_local, space_id)
    return [to_reservation_out(r) for r in rows]


@router.post("/blocks", response_model=ReservationOut, status_code=201)
def create_block_route(
    body: AdminBlockCreate, db: Session = Depends(get_db), admin: User = Depends(get_admin_user)
):
    block = create_admin_block(db, admin, body.space_id, body.start_at, body.end_at, body.reason)
    return to_reservation_out(block)


@router.post("/run-no-show-worker")
def run_worker(db: Session = Depends(get_db), _: User = Depends(get_admin_user)):
    n = auto_cancel_no_shows(db)
    return {"cancelled_as_no_show": n}


@router.get("/settings", response_model=AppSettingsOut)
def get_settings_route(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """Any signed-in user can read the current rules (the booking UI needs them)."""
    return get_app_settings(db)


@router.put("/settings", response_model=AppSettingsOut)
def update_settings_route(
    body: AppSettingsUpdate, db: Session = Depends(get_db), _: User = Depends(get_admin_user)
):
    row = update_app_settings(
        db,
        daily_limit_hours=body.daily_limit_hours,
        slot_minutes=body.slot_minutes,
        checkin_grace_minutes=body.checkin_grace_minutes,
    )
    cache_delete_pattern("slots:*")
    return row
