from fastapi import FastAPI
from app.api.v1 import auth, users

app = FastAPI()

app.include_router(auth.router)
app.include_router(users.router)


@app.get("/")
def root():
    return {"message": "Authentication Service"}
