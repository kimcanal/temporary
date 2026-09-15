from datetime import date, datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import get_admin_user, get_current_user
from app.database import get_db
from app.models.space import Space
from app.models.user import User
from app.schemas.reservation import SlotOut, SlotsResponse
from app.schemas.space import SpaceCreate, SpaceOut
from app.services.slots import generate_slots

router = APIRouter(prefix="/spaces", tags=["spaces"])
KST = ZoneInfo("Asia/Seoul")


@router.get("", response_model=list[SpaceOut])
def list_spaces(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.query(Space).filter(Space.is_active.is_(True)).order_by(Space.name).all()


@router.get("/{space_id}", response_model=SpaceOut)
def get_space(space_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    space = db.get(Space, space_id)
    if not space or not space.is_active:
        raise HTTPException(status_code=404, detail="Space not found")
    return space


@router.get("/{space_id}/slots", response_model=SlotsResponse)
def get_slots(
    space_id: int,
    day: date = Query(..., alias="date", description="YYYY-MM-DD (campus local KST)"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    space = db.get(Space, space_id)
    if not space or not space.is_active:
        raise HTTPException(status_code=404, detail="Space not found")
    raw = generate_slots(db, space, day)
    slots = [
        SlotOut(
            start_at=datetime.fromisoformat(s["start_at"]),
            end_at=datetime.fromisoformat(s["end_at"]),
            available=s["available"],
        )
        for s in raw
    ]
    return SlotsResponse(space_id=space_id, date=day, slots=slots)


@router.post("", response_model=SpaceOut, status_code=201)
def create_space(
    body: SpaceCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user),
):
    if db.query(Space).filter(Space.name == body.name).first():
        raise HTTPException(status_code=400, detail="Space name exists")
    space = Space(**body.model_dump())
    db.add(space)
    db.commit()
    db.refresh(space)
    return space
