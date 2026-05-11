from fastapi import HTTPException, status
from psycopg import Connection


class ProfileService:
    def __init__(self, db: Connection):
        self.db = db

    def get_profile(self, user_id: int):
        try:
            cursor = self.db.cursor()
            cursor.execute("SELECT * FROM users WHERE id = %s;", (user_id,))
            user = cursor.fetchone()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

        if user is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User details is unavailable")

        return user

    def delete_profile(self, user_id: int):
        try:
            cursor = self.db.cursor()
            cursor.execute("DELETE FROM users WHERE id = %s;", (user_id,))
            deleted_count = cursor.rowcount
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

        if deleted_count == 0:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not logged in!")
