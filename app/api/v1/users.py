from jinja2 import DictLoader
from app.services.oauth import get_current_user
import app.core.security as security
from app.database.session import get_db
from fastapi import Depends, HTTPException, status, Response, APIRouter
from psycopg import Connection
from psycopg.errors import UniqueViolation
import app.schemas.users as schemas
from typing import List


router = APIRouter(
    prefix='/users',
    tags=['Users']
)


# -------------------USERS---------------------
# get all users for admin use
# @router.get('/')
# def get_users(db: Connection = Depends(get_db)):
#     with db.cursor() as cursor:
#         cursor.execute(''' SELECT * from users; ''')
#         users = cursor.fetchall()
#     return users

@router.post('/', status_code=status.HTTP_201_CREATED, response_model=schemas.UserResponse)
def post_users( user:schemas.UserCreate, db: Connection = Depends(get_db)):
     # Hashing the Password
     hashed_pass = security.hash(user.password)
     user.password = hashed_pass
     try:
        with db.cursor() as cursor:
            cursor.execute('''Insert into users (email, username, hashed_password, profile_pic) VALUES (%s, %s, %s, %s) RETURNING id, email, created_at;''', (user.email, user.username, hashed_pass, user.profile_pic))
            new_user = cursor.fetchone()
        db.commit()
        return new_user

     except UniqueViolation:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_406_NOT_ACCEPTABLE, detail="Email Already Registered. Try login!")
     

@router.post('/verify')


@router.get('/profile', response_model=schemas.UserResponse)
def get_users(db: Connection = Depends(get_db), current_user: dict = Depends(get_current_user)):
    if current_user["id"] is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='You must login first!')
    with db.cursor() as cursor:
        cursor.execute(''' SELECT * from users where id = %s; ''', (current_user["id"],))
        users = cursor.fetchone()
    if users is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='User details is unavailable')
    return users

@router.delete('/profile/delete', status_code=status.HTTP_204_NO_CONTENT)
def delete_users(db: Connection = Depends(get_db), current_user: DictLoader = Depends(get_current_user)):
    with db.cursor() as cursor:
        cursor.execute('Delete from users where id = %s;',(current_user["id"],))
        deleted_user = cursor.rowcount

    db.commit()

    if deleted_user == 0:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not logged in!")
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)