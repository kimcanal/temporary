from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.reservation import ReservationCreate, ReservationOut
from app.services import reservations as svc

router = APIRouter(prefix="/reservations", tags=["reservations"])


def to_reservation_out(r) -> ReservationOut:
    return ReservationOut(
        id=r.id,
        user_id=r.user_id,
        space_id=r.space_id,
        start_at=r.start_at,
        end_at=r.end_at,
        status=r.status,
        party_size=r.party_size,
        is_admin_block=r.is_admin_block,
        note=r.note,
        checked_in_at=r.checked_in_at,
        created_at=r.created_at,
        space_name=r.space.name if getattr(r, "space", None) else None,
        user_name=r.user.full_name if getattr(r, "user", None) else None,
    )


@router.post("", response_model=ReservationOut, status_code=201)
def create(body: ReservationCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    r = svc.create_reservation(
        db, user, body.space_id, body.start_at, body.end_at, body.party_size, body.note
    )
    return to_reservation_out(r)


@router.get("/mine", response_model=list[ReservationOut])
def mine(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return [to_reservation_out(r) for r in svc.list_my_reservations(db, user)]


@router.post("/{reservation_id}/cancel", response_model=ReservationOut)
def cancel(reservation_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    r = svc.cancel_reservation(db, user, reservation_id)
    return to_reservation_out(r)


@router.post("/{reservation_id}/check-in", response_model=ReservationOut)
def check_in(reservation_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    r = svc.check_in(db, user, reservation_id)
    return to_reservation_out(r)


@router.post("/{reservation_id}/check-out", response_model=ReservationOut)
def check_out(reservation_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    r = svc.check_out(db, user, reservation_id)
    return to_reservation_out(r)
