from datetime import datetime, timezone

import redis
from fastapi import HTTPException
from redis.exceptions import RedisError

from .config import settings

r = redis.from_url(settings.REDIS_URL, decode_responses=True)


def enforce_budget(user_id: str):
    """Monthly budget guard."""
    month_key = datetime.now(timezone.utc).strftime("%Y-%m")
    key = f"budget:{user_id}:{month_key}"

    try:
        current = float(r.get(key) or 0.0)
        cost = settings.COST_PER_REQUEST_USD

        if current + cost > settings.MONTHLY_BUDGET_USD:
            raise HTTPException(
                status_code=402,
                detail="Monthly budget exceeded",
            )

        new_total = current + cost
        r.set(key, new_total)
        r.expire(key, 32 * 24 * 3600)
    except HTTPException:
        raise
    except RedisError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Cost guard unavailable: {exc.__class__.__name__}",
        )

