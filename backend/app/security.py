import secrets

from fastapi import Header, HTTPException

from app.config import get_settings


def identity(authorization: str = Header(default="")) -> dict:
    settings = get_settings()
    if settings.environment == "development" and not settings.admin_api_key:
        return {"actor": "local-demo-admin", "role": "admin"}
    token = authorization.removeprefix("Bearer ")
    for role, key in [("admin", settings.admin_api_key), ("reviewer", settings.reviewer_api_key), ("viewer", settings.viewer_api_key)]:
        if key and secrets.compare_digest(token, key):
            return {"actor": f"api-key:{role}", "role": role}
    raise HTTPException(401, "Valid bearer credential required")


def require_write(user: dict, review: bool = False) -> None:
    if user["role"] == "viewer" or (review and user["role"] not in {"admin", "reviewer"}):
        raise HTTPException(403, "A governance reviewer credential is required")