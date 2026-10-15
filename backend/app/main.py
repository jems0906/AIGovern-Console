from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm.exc import StaleDataError

from app.api.crud import resource_router
from app.api.routes import allowlist, audit_logs, aup_incidents, baseline, changes, datasources, evidence, health, inventory, rollout, sharing, skills
from app.config import get_settings
from app.database import Base, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    if settings.environment not in {"development", "production", "test"}:
        raise RuntimeError("ENVIRONMENT must be development, test, or production")
    if settings.environment == "production" and len(settings.admin_api_key) < 32:
        raise RuntimeError("Production requires ADMIN_API_KEY with at least 32 characters")
    if settings.environment == "development":
        Base.metadata.create_all(engine)
    yield


app = FastAPI(title="AIGovern Console", version="1.0.0", lifespan=lifespan,
              description="Governance system of record. Imports simulate vendor feeds; no vendor settings are changed.")
app.add_middleware(CORSMiddleware, allow_origins=get_settings().cors_origins.split(","),
                   allow_methods=["GET", "POST", "PATCH"], allow_headers=["Authorization", "Content-Type"])


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@app.exception_handler(StaleDataError)
async def conflict(request: Request, exc: StaleDataError):
    return JSONResponse(status_code=409, content={"detail": "Concurrent modification; refresh and retry"})


for module in [health, allowlist, inventory, skills, sharing, datasources, rollout, baseline, changes, audit_logs, evidence, aup_incidents]:
    app.include_router(module.router, prefix="/api")
app.include_router(resource_router("retention"), prefix="/api")