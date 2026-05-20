from fastapi import APIRouter

from app.schemas.generate import GenerateRequest, GenerateResponse
from app.services.ollama_service import OllamaService
from app.services.gemini_service import GeminiService

router = APIRouter(prefix="/generate", tags=["Generate"])


@router.post("", response_model=GenerateResponse)
def generate(request: GenerateRequest):
    service = GeminiService()
    text = service.generate(request.prompt, request.system)
    return GenerateResponse(text=text)
