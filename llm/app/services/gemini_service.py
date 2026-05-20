from google import genai
from fastapi import HTTPException, status

from app.core.config import settings


class GeminiService:
    def __init__(self):
        self.Client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model = settings.GEMINI_MODEL

    def generate(self, prompt:str, system: str | None = None) -> str:
        try:
            response = self.client.models.generate_content(model=self.model, content=prompt,
                                                           config = {
                                                               "system_instruction": system
                                                           } if system else None,)
            return response.text.strip()
        
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Gemini Error: {e}")
