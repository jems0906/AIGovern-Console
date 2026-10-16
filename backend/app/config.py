from functools import lru_cache
from pathlib import Path
from typing import Literal
from uuid import UUID

from pydantic import Field
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = f"sqlite:///{(Path(__file__).resolve().parents[1] / 'aigovern.db').as_posix()}"
    environment: str = "development"
    auth_mode: Literal["api_key", "entra"] = "api_key"
    admin_api_key: str = ""
    reviewer_api_key: str = ""
    viewer_api_key: str = ""
    entra_tenant_id: str = ""
    entra_spa_client_id: str = ""
    entra_api_client_id: str = ""
    entra_api_audience: str = ""
    entra_api_scope: str = ""
    entra_admin_role: str = "AIGovern.Admin"
    entra_reviewer_role: str = "AIGovern.Reviewer"
    entra_viewer_role: str = "AIGovern.Viewer"
    vendor_feeds_enabled: bool = False
    vendor_sync_interval_seconds: int = Field(default=300, ge=60, le=86400)
    vendor_sync_overlap_seconds: int = Field(default=3600, ge=0, le=604800)
    vendor_initial_lookback_hours: int = Field(default=24, ge=1, le=168)
    anthropic_compliance_api_key: str = ""
    anthropic_compliance_tenant: str = ""
    openai_compliance_api_key: str = ""
    openai_compliance_principal_id: str = ""
    openai_compliance_event_types: str = "AUTH_LOG"
    o365_tenant_id: str = ""
    o365_client_id: str = ""
    o365_client_secret: str = ""
    o365_publisher_id: str = ""
    o365_content_types: str = "Audit.AzureActiveDirectory,Audit.General"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @model_validator(mode="after")
    def validate_integrations(self):
        if self.auth_mode == "entra":
            required = {
                "ENTRA_TENANT_ID": self.entra_tenant_id,
                "ENTRA_SPA_CLIENT_ID": self.entra_spa_client_id,
                "ENTRA_API_CLIENT_ID": self.entra_api_client_id,
                "ENTRA_API_AUDIENCE": self.entra_api_audience,
                "ENTRA_API_SCOPE": self.entra_api_scope,
            }
            missing = [name for name, value in required.items() if not value]
            if missing:
                raise ValueError(f"AUTH_MODE=entra requires: {', '.join(missing)}")
            for name, value in (("ENTRA_TENANT_ID", self.entra_tenant_id),
                                ("ENTRA_SPA_CLIENT_ID", self.entra_spa_client_id),
                                ("ENTRA_API_CLIENT_ID", self.entra_api_client_id)):
                if not _is_guid(value):
                    raise ValueError(f"{name} must be a valid GUID")

        if self.vendor_feeds_enabled:
            groups = {
                "Anthropic": (self.anthropic_compliance_api_key, self.anthropic_compliance_tenant),
                "OpenAI": (self.openai_compliance_api_key, self.openai_compliance_principal_id),
                "Microsoft 365": (self.o365_tenant_id, self.o365_client_id, self.o365_client_secret,
                                  self.o365_publisher_id),
            }
            incomplete = [name for name, values in groups.items() if any(values) and not all(values)]
            configured = [name for name, values in groups.items() if all(values)]
            if incomplete:
                raise ValueError(f"Incomplete vendor feed configuration: {', '.join(incomplete)}")
            if not configured:
                raise ValueError("VENDOR_FEEDS_ENABLED requires at least one complete vendor feed configuration")
            if all(groups["Microsoft 365"]):
                for name, value in (("O365_TENANT_ID", self.o365_tenant_id),
                                    ("O365_CLIENT_ID", self.o365_client_id),
                                    ("O365_PUBLISHER_ID", self.o365_publisher_id)):
                    if not _is_guid(value):
                        raise ValueError(f"{name} must be a valid GUID")
        return self


def _is_guid(value: str) -> bool:
    try:
        UUID(value)
        return True
    except (ValueError, TypeError, AttributeError):
        return False


@lru_cache
def get_settings() -> Settings:
    return Settings()