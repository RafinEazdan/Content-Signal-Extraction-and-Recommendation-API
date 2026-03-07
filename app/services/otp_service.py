import random
import secrets

class OTPService:
    def __init__(self, redis_client):
        self.redis = redis_client

    async def generate_otp(self,email):
        otp = f"{secrets.randbelow(1000000):06d}"
        