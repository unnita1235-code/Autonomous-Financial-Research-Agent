import json
import os
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

class JobStore:
    def __init__(self):
        self._redis = None
        self._memory: Dict[str, Any] = {}
        self._try_redis()

    def _try_redis(self):
        url = os.getenv("REDIS_URL")
        if not url:
            return
        try:
            import redis
            client = redis.from_url(url, decode_responses=True)
            client.ping()
            self._redis = client
            logger.info("JobStore: Redis connected at %s", url)
        except Exception as e:
            logger.warning("JobStore: Redis unavailable (%s) — using in-memory", e)

    def set(self, job_id: str, data: Dict[str, Any], ttl: int = 86400):
        if self._redis:
            try:
                self._redis.setex(f"job:{job_id}", ttl, json.dumps(data, default=str))
                return
            except Exception as e:
                logger.warning("Redis set failed: %s", e)
        self._memory[job_id] = data

    def get(self, job_id: str) -> Optional[Dict[str, Any]]:
        if self._redis:
            try:
                raw = self._redis.get(f"job:{job_id}")
                if raw:
                    return json.loads(raw)
            except Exception as e:
                logger.warning("Redis get failed: %s", e)
        return self._memory.get(job_id)

    def update(self, job_id: str, updates: Dict[str, Any]):
        current = self.get(job_id) or {}
        current.update(updates)
        self.set(job_id, current)

JOB_STORE = JobStore()
