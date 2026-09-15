"""Study space / room model."""
from datetime import datetime, time

from sqlalchemy import Boolean, DateTime, Integer, String, Text, Time, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Space(Base):
    __tablename__ = "spaces"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    capacity: Mapped[int] = mapped_column(Integer, default=4, nullable=False)
    location: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    open_time: Mapped[time] = mapped_column(Time, nullable=False)  # e.g. 09:00
    close_time: Mapped[time] = mapped_column(Time, nullable=False)  # e.g. 22:00
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    reservations = relationship("Reservation", back_populates="space")
