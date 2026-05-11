from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from psycopg import Connection

import app.schemas.users as schemas
from app.database.session import get_db
from app.services.login_service import LoginService


router = APIRouter(tags=["Login"])


@router.post("/login", response_model=schemas.Token)
def login(user_credential: OAuth2PasswordRequestForm = Depends(), db: Connection = Depends(get_db)):
    service = LoginService(db)
    return service.login(user_credential.username, user_credential.password)
