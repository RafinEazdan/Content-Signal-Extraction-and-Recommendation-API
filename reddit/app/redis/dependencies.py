from .redis_client import RedisClient

redis_client = RedisClient()


def get_redis() -> RedisClient:
    return redis_client
