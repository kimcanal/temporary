"""Single-row table of business rules an admin can tune at runtime."""
from sqlalchemy import Float, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

APP_SETTINGS_ROW_ID = 1


class AppSettings(Base):
    """Row id is always APP_SETTINGS_ROW_ID — there is exactly one row."""

    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    daily_limit_hours: Mapped[float] = mapped_column(Float, nullable=False)
    slot_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    checkin_grace_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
