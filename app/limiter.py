import os
from slowapi import Limiter
from slowapi.util import get_remote_address

def _storage_uri() -> str:
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        return redis_url
    return "memory://"

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=_storage_uri(),
    default_limits=["200/hour"],
)
