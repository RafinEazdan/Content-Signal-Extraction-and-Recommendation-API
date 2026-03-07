from pydantic import BaseModel, EmailStr


class verifyotpRequest(BaseModel):
    email: EmailStr
    otp: str