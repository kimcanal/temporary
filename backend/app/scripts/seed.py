"""Seed demo spaces and optional admin user."""
from datetime import time
import logging

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.app_settings import APP_SETTINGS_ROW_ID, AppSettings
from app.models.space import Space
from app.models.user import User

logger = logging.getLogger("slotlock.seed")

SPACES = [
    {
        "name": "곤자가 플라자 스터디룸 A",
        "description": "조용한 스터디 공간 – 4인, 화이트보드",
        "capacity": 4,
        "location": "곤자가 플라자 4F",
        "open_time": time(9, 0),
        "close_time": time(22, 0),
    },
    {
        "name": "로욜라 도서관 그룹룸 3",
        "description": "그룹 토론용 – 프로젝터 가능",
        "capacity": 6,
        "location": "로욜라 도서관 3F",
        "open_time": time(9, 0),
        "close_time": time(22, 0),
    },
    {
        "name": "다산관 세미나실 B",
        "description": "소규모 세미나·발표 연습",
        "capacity": 8,
        "location": "다산관 2F",
        "open_time": time(8, 0),
        "close_time": time(23, 0),
    },
    {
        "name": "엠마오관 회의실 1",
        "description": "팀 미팅·짧은 스탠드업",
        "capacity": 8,
        "location": "엠마오관 1F",
        "open_time": time(10, 0),
        "close_time": time(20, 0),
    },
]


def seed_if_empty(db: Session) -> None:
    if db.query(Space).count() == 0:
        for s in SPACES:
            db.add(Space(**s))
        db.commit()
        logger.info("Seeded %d spaces", len(SPACES))

    admin_email = "admin"
    if not db.query(User).filter(User.email == admin_email).first():
        db.add(
            User(
                email=admin_email,
                hashed_password=hash_password("admin"),
                full_name="SlotLock Admin",
                is_admin=True,
            )
        )
        db.commit()
        logger.info("Seeded admin user %s / admin", admin_email)

    demo_email = "student@slotlock.local"
    if not db.query(User).filter(User.email == demo_email).first():
        db.add(
            User(
                email=demo_email,
                hashed_password=hash_password("student123"),
                full_name="Demo Student",
                is_admin=False,
            )
        )
        db.commit()
        logger.info("Seeded demo student %s / student123", demo_email)

    if db.query(AppSettings).count() == 0:
        db.add(
            AppSettings(
                id=APP_SETTINGS_ROW_ID,
                daily_limit_hours=2.0,
                slot_minutes=30,
                checkin_grace_minutes=15,
            )
        )
        db.commit()
        logger.info("Seeded default app settings (2h/day, 30min slots, 15min grace)")


if __name__ == "__main__":
    from app.database import SessionLocal, engine
    from app.database import Base
    from sqlalchemy import text

    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS btree_gist"))
        Base.metadata.create_all(bind=conn)
    session = SessionLocal()
    try:
        seed_if_empty(session)
    finally:
        session.close()
