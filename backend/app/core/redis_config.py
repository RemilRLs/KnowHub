import os
from dramatiq.results.backends import RedisBackend
import redis

password = os.getenv("REDIS_PASSWORD", "")
host = os.getenv("REDIS_HOST", "redis")
port = os.getenv("REDIS_PORT", "6379")
db   = os.getenv("REDIS_DB", "0")
REDIS_URL = f"redis://:{password}@{host}:{port}/{db}" if password else f"redis://{host}:{port}/{db}"

redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)

results_backend = RedisBackend(url=REDIS_URL, namespace="knowhub:results")
