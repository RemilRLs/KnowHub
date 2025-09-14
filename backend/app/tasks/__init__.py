# app/tasks/setup.py
import os, dramatiq

from dramatiq.brokers.redis import RedisBroker
from dramatiq.results import Results
from dramatiq.results.backends import RedisBackend

password = os.getenv("REDIS_PASSWORD", "")
host = os.getenv("REDIS_HOST", "redis")
port = os.getenv("REDIS_PORT", "6379")
db   = os.getenv("REDIS_DB", "0")
REDIS_URL = f"redis://:{password}@{host}:{port}/{db}" if password else f"redis://{host}:{port}/{db}"

results_backend = RedisBackend(url=REDIS_URL)

broker = RedisBroker(url=REDIS_URL)
broker.add_middleware(Results(backend=results_backend))
dramatiq.set_broker(broker)

# Actors

from .ingest import ingest_document