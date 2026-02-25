from fastapi import FastAPI

from app.routers import users
from app.auth.oauth import get_current_user
from app.database.database import get_db

app = FastAPI()


app.include_router(users.router)

@app.get("/")
def root():
    return {"Hello":"World!"}

