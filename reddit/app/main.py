from fastapi import FastAPI
from app.api.v1 import ideas

app = FastAPI(title="Reddit Trending Ideas")

app.include_router(ideas.router)


@app.get("/")
def root():
    return {"service": "reddit-ideas"}
