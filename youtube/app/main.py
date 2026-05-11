from fastapi import FastAPI

from youtube.app.services.oauth import get_current_user
from youtube.app.database.session import get_db
from youtube.app.api.v1 import video_recommendation
from youtube.app.api.v1 import auth, channel, comment, comment_analysis, metric, users, video

app = FastAPI()


app.include_router(users.router)
app.include_router(auth.router)
app.include_router(channel.router)
app.include_router(video.router)
app.include_router(metric.router)
app.include_router(comment.router)
app.include_router(comment_analysis.router)
app.include_router(video_recommendation.router)


@app.get("/")
def root():
    return {"Hello":"World!"}


# @app.on_event("shutdown")
# def shutdown():
#     pool.close()
