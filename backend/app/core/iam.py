import contextvars
import logging
import uuid
from typing import Any

import redis
from fastapi import (
    Depends,
    HTTPException,
    Request,
    WebSocket,
    WebSocketException,
    status,
)
from sqlalchemy import event
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse

from app.core.config import settings
from app.core.database import get_db
from app.core.jwks import jwks_manager
from app.core.metrics import metrics_collector

logger = logging.getLogger("app.iam")

# Context variable managing active request workspace context safely across threads
current_workspace_id: contextvars.ContextVar[uuid.UUID | None] = contextvars.ContextVar(
    "current_workspace_id", default=None
)

# Connect to redis instance
redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)

# Granular Permission Scopes definition
ROLE_PERMISSIONS = {
    "Owner": {
        "meeting.read",
        "meeting.write",
        "meeting.delete",
        "meeting.export",
        "meeting.share",
        "meeting.manage",
        "tasks.read",
        "tasks.write",
        "workspace.invite",
        "workspace.delete",
        "conflicts.write",
    },
    "Admin": {
        "meeting.read",
        "meeting.write",
        "meeting.delete",
        "meeting.export",
        "meeting.share",
        "meeting.manage",
        "tasks.read",
        "tasks.write",
        "workspace.invite",
        "conflicts.write",
    },
    "Manager": {
        "meeting.read",
        "meeting.write",
        "meeting.export",
        "tasks.read",
        "tasks.write",
        "conflicts.write",
    },
    "Member": {"meeting.read", "meeting.write", "tasks.read"},
}


def load_permissions_for_role(role: str) -> set[str]:
    """Resolves granular scopes linked to roles."""
    return ROLE_PERMISSIONS.get(role, set())


def cache_user_permissions(
    user_id: uuid.UUID, workspace_id: uuid.UUID, permissions: set[str]
) -> None:
    """Stores resolved user permissions in Redis for fast API gateway lookups."""
    cache_key = f"user:permissions:{user_id}:{workspace_id}"
    try:
        if permissions:
            redis_client.delete(cache_key)
            redis_client.sadd(cache_key, *permissions)
            redis_client.expire(cache_key, 900)  # TTL of 15 minutes matching JWT
    except redis.RedisError as e:
        logger.warning("Failed writing to Redis cache permissions store: %s", e)


def get_cached_user_permissions(
    user_id: uuid.UUID, workspace_id: uuid.UUID
) -> set[str] | None:
    """Retrieves cached permission scopes from Redis."""
    cache_key = f"user:permissions:{user_id}:{workspace_id}"
    try:
        if redis_client.exists(cache_key):
            from app.core.metrics import metrics_collector

            metrics_collector.increment("permission_cache_hits")
            return set(redis_client.smembers(cache_key))
        else:
            from app.core.metrics import metrics_collector

            metrics_collector.increment("permission_cache_misses")
            return None
    except redis.RedisError as e:
        logger.warning("Failed querying Redis cache permissions store: %s", e)
        return None


def invalidate_user_permissions(user_id: uuid.UUID, workspace_id: uuid.UUID) -> None:
    """Purges cached permission scopes from Redis upon role alterations."""
    cache_key = f"user:permissions:{user_id}:{workspace_id}"
    try:
        redis_client.delete(cache_key)
    except redis.RedisError as e:
        logger.warning("Failed invalidating Redis cache permissions: %s", e)


def get_user_permissions(
    db: Session, user_id: uuid.UUID, workspace_id: uuid.UUID
) -> set[str]:
    """Queries and returns user workspace permissions, leveraging Redis caches."""
    cached = get_cached_user_permissions(user_id, workspace_id)
    if cached is not None:
        return cached

    # Cache miss: query database membership role mapping
    from app.models.auth import Membership

    membership = (
        db.query(Membership)
        .filter(Membership.user_id == user_id, Membership.workspace_id == workspace_id)
        .first()
    )

    if not membership:
        return set()

    permissions = load_permissions_for_role(membership.role)
    cache_user_permissions(user_id, workspace_id, permissions)
    return permissions


# ==========================================
# CUSTOM FASTAPI IAM MIDDLEWARE
# ==========================================


class IAMMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Any) -> Any:
        path = request.url.path
        public_auth_paths = [
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/api/v1/auth/verify",
            "/api/v1/auth/refresh",
            "/api/v1/auth/oauth/google",
            "/api/v1/auth/oauth/google/callback",
            "/api/v1/auth/.well-known/jwks.json",
        ]
        is_public = (
            path in public_auth_paths or 
            path in ["/", "/docs", "/openapi.json", "/health", "/metrics"] or
            path.startswith("/api/v1/health/")
        )
        if is_public:
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return StarletteResponse(
                "Unauthorized. Missing authorization header.",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        token = auth_header.split(" ")[1]
        try:
            payload = jwks_manager.verify_token(token)
            user_id = uuid.UUID(payload["sub"])
            workspace_id_str = payload.get("workspace_id")
            workspace_id = uuid.UUID(workspace_id_str) if workspace_id_str else None

            # Bind identities to active request state
            request.state.user_id = user_id
            request.state.workspace_id = workspace_id

            # Enforce active workspace context var isolation scope
            context_token = current_workspace_id.set(workspace_id)
            try:
                response = await call_next(request)
                return response
            finally:
                current_workspace_id.reset(context_token)
        except Exception as e:
            # Increment denied metrics
            from app.core.metrics import metrics_collector

            metrics_collector.increment("authorization_denied_total")
            return StarletteResponse(
                f"Unauthorized. Invalid token signature or claims: {e}",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )


# ==========================================
# ROUTE SCOPE PERMISSION ASSERTION CHECKER
# ==========================================


class PermissionRequirement:
    def __init__(self, required_permission: str):
        self.required_permission = required_permission

    def __call__(self, request: Request, db: Session = Depends(get_db)) -> None:
        """Verifies if the requesting identity holds the required scope."""
        user_id = getattr(request.state, "user_id", None)
        workspace_id = getattr(request.state, "workspace_id", None)

        if not user_id or not workspace_id:
            from app.core.metrics import metrics_collector

            metrics_collector.increment("authorization_denied_total")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unauthorized. Session context missing.",
            )

        permissions = get_user_permissions(db, user_id, workspace_id)
        if self.required_permission not in permissions:
            from app.core.metrics import metrics_collector

            metrics_collector.increment("authorization_denied_total")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Forbidden. Insufficient scope requirements: "
                    f"missing {self.required_permission}"
                ),
            )


# ==========================================
# SQLALCHEMY BEFORE_FLUSH EVENT HOOK (RLS)
# ==========================================


@event.listens_for(Session, "before_flush")
def enforce_tenant_isolation_flush(
    session: Session, flush_context: Any, instances: Any
) -> None:
    """SQLAlchemy hook enforcing tenant write isolation.

    Verifies that the workspace_id matches the active request context variable.
    """
    active_ws = current_workspace_id.get()
    if active_ws is None:
        # If no workspace context is active, bypass check
        # (e.g. system registration, migrations)
        return

    # Check newly created or modified instances
    for obj in session.new | session.dirty:
        if hasattr(obj, "workspace_id"):
            val = obj.workspace_id
            if val is not None and val != active_ws:
                metrics_collector.increment("rls_violation_total")
                raise PermissionError(
                    "Cross-workspace query or modification denied by RLS policy."
                )


async def get_websocket_user(websocket: WebSocket) -> uuid.UUID:
    """Verifies WebSocket handshake tokens passed via query parameters."""
    token = websocket.query_params.get("token")
    if not token:
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Missing token query parameter",
        )
    try:
        payload = jwks_manager.verify_token(token)
        return uuid.UUID(payload["sub"])
    except Exception as e:
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason=f"Invalid or expired token signature: {e}",
        ) from e
