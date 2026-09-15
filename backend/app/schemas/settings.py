from pydantic import BaseModel, Field


class AppSettingsOut(BaseModel):
    daily_limit_hours: float
    slot_minutes: int
    checkin_grace_minutes: int

    model_config = {"from_attributes": True}


class AppSettingsUpdate(BaseModel):
    daily_limit_hours: float = Field(gt=0, le=24)
    slot_minutes: int = Field(gt=0, le=240)
    checkin_grace_minutes: int = Field(ge=0, le=180)
