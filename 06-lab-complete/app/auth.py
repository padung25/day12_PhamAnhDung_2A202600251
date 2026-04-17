from fastapi import Header, HTTPException
from .config import settings

def verify_api_key(
    x_api_key: str = Header(..., alias="X-API-Key"),
    x_user_id: str = Header(default="default-user", alias="X-User-Id"),
):
    """
    Verify API key from request header.

    - Nếu key đúng: trả về user_id để các dependency khác dùng tiếp
    - Nếu key sai: raise 401 Unauthorized
    """
    if x_api_key != settings.AGENT_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

    return x_user_id