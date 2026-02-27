import psycopg
from psycopg.rows import dict_row
import time
from app.core.config import settings

DATABASE_URL = settings.DATABASE_URL

def get_db():
    while True:
        try:
            conn = psycopg.connect(
                DATABASE_URL,
                row_factory=dict_row
            )
            print("DB is connected!!!!!!")
            break
        except Exception as e:
            print("DB Connection Failed.\nError= ",e)
            time.sleep(2)

    try:
        yield conn

    finally:
        conn.close()