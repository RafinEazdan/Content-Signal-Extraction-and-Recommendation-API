from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    YT_API_KEY: str
    DATABASE_URL : str
    SECRET_KEY : str
    POSTGRES_PASSWORD : str
    POSTGRES_DB : str
    ACCESS_TOKEN_EXPIRE_MINUTES : int
    ALGORITHM : str
    REDIS_URL : str
    HF_API_KEY : str
    OLLAMA_BASE_URL : str
    LLM_MODEL : str

    class Config:
        env_file = '.env'

settings = Settings()

