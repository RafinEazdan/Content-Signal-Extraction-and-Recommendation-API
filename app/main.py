from fastapi import FastAPI

from app.services.oauth import get_current_user
from app.database.session import get_db
from app.api.v1 import auth, channel, users, video

app = FastAPI()


app.include_router(users.router)
app.include_router(auth.router)
app.include_router(channel.router)
app.include_router(video.router)


@app.get("/")
def root():
    return {"Hello":"World!"}


# @app.on_event("shutdown")
# def shutdown():
#     pool.close()
