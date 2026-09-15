from datetime import date, datetime

from pydantic import BaseModel, Field, model_validator


class ReservationCreate(BaseModel):
    space_id: int
    start_at: datetime
    end_at: datetime
    party_size: int = Field(default=1, ge=1, le=200)
    note: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def check_range(self):
        if self.end_at <= self.start_at:
            raise ValueError("end_at must be after start_at")
        return self


class ReservationOut(BaseModel):
    id: int
    user_id: int
    space_id: int
    start_at: datetime
    end_at: datetime
    status: str
    party_size: int
    is_admin_block: bool
    note: str | None
    checked_in_at: datetime | None
    created_at: datetime
    space_name: str | None = None
    user_name: str | None = None

    model_config = {"from_attributes": True}


class AdminBlockCreate(BaseModel):
    space_id: int
    start_at: datetime
    end_at: datetime
    reason: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def check_range(self):
        if self.end_at <= self.start_at:
            raise ValueError("end_at must be after start_at")
        return self


class SlotOut(BaseModel):
    start_at: datetime
    end_at: datetime
    available: bool


class SlotsResponse(BaseModel):
    space_id: int
    date: date
    slots: list[SlotOut]
