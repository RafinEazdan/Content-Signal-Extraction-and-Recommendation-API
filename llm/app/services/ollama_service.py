import httpx
from fastapi import HTTPException

from app.core.config import settings


class OllamaService:
    def __init__(self):
        self.url = f"{settings.OLLAMA_BASE_URL}/api/chat"
        self.model = settings.LLM_MODEL

    def generate(self, prompt: str, system: str | None = None) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        try:
            response = httpx.post(
                self.url,
                json={"model": self.model, "stream": False, "messages": messages},
                timeout=120,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=502, detail=f"Ollama error: {e.response.text}")
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Ollama unreachable: {e}")

        return response.json()["message"]["content"].strip()
