from fastapi import FastAPI

from app.api import users
from app.services.oauth import get_current_user
from app.database.session import get_db
from app.api import auth

app = FastAPI()


app.include_router(users.router)
app.include_router(auth.router)


@app.get("/")
def root():
    return {"Hello":"World!"}

