from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.security import identity

router = APIRouter()


@router.get("/health", tags=["health"])
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok"}


@router.get("/session", tags=["session"])
def session(user: dict = Depends(identity)):
    return {**user, "environment": get_settings().environment, "demo": user["actor"] == "local-demo-admin"}