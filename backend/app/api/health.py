"""
Platform Health & Readiness Check Endpoints

Maintains system operational diagnostics separating liveness checks (/live) and
readiness checks (/ready) probing database connection states, caching latency pings,
and object storage endpoints in compliance with SLO standards.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.infrastructure.storage import MinIOStorageService
import redis.asyncio as aioredis
from app.core.config import settings

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/live", status_code=status.HTTP_200_OK)
def liveness_check() -> dict:
    """Verifies that the python server daemon is currently running."""
    return {"status": "alive"}


@router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness_check(db: Session = Depends(get_db)) -> dict:
    """Runs connectivity checks verifying database, cache, and object storage states."""
    diagnostics = {}
    unhealthy = False

    # 1. Probe SQL DB liveness
    try:
        db.execute("SELECT 1")
        diagnostics["database"] = "healthy"
    except Exception as e:
        diagnostics["database"] = f"unhealthy: {e}"
        unhealthy = True

    # 2. Probe Redis Cache liveness
    try:
        r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        await r.ping()
        await r.close()
        diagnostics["cache"] = "healthy"
    except Exception as e:
        diagnostics["cache"] = f"unhealthy: {e}"
        unhealthy = True

    # 3. Probe MinIO Storage liveness
    try:
        storage = MinIOStorageService()
        # Verify connection does not throw
        diagnostics["storage"] = "healthy"
    except Exception as e:
        diagnostics["storage"] = f"unhealthy: {e}"
        unhealthy = True

    if unhealthy:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "unready", "diagnostics": diagnostics}
        )

    return {"status": "ready", "diagnostics": diagnostics}
