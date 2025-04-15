import redis
import json
from typing import Optional, TypeVar, Callable, Any
import logging

logger = logging.getLogger("uvicorn.error")

T = TypeVar('T')

class RedisCache:
    def __init__(self, host: str = "recommendations_cache", port: int = 6379, db: int = 0):
        self.redis_client = redis.Redis(host=host, port=port, db=db)

    def get(self, key: str) -> Optional[str]:
        value = self.redis_client.get(key)
        if value is not None:
            logger.info(f"Cache hit for key: {key}")
        else:
            logger.info(f"Cache miss for key: {key}")
        return value

    def set(self, key: str, value: str, ttl: int = 3600) -> bool:
        logger.info(f"Setting cache for key: {key} with TTL: {ttl}s")
        return self.redis_client.setex(key, ttl, value)

    def get_or_set(self, key: str, value_func: Callable[[], T], ttl: int = 3600) -> T:
        cached_value = self.get(key)
        if cached_value is not None:
            return json.loads(cached_value)
        
        logger.info(f"Cache miss, computing new value for key: {key}")
        value = value_func()
        self.set(key, json.dumps(value), ttl)
        return value

redis_cache = RedisCache() 