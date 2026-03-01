from fastapi import APIRouter, Depends, HTTPException
from psycopg import Connection

from app.database.session import get_db
from app.redis.depends import get_redis
from app.services.oauth import get_current_user

router = APIRouter(
    prefix='/videos',
    tags=['Videos']
)

@router.post('/')