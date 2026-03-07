from fastapi import HTTPException
from psycopg import Connection
from core.security import hash
from services.otp_service import OTPService



class SignupService:
    def __init__(self,db: Connection,redis):
        self.db = db
        self.redis = redis

    def check_existing_user(self, email):
        try:
            with self.db.cursor() as cursor:
                cursor.execute("SELECT id FROM users WHERE email = %s;", (email,))
            existing_user = cursor.fetchone()

            if existing_user:
                raise HTTPException(status_code=409, detail="Email already registered. Please login.")
            
        except Exception as e:
             raise HTTPException(status_code=400, detail="Databse is not connected")

    async def send_otp(self, email, password):
        hashed_password = hash(password)
        otp_service = OTPService(self.redis)
        return await otp_service.generate_otp(email,hashed_password)
    
    # def signup_user(self, ):
        


    

    