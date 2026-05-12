from fastapi import FastAPI

from app.api.v1 import video_recommendation
from app.api.v1 import channel, comment, comment_analysis, metric, video

app = FastAPI()


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
