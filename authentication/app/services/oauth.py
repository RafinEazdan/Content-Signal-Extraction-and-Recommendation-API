from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from psycopg import Connection
import jwt
from jwt.exceptions import InvalidTokenError

import app.schemas.users as schemas
from app.core.config import settings
from app.database.session import get_db


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


def create_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def verify_token(token: str, credential_exception):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, settings.ALGORITHM)
        id: str = payload.get("id")

        if id is None:
            raise credential_exception

        return schemas.TokenData(id=id)
    except InvalidTokenError:
        raise credential_exception


def get_current_user(token: str = Depends(oauth2_scheme), db: Connection = Depends(get_db)):
    credential_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="User cannot be authenticated"
    )

    token_data = verify_token(token, credential_exception)

    with db.cursor() as cursor:
        cursor.execute("SELECT id FROM users WHERE id = %s;", (token_data.id,))
        user = cursor.fetchone()

    if user is None:
        raise credential_exception

    return user
