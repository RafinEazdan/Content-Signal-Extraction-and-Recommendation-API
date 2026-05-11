from fastapi import HTTPException, status
from psycopg import Connection

import app.core.security as security
from app.services.oauth import create_token


class LoginService:
    def __init__(self, db: Connection):
        self.db = db

    def login(self, email: str, password: str):
        try:
            cursor = self.db.cursor()
            cursor.execute(
                "SELECT id, email, hashed_password AS password FROM users WHERE email = %s;",
                (email,)
            )
            user = cursor.fetchone()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

        if user is None or not security.verify_pass(password, user["password"]):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Credentials")

        access_token = create_token(data={"id": user["id"]})
        return {"token": access_token, "token_type": "bearer"}
