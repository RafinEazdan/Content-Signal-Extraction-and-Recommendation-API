from pydantic import BaseModel
from pydantic import EmailStr
from datetime import datetime

class UserCreate(BaseModel):
    username: str
    email: str
    password: str


class UserResponse(BaseModel):
    email: EmailStr
    id: int
    created_at: datetime

    class Config:
        from_attributes = True