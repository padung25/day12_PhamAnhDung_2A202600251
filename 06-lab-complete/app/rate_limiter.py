from datetime import datetime, timezone

import redis
from fastapi import HTTPException
from redis.exceptions import RedisError

from .config import settings

r = redis.from_url(settings.REDIS_URL, decode_responses=True)


def enforce_rate_limit(user_id: str):
    """Fixed window rate limiting per minute."""
    now = datetime.now(timezone.utc)
    minute_key = now.strftime("%Y-%m-%d:%H:%M")
    key = f"rate_limit:{user_id}:{minute_key}"

    try:
        current = r.incr(key)
        if current == 1:
            r.expire(key, 60)
    except RedisError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Rate limiter unavailable: {exc.__class__.__name__}",
        )

    if current > settings.RATE_LIMIT_PER_MINUTE:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded ({settings.RATE_LIMIT_PER_MINUTE}/min)",
        )

