from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    YT_API_KEY: str
    DATABASE_URL : str
    SECRET_KEY : str
    POSTGRES_PASSWORD : str
    ACCESS_TOKEN_EXPIRE_MINUTES : int
    ALGORITHM : str
    REDIS_URL : str

    class Config:
        env_file = '.env'

settings = Settings()

