"""Admin-tunable business rules, persisted as a single DB row (app_settings)."""
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.app_settings import APP_SETTINGS_ROW_ID, AppSettings


def get_app_settings(db: Session) -> AppSettings:
    row = db.get(AppSettings, APP_SETTINGS_ROW_ID)
    if row is None:
        # Normally seeded at startup (see scripts/seed.py); fall back to the
        # env-configured defaults so the app still works if that step was skipped.
        env = get_settings()
        row = AppSettings(
            id=APP_SETTINGS_ROW_ID,
            daily_limit_hours=env.daily_limit_hours,
            slot_minutes=env.slot_minutes,
            checkin_grace_minutes=env.checkin_grace_minutes,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def update_app_settings(
    db: Session, *, daily_limit_hours: float, slot_minutes: int, checkin_grace_minutes: int
) -> AppSettings:
    row = get_app_settings(db)
    row.daily_limit_hours = daily_limit_hours
    row.slot_minutes = slot_minutes
    row.checkin_grace_minutes = checkin_grace_minutes
    db.commit()
    db.refresh(row)
    return row
