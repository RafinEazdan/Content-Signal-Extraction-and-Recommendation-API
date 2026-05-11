from typing import Optional

from pydantic import BaseModel
from pydantic import EmailStr
from datetime import datetime

class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    profile_pic: str | None = None


class UserResponse(BaseModel):
    username: str
    email: EmailStr
    id: int
    created_at: datetime
    profile_pic: str | None = None

    class Config:
        from_attributes = True

class OTPVerifyRequest(BaseModel):
    email: EmailStr
    otp: str


class Token(BaseModel):
    token: str
    token_type: str

class TokenData(BaseModel):
    id: Optional[int]  = None