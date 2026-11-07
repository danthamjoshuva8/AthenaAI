import json
import logging

import redis

from redis.exceptions import RedisError

from app.config.settings import settings


logger = logging.getLogger(__name__)


class CacheManager:
    """
    Centralized Redis cache manager.

    Provides common methods for reading, writing,
    deleting and checking cached values.

    Redis failures should not break trading calculations.
    """

    def __init__(self):

        self.enabled = settings.CACHE_ENABLED

        self.client = redis.Redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
            health_check_interval=30
        )

    def connect(self):
        """Check Redis connectivity."""

        if not self.enabled:
            return False

        try:

            self.client.ping()

            logger.info(
                "Redis connected",
                extra={
                    "event": "redis_connected"
                }
            )

            return True

        except RedisError:

            logger.warning(
                "Redis unavailable; cache disabled for this operation",
                extra={
                    "event": "redis_connection_failed"
                }
            )

            return False

    def get_json(self, key: str):
        """
        Retrieve a JSON value from Redis.

        Returns:
            Cached Python object or None.
        """

        if not self.enabled:
            return None

        try:

            value = self.client.get(key)

            if value is None:

                logger.debug(
                    "Cache miss",
                    extra={
                        "event": "cache_miss"
                    }
                )

                return None

            logger.debug(
                "Cache hit",
                extra={
                    "event": "cache_hit"
                }
            )

            return json.loads(value)

        except (RedisError, json.JSONDecodeError):

            logger.exception(
                "Cache read failed",
                extra={
                    "event": "cache_read_failed"
                }
            )

            return None

    def set_json(
        self,
        key: str,
        value,
        ttl: int = None
    ):
        """
        Store a JSON-compatible value in Redis.

        Args:
            key: Unique cache key.
            value: Value to serialize.
            ttl: Expiration time in seconds.
        """

        if not self.enabled:
            return False

        try:

            serialized = json.dumps(
                value,
                default=str
            )

            self.client.set(
                key,
                serialized,
                ex=ttl or settings.CACHE_DEFAULT_TTL
            )

            return True

        except (RedisError, TypeError, ValueError):

            logger.exception(
                "Cache write failed",
                extra={
                    "event": "cache_write_failed"
                }
            )

            return False

    def delete(self, key: str):
        """Delete a cached entry."""

        if not self.enabled:
            return False

        try:

            self.client.delete(key)

            return True

        except RedisError:

            logger.exception(
                "Cache deletion failed",
                extra={
                    "event": "cache_delete_failed"
                }
            )

            return False

    def close(self):
        """Close Redis connections."""

        self.client.close()


cache_manager = CacheManager()