from fastapi import APIRouter, Depends, status, Response
from psycopg import Connection

import app.schemas.users as schemas
from app.database.session import get_db
from app.redis.dependencies import get_redis
from app.services.oauth import get_current_user
from app.services.signup_service import SignupService
from app.services.profile_service import ProfileService


router = APIRouter(prefix="/users", tags=["Users"])


@router.post("/signup/send-otp", status_code=200)
async def send_otp(payload: schemas.UserCreate, db: Connection = Depends(get_db), redis=Depends(get_redis)):
    service = SignupService(db, redis)
    service.check_existing_user(payload.email)
    return await service.send_otp(payload.email, payload.password, payload.username, payload.profile_pic)


@router.post("/signup/verify-otp", response_model=schemas.UserResponse)
async def verify_and_signup(payload: schemas.OTPVerifyRequest, db: Connection = Depends(get_db), redis=Depends(get_redis)):
    service = SignupService(db, redis)
    await service.verify_user(payload.email, payload.otp)
    return await service.signup_user(payload.email)


@router.get("/profile", response_model=schemas.UserResponse)
def get_profile(db: Connection = Depends(get_db), current_user: dict = Depends(get_current_user)):
    service = ProfileService(db)
    return service.get_profile(current_user["id"])


@router.delete("/profile/delete", status_code=status.HTTP_204_NO_CONTENT)
def delete_profile(db: Connection = Depends(get_db), current_user: dict = Depends(get_current_user)):
    service = ProfileService(db)
    service.delete_profile(current_user["id"])
    return Response(status_code=status.HTTP_204_NO_CONTENT)
