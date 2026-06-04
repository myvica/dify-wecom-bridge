import redis
import json
from typing import Optional, Any
from app.config import settings


class RedisClient:
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        db: Optional[int] = None,
        password: Optional[str] = None,
    ):
        self.host = host or settings.redis_host
        self.port = port or settings.redis_port
        self.db = db if db is not None else settings.redis_db
        self.password = password if password is not None else settings.redis_password
        self._client: Optional[redis.Redis] = None
        self._connect()

    def _connect(self):
        self._client = redis.Redis(
            host=self.host,
            port=self.port,
            db=self.db,
            password=self.password,
            decode_responses=True,
        )

    def get(self, key: str) -> Optional[Any]:
        try:
            value = self._client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception:
            return None

    def set(self, key: str, value: Any, ex: Optional[int] = None):
        try:
            self._client.set(key, json.dumps(value), ex=ex)
        except Exception:
            pass

    def delete(self, key: str):
        try:
            self._client.delete(key)
        except Exception:
            pass

    def get_session(self, session_key: str) -> Optional[dict]:
        return self.get(f"session:{session_key}")

    def set_session(self, session_key: str, session_data: dict, ex: int = 86400 * 7):
        self.set(f"session:{session_key}", session_data, ex=ex)

    def delete_session(self, session_key: str):
        self.delete(f"session:{session_key}")
