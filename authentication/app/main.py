from fastapi import FastAPI
from sqlalchemy import create_engine
from app.api.v1 import auth, users
from app.database.base import Base
from app.core.config import settings
import app.models.user  # noqa: F401 — registers User with Base.metadata

app = FastAPI()

app.include_router(auth.router)
app.include_router(users.router)


@app.on_event("startup")
def create_tables():
    engine = create_engine(settings.DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1))
    Base.metadata.create_all(bind=engine)


@app.get("/")
def root():
    return {"message": "Authentication Service"}
