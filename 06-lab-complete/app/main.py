import json
import logging
import signal
import sys
import time

import redis
from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from redis.exceptions import RedisError

from .auth import verify_api_key
from .config import settings
from .cost_guard import enforce_budget
from .rate_limiter import enforce_rate_limit

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def log(event: str, **kwargs):
    logger.info(json.dumps({"event": event, **kwargs}, ensure_ascii=False))


r = redis.from_url(settings.REDIS_URL, decode_responses=True)

accepting_requests = True
active_requests = 0


def shutdown_handler(signum, frame):
    global accepting_requests

    log("shutdown_start", signal=signum)
    accepting_requests = False

    wait = 0
    max_wait = 10
    while active_requests > 0 and wait < max_wait:
        log("waiting_requests", active=active_requests)
        time.sleep(1)
        wait += 1

    try:
        r.close()
    except RedisError:
        pass

    log("shutdown_done")
    sys.exit(0)


signal.signal(signal.SIGTERM, shutdown_handler)

app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION)


class AskRequest(BaseModel):
    question: str
    user_id: str | None = None


def mock_llm(question: str, history: list[str]) -> str:
    if history:
        previous_questions = [item[2:] for item in history if item.startswith("Q:")]
        if previous_questions:
            return (
                f"Your previous question was: '{previous_questions[-1]}'. "
                f"Now you asked: '{question}'"
            )
        return f"I have conversation context. Now you asked: '{question}'"
    return f"You asked: '{question}'"


@app.get("/", tags=["Info"])
def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "endpoints": {
            "ask": "POST /ask (requires X-API-Key)",
            "health": "GET /health",
            "ready": "GET /ready",
        },
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def ready():
    try:
        r.ping()
        if not accepting_requests:
            return JSONResponse(status_code=503, content={"status": "shutting_down"})
        return {"status": "ready"}
    except RedisError as exc:
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "detail": exc.__class__.__name__},
        )


@app.post("/ask")
def ask(payload: AskRequest, user_id: str = Depends(verify_api_key)):
    global active_requests

    if not accepting_requests:
        raise HTTPException(status_code=503, detail="Server shutting down")

    active_requests += 1
    try:
        actual_user_id = payload.user_id or user_id

        enforce_rate_limit(actual_user_id)
        enforce_budget(actual_user_id)

        key = f"history:{actual_user_id}"
        try:
            history = r.lrange(key, 0, -1)
        except RedisError as exc:
            raise HTTPException(
                status_code=503,
                detail=f"Conversation store unavailable: {exc.__class__.__name__}",
            )

        answer = mock_llm(payload.question, history)

        try:
            r.rpush(key, f"Q:{payload.question}")
            r.rpush(key, f"A:{answer}")
            r.expire(key, 7 * 24 * 3600)
        except RedisError as exc:
            raise HTTPException(
                status_code=503,
                detail=f"Conversation store unavailable: {exc.__class__.__name__}",
            )

        log("ask_ok", user=actual_user_id)
        return {
            "user_id": actual_user_id,
            "question": payload.question,
            "answer": answer,
        }
    finally:
        active_requests -= 1

