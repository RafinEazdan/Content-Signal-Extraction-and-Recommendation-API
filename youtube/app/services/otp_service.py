import secrets
import json

from fastapi import HTTPException 


class OTPService:
    def __init__(self, redis_client):
        self.redis = redis_client

    async def generate_otp(self,email, hashed_pass, username,profilepic):
        otp = f"{secrets.randbelow(1000000):06d}"
        data_block = {
            "email": email,
            "username":username,
            "hashed_password": hashed_pass,
            "profilepic":profilepic,
            "otp": otp
        }
        await self.redis.set(f"reg:{email}", json.dumps(data_block), expire=500)
        print(f"OTP is: {otp}") # development purpose

        return {"message": "OTP sent to email. Please check your inbox and spam folder."}
    
    async def verify_otp(self, user_email, user_otp):
        data = await self.redis.get(f"reg:{user_email}")

        if not data:
            raise HTTPException(status_code=400, detail="You have entered Wrong or Invalid OTP")
        
        data_block = json.loads(data)
        stored_otp = data_block["otp"]
        if stored_otp != user_otp:
            raise HTTPException(status_code=400, detail="Invalid OTP")
        
        return True

        