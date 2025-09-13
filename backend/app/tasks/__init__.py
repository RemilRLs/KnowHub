import os, dramatiq
from dramatiq.brokers.redis import RedisBroker

password = os.getenv("REDIS_PASSWORD", "")
host = os.getenv("REDIS_HOST", "redis")
port = os.getenv("REDIS_PORT", "6379")
db   = os.getenv("REDIS_DB", "0")

REDIS_URL = f"redis://:{password}@{host}:{port}/{db}" if password else f"redis://{host}:{port}/{db}"

broker = RedisBroker(url=REDIS_URL)
dramatiq.set_broker(broker)