from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    OLLAMA_BASE_URL: str
    LLM_MODEL: str

    class Config:
        env_file = ".env"


settings = Settings()
