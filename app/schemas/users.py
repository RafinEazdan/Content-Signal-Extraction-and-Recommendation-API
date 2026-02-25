from pydantic import BaseModel
from pydantic import EmailStr
from datetime import datetime

class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    profile_pic: str | None = None


class UserResponse(BaseModel):
    email: EmailStr
    id: int
    created_at: datetime
    profile_pic: str | None = None

    class Config:
        from_attributes = True