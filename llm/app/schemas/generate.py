from pydantic import BaseModel


class GenerateRequest(BaseModel):
    prompt: str
    system: str | None = None


class GenerateResponse(BaseModel):
    text: str
