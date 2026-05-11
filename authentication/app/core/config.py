from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    REDIS_URL: str

    class Config:
        env_file = '.env'


settings = Settings()
