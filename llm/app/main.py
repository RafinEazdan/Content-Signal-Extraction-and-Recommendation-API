from fastapi import FastAPI
from app.api.v1 import generate

app = FastAPI(title="LLM Service")

app.include_router(generate.router)


@app.get("/health")
def health():
    return {"status": "ok"}
