from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.security import identity

router = APIRouter()


@router.get("/auth/config", tags=["session"])
def auth_config():
    settings = get_settings()
    return {
        "mode": settings.auth_mode,
        "tenant_id": settings.entra_tenant_id if settings.auth_mode == "entra" else "",
        "spa_client_id": settings.entra_spa_client_id if settings.auth_mode == "entra" else "",
        "api_scope": settings.entra_api_scope if settings.auth_mode == "entra" else "",
    }


@router.get("/health", tags=["health"])
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok"}


@router.get("/session", tags=["session"])
def session(user: dict = Depends(identity)):
    return {**user, "environment": get_settings().environment, "demo": user["actor"] == "local-demo-admin"}