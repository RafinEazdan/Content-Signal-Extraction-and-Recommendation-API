from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    AUTH_SERVICE_URL: str = "http://authentication:8001"
    YOUTUBE_SERVICE_URL: str = "http://api:8003"
    REDDIT_SERVICE_URL: str = "http://reddit:8002"
    LLM_SERVICE_URL: str = "http://llm:8004"

    class Config:
        env_file = ".env"


settings = Settings()

# Maps incoming path prefix → upstream base URL
# Order matters: longer prefixes first so they match before shorter ones.
ROUTE_MAP: list[tuple[str, str]] = [
    ("/auth", settings.AUTH_SERVICE_URL),
    ("/youtube", settings.YOUTUBE_SERVICE_URL),
    ("/reddit", settings.REDDIT_SERVICE_URL),
    ("/llm", settings.LLM_SERVICE_URL),
]
