import json
import logging
from typing import Callable, Awaitable
from fastapi import Request, Response
from fastapi.responses import Response as FastAPIResponse
from starlette.middleware.base import BaseHTTPMiddleware
import redis.asyncio as aioredis
from app.core.config import settings

logger = logging.getLogger(__name__)

class IdempotencyMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self._redis_client = None

    @property
    def redis_client(self):
        if hasattr(self.__class__, "_mock_redis") and self.__class__._mock_redis is not None:
            return self.__class__._mock_redis
        if self._redis_client is None:
            self._redis_client = aioredis.from_url(settings.REDIS_URL)
        return self._redis_client

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        # We only apply idempotency checks on mutating meeting endpoints
        if request.method not in ("POST", "PUT", "PATCH") or "/api/v1/meetings" not in request.url.path:
            return await call_next(request)

        idempotency_key = request.headers.get("Idempotency-Key")
        if not idempotency_key:
            return await call_next(request)

        # Scoping key by workspace/tenant to avoid collision risks across different workspaces
        # (Fall back to default if workspace context is not yet resolved by active route middleware)
        workspace_id = request.headers.get("X-Workspace-ID", "global")
        redis_key = f"idempotency:{workspace_id}:{idempotency_key}"

        # 1. Check Redis status
        try:
            cached_data = await self.redis_client.get(redis_key)
            if cached_data:
                cached_json = json.loads(cached_data)
                status = cached_json.get("status")

                if status == "PROCESSING":
                    # Replay requested before first execution completes
                    return Response(
                        content=json.dumps({"error": "Concurrent request processing under the same Idempotency-Key."}),
                        status_code=409,
                        media_type="application/json"
                    )
                elif status == "RESOLVED":
                    # Return cached response details
                    return Response(
                        content=cached_json.get("body"),
                        status_code=cached_json.get("status_code"),
                        headers=cached_json.get("headers"),
                        media_type="application/json"
                    )
        except Exception as e:
            logger.error(f"Error checking idempotency cache: {e}", exc_info=True)

        # 2. Lock key as PROCESSING
        try:
            # Set with a short 2-minute lock TTL to prevent permanent locks if backend crashes
            await self.redis_client.set(redis_key, json.dumps({"status": "PROCESSING"}), ex=120)
        except Exception as e:
            logger.error(f"Error locking idempotency key: {e}", exc_info=True)

        # 3. Process request
        response = await call_next(request)

        # 4. Resolve key with response body & headers
        # We only cache successful/client error codes (not 5xx server errors, so clients can retry them)
        if response.status_code < 500:
            body_bytes = b""
            try:
                async for chunk in response.body_iterator:
                    body_bytes += chunk
            except Exception as body_err:
                logger.error(f"Error reading body stream: {body_err}", exc_info=True)
                return response

            try:
                cached_response = {
                    "status": "RESOLVED",
                    "status_code": response.status_code,
                    "body": body_bytes.decode("utf-8", errors="ignore"),
                    "headers": {k: v for k, v in response.headers.items() if k.lower() not in ("content-length", "date")}
                }
                # Save resolved response with 24-hour TTL (86400 seconds)
                await self.redis_client.set(redis_key, json.dumps(cached_response), ex=86400)
            except Exception as redis_err:
                logger.error(f"Error saving resolved response: {redis_err}", exc_info=True)

            # Return fresh response wrapper holding the original bytes (even if Redis cache write failed)
            return Response(
                content=body_bytes,
                status_code=response.status_code,
                headers=response.headers,
                media_type=response.media_type
            )

        return response
