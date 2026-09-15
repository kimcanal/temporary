"""Reservation model with PostgreSQL exclusion constraint for no-overlap."""
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ReservationStatus:
    """Literal values allowed in `Reservation.status`."""

    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    CHECKED_IN = "checked_in"
    NO_SHOW = "no_show"
    COMPLETED = "completed"

    # Holds the space/time slot: matches the DB exclusion constraint's WHERE clause.
    ACTIVE = (CONFIRMED, CHECKED_IN)
    # Counts against a user's daily booking-hours limit.
    COUNTS_TOWARD_DAILY_LIMIT = (CONFIRMED, CHECKED_IN, COMPLETED)


class Reservation(Base):
    """A booked time range on a space.

    Overlap prevention relies on PostgreSQL:
      EXCLUDE USING gist (space_id WITH =, tstzrange(start_at, end_at, '[)') WITH &&)
    applied only to rows with status IN ('confirmed', 'checked_in').
    """

    __tablename__ = "reservations"
    __table_args__ = (
        CheckConstraint("end_at > start_at", name="ck_reservation_positive_duration"),
        CheckConstraint("party_size > 0", name="ck_reservation_positive_party_size"),
        ExcludeConstraint(
            ("space_id", "="),
            (text("tstzrange(start_at, end_at, '[)')"), "&&"),
            using="gist",
            where=text("status IN ('confirmed', 'checked_in')"),
            name="excl_no_overlap_active",
        ),
        Index("ix_reservations_user_start", "user_id", "start_at"),
        Index("ix_reservations_space_start", "space_id", "start_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    space_id: Mapped[int] = mapped_column(ForeignKey("spaces.id"), nullable=False, index=True)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # One of ReservationStatus's values above.
    status: Mapped[str] = mapped_column(String(32), default=ReservationStatus.CONFIRMED, nullable=False)
    # How many people are actually using the space (<= Space.capacity).
    party_size: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    # True for a slot an admin blocked off (e.g. a class) rather than a real booking.
    # user_id is the admin who created the block. Uses the same status/exclusion-constraint
    # machinery as a real reservation so it still prevents double-booking.
    is_admin_block: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    checked_in_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user = relationship("User", back_populates="reservations")
    space = relationship("Space", back_populates="reservations")
