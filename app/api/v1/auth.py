from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from psycopg import Connection
import app.core.security as security
from app.services import oauth
import app.schemas.users as user_schema
from app.database.session import get_db

router = APIRouter(
    tags=["Login"]
)

@router.post('/login', response_model=user_schema.Token)
def login(user_credential: OAuth2PasswordRequestForm = Depends(), db: Connection = Depends(get_db)):
    with db.cursor() as cursor:
        cursor.execute('SELECT id,email,hashed_password as password from users where email = %s', (user_credential.username,))
        user = cursor.fetchone()

    if user is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Invalid Credentials')
    verify_pass = security.verify_pass(user_credential.password, user["password"])

    if verify_pass is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Invalid Credentials')
    access_token = oauth.create_token(data={'id': user["id"]})

    return{'token':access_token, 'token_type':'bearer'}
