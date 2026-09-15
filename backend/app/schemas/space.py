from datetime import time

from pydantic import BaseModel, Field


class SpaceOut(BaseModel):
    id: int
    name: str
    description: str | None
    capacity: int
    location: str
    open_time: time
    close_time: time
    is_active: bool

    model_config = {"from_attributes": True}


class SpaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    capacity: int = Field(default=4, ge=1, le=100)
    location: str = ""
    open_time: time
    close_time: time
