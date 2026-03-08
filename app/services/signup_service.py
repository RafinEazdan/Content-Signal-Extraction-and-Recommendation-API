from fastapi import HTTPException
from psycopg import Connection
import json

from app.core.security import hash
from app.services.otp_service import OTPService


class SignupService:
    def __init__(self,db: Connection,redis):
        self.db = db
        self.redis = redis

    def check_existing_user(self, email):
        try:
            cursor = self.db.cursor()
            cursor.execute("SELECT id FROM users WHERE email = %s;", (email,))
            existing_user = cursor.fetchone()

            if existing_user:
                raise HTTPException(status_code=409, detail="Email already registered. Please login.")
            
            return True
            
        except HTTPException:
            raise  # ← let it pass through untouched
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    async def send_otp(self, email, password, username,profilepic):
        hashed_password = hash(password)
        otp_service = OTPService(self.redis)
        return await otp_service.generate_otp(email,hashed_password, username,profilepic)
    
    async def verify_user(self, email, otp):
        otp_service = OTPService(self.redis)
        return await otp_service.verify_otp(email, otp)

    async def signup_user(self, email):
        data = await self.redis.get(f"reg:{email}")

        if not data:
            raise HTTPException(status_code=400, detail="Registration expired or not found")

        data_block = json.loads(data)

        email = data_block["email"]
        hashed_password = data_block["hashed_password"]
        username = data_block["username"]
        profilepic = data_block["profilepic"]

        try:
            cursor = self.db.cursor()
            cursor.execute(
                    """
                    INSERT INTO users (email, username, hashed_password, profile_pic)
                    VALUES (%s, %s, %s, %s)
                    RETURNING *;
                    """,
                    (email, username, hashed_password, profilepic)
                )
            user = cursor.fetchone()

            self.db.commit()

            await self.redis.delete(f"reg:{email}")

            return {
                "username": user["username"],
                "email": user["email"],
                "id": user["id"],
                "created_at": user["created_at"],
                "profile_pic": user["profile_pic"]
            }

        except Exception as e:
            self.db.rollback()
            raise HTTPException(status_code=500, detail=f"User registration failed: {e}")
    
    
        


    

    