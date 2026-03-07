
from fastapi import Depends
from psycopg import Connection
from core.security import hash
from services.otp_service import OTPService



class SignupService:
    def __init__(self,db: Connection,redis):
        self.db = db
        self.redis = redis

    async def send_otp(self, email, password):
        hashed_password = hash(password)
        otp_service = OTPService(self.redis)
        return await otp_service.generate_otp(email,hashed_password)


    

    