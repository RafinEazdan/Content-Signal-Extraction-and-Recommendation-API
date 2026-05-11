import psycopg
from psycopg.rows import dict_row
import time
from app.core.config import settings


def get_db():
    while True:
        try:
            conn = psycopg.connect(settings.DATABASE_URL, row_factory=dict_row)
            break
        except Exception as e:
            print("DB Connection Failed. Error=", e)
            time.sleep(2)
    try:
        yield conn
    finally:
        conn.close()
