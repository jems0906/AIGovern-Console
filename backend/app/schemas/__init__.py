from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Platform = Literal["claude", "chatgpt", "copilot"]
Kind = Literal["connector", "app", "plugin", "extension", "agent", "custom_gpt", "skill"]


class Common(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=200)
    platform: Platform
    tenant: str = Field(default="demo", min_length=1, max_length=120)
    owner: str = Field(min_length=1, max_length=200)


class RiskReview(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reviewer: str = Field(min_length=1)
    reviewed_at: date
    data_access_scope: str = Field(min_length=1)
    publishing_identity: Literal["personal", "shared_connection"]
    external_write_actions: bool
    notes: str = ""


class Allowlist(Common):
    kind: Kind
    external_id: str = Field(min_length=1)
    workspace_agent: bool = False
    status: Literal["submitted", "security_review", "data_owner_approval", "approved", "denied", "enabled", "retired"] = "submitted"
    risk_review: RiskReview | None = None
    data_owner_approval: str = ""
    justification: str = Field(min_length=1)


class InventoryItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    external_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    kind: Kind
    owner: str = "Unknown"
    version: str = ""


class Inventory(Common):
    items: list[InventoryItem] = Field(max_length=10000)
    captured_at: datetime
    reviewer: str = ""
    reviewed_at: date | None = None
    next_review_due: date | None = None

    @model_validator(mode="after")
    def unique_items(self):
        keys = [(item.kind, item.external_id) for item in self.items]
        if len(keys) != len(set(keys)):
            raise ValueError("Snapshot contains duplicate kind/external_id pairs")
        return self


class Skill(Common):
    version: str = Field(min_length=1)
    description: str = ""
    superseded: bool = False
    retirement_date: date | None = None
    versions: list[dict] = Field(default_factory=list)
    status: Literal["active", "retired"] = "active"


class Sharing(Common):
    setting: str = Field(min_length=1)
    approved_value: str = Field(min_length=1)
    observed_value: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    status: Literal["active"] = "active"


class Datasource(Common):
    approval_reference: str = ""
    permission_verified_at: date | None = None
    scope: str = Field(min_length=1)
    status: Literal["pending", "approved", "enabled", "retired"] = "pending"


class Rollout(Common):
    phase: Literal["core", "intelligence", "integrations", "automation_agents"]
    entry_criteria: dict[str, bool] = Field(default_factory=dict)
    reassessment: dict[str, bool] = Field(default_factory=dict)
    retrospective: dict[str, str] = Field(default_factory=dict)
    status: Literal["planned", "active", "completed"] = "planned"


class Baseline(Common):
    setting: str = Field(min_length=1)
    approved_value: str = Field(min_length=1)
    observed_value: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    status: Literal["active"] = "active"


class Change(Common):
    description: str = Field(min_length=1)
    baseline_id: str = Field(min_length=1)
    before_value: str = Field(min_length=1)
    after_value: str = Field(min_length=1)
    risk_level: Literal["low", "medium", "high", "critical"]
    privileged: bool = False
    approver: str = ""
    scheduled_start: datetime
    scheduled_end: datetime
    rollback_plan: str = ""
    outcome: str = ""
    status: Literal["draft", "approved", "implemented", "failed", "rolled_back"] = "draft"


class Evidence(Common):
    artifact_type: Literal["certification", "dpa", "baa", "vendor_control_change", "other"]
    reference: str = Field(min_length=1)
    expires_at: date | None = None
    obligations: str = ""
    control_change: str = ""
    posture_impact: str = ""
    status: Literal["pending", "approved", "expired", "superseded"] = "pending"


class Retention(Common):
    position: str = Field(min_length=1)
    approved_by: str = Field(min_length=1)
    approved_at: date
    review_due: date
    reference: str = Field(min_length=1)
    status: Literal["approved", "superseded"] = "approved"


class Incident(Common):
    category: Literal["confidential", "claimant", "employee", "production", "other"]
    severity: Literal["low", "medium", "high", "critical"]
    description: str = Field(min_length=1)
    occurred_at: datetime
    escalated_to: str = ""
    escalation_reference: str = ""
    resolution: str = ""
    status: Literal["open", "escalated", "resolved"] = "open"


SCHEMAS = {
    "allowlist": Allowlist, "inventory": Inventory, "skills": Skill,
    "sharing": Sharing, "datasources": Datasource, "rollout": Rollout,
    "baseline": Baseline, "changes": Change, "evidence": Evidence,
    "retention": Retention, "aup_incidents": Incident,
}