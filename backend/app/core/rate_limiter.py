import logging
import time
from typing import Any

import redis
from fastapi import Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse

from app.core.config import settings

logger = logging.getLogger("app.rate_limiter")

# Connect to Redis rate limit database partition
redis_limiter = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)


class SlidingWindowRateLimiter(BaseHTTPMiddleware):
    def __init__(
        self,
        app: Any,
        ip_limit: int = 100,  # 100 requests per minute per IP
        user_limit: int = 200,  # 200 requests per minute per User
        window_seconds: int = 60,
    ) -> None:
        super().__init__(app)
        self.ip_limit = ip_limit
        self.user_limit = user_limit
        self.window_seconds = window_seconds

    async def dispatch(self, request: Request, call_next: Any) -> Any:
        # Skip rate limiting check for public OpenAPI UI routes
        path = request.url.path
        if path in ["/", "/docs", "/openapi.json", "/health"]:
            return await call_next(request)

        now = time.time()
        clear_before = now - self.window_seconds

        # 1. Resolve identifiers
        ip = request.client.host if request.client else "Unknown IP"
        user_id = getattr(request.state, "user_id", None)

        try:
            pipe = redis_limiter.pipeline()

            # IP Rate Limiting Key check
            ip_key = f"rate_limit:ip:{ip}"
            pipe.zremrangebyscore(ip_key, 0, clear_before)
            pipe.zcard(ip_key)
            pipe.zadd(ip_key, {str(now): now})
            pipe.expire(ip_key, self.window_seconds + 5)

            # User Rate Limiting Key check (if authenticated)
            user_key = None
            if user_id:
                user_key = f"rate_limit:user:{user_id}"
                pipe.zremrangebyscore(user_key, 0, clear_before)
                pipe.zcard(user_key)
                pipe.zadd(user_key, {str(now): now})
                pipe.expire(user_key, self.window_seconds + 5)

            # Execute transactional commands pipeline
            results = pipe.execute()

            # Extract count results
            ip_count = results[1]
            if ip_count > self.ip_limit:
                logger.warning("IP Rate limit breached: %s", ip)
                return StarletteResponse(
                    "Too Many Requests. IP rate limit exceeded.",
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                )

            if user_key:
                # Offset in results array due to previous IP operations
                user_count = results[5]
                if user_count > self.user_limit:
                    logger.warning("User Rate limit breached: %s", user_id)
                    return StarletteResponse(
                        "Too Many Requests. User account rate limit exceeded.",
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    )

        except redis.RedisError as e:
            # Fallback warning: allow requests on Redis connection issues
            logger.error("Limiter Redis connection outage: %s", e)

        return await call_next(request)
