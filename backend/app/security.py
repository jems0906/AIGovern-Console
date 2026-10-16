import secrets
from functools import lru_cache

import jwt
from fastapi import Header, HTTPException
from jwt import PyJWKClient

from app.config import get_settings


@lru_cache(maxsize=8)
def _jwks_client(tenant_id: str) -> PyJWKClient:
    return PyJWKClient(f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys")


def _entra_identity(token: str, settings) -> dict:
    issuer = f"https://login.microsoftonline.com/{settings.entra_tenant_id}/v2.0"
    try:
        key = _jwks_client(settings.entra_tenant_id).get_signing_key_from_jwt(token).key
        claims = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience=settings.entra_api_audience,
            issuer=issuer,
            options={"require": ["exp", "iss", "aud", "tid", "oid"]},
        )
    except (jwt.PyJWTError, jwt.PyJWKClientError, ValueError) as exc:
        raise HTTPException(401, "Invalid or expired Microsoft Entra access token") from exc

    if claims["tid"].casefold() != settings.entra_tenant_id.casefold():
        raise HTTPException(401, "Access token belongs to a different Entra tenant")
    roles = claims.get("roles")
    if not isinstance(roles, list):
        raise HTTPException(403, "Microsoft Entra app role assignment is required")
    role_map = {
        settings.entra_admin_role: "admin",
        settings.entra_reviewer_role: "reviewer",
        settings.entra_viewer_role: "viewer",
    }
    role = next((role_map[item] for item in roles if item in role_map), None)
    if not role:
        raise HTTPException(403, "User has no AIGovern application role")
    return {"actor": f"entra:{claims['tid']}:{claims['oid']}", "role": role}


def identity(authorization: str = Header(default="")) -> dict:
    settings = get_settings()
    if settings.auth_mode == "entra":
        if not settings.entra_tenant_id or not settings.entra_api_client_id:
            raise HTTPException(503, "Microsoft Entra authentication is not configured")
        scheme, _, token = authorization.partition(" ")
        if scheme.casefold() != "bearer" or not token.strip():
            raise HTTPException(401, "Microsoft Entra bearer token required")
        return _entra_identity(token.strip(), settings)
    if settings.environment == "development" and not settings.admin_api_key:
        return {"actor": "local-demo-admin", "role": "admin"}
    scheme, _, token = authorization.partition(" ")
    token = token.strip() if scheme.casefold() == "bearer" else ""
    for role, key in [("admin", settings.admin_api_key), ("reviewer", settings.reviewer_api_key), ("viewer", settings.viewer_api_key)]:
        if key and secrets.compare_digest(token, key):
            return {"actor": f"api-key:{role}", "role": role}
    raise HTTPException(401, "Valid bearer credential required")


def require_write(user: dict, review: bool = False) -> None:
    if user["role"] == "viewer" or (review and user["role"] not in {"admin", "reviewer"}):
        raise HTTPException(403, "A governance reviewer credential is required")