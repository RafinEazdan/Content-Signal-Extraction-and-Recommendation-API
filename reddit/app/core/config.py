from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    REDIS_URL: str
    RAPIDAPI_KEY: str
    LLM_SERVICE_URL: str

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
