from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import os
from dotenv import load_dotenv
import jwt
from jwt.exceptions import InvalidTokenError
from psycopg import Connection

# import app.schemas as schemas
from app.database.database import get_db

load_dotenv()


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES")
ACCESS_TOKEN_EXPIRE_MINUTES = float(ACCESS_TOKEN_EXPIRE_MINUTES)

def create_token(data: dict):
    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({'exp': expire})
    encoded_jwt = jwt.encode(to_encode,SECRET_KEY,algorithm=ALGORITHM)

    return encoded_jwt

def verify_token(token: str, credential_exception):
    try:
        payload = jwt.decode(token, SECRET_KEY, ALGORITHM)
        id: str = payload.get('id')

        if id is None:
            raise credential_exception
        
        token_data = schemas.TokenData(id=id)

    except InvalidTokenError:
        raise credential_exception
    
    return token_data

def get_current_user(token: str = Depends(oauth2_scheme), db: Connection = Depends(get_db)):
    credential_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='User cannot be authenticated')

    token = verify_token(token, credential_exception)

    if token is None:
        raise credential_exception

    with db.cursor() as cursor:
        cursor.execute('select id from users where id = %s', (token.id,))
        user = cursor.fetchone()

    if user is None:
        raise credential_exception
    
    return user
    