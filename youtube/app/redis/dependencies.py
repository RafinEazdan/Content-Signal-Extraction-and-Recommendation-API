from .redis_client import RedisClient

redis_client = RedisClient()

def get_redis():
    return redis_client