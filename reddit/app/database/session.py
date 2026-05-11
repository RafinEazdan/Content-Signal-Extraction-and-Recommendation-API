import time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    while True:
        try:
            db = SessionLocal()
            db.execute(__import__("sqlalchemy").text("SELECT 1"))
            break
        except Exception as e:
            print(f"DB connection failed: {e}")
            time.sleep(2)

    try:
        yield db
    finally:
        db.close()
