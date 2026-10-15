PHASES = ["core", "intelligence", "integrations", "automation_agents"]
ENTRY_CRITERIA = {
    "core": ["sso_scim_ready", "acceptable_use_approved", "retention_approved"],
    "intelligence": ["core_use_cases_validated", "training_complete", "audit_verified"],
    "integrations": ["data_owners_approved", "permissions_verified", "connector_allowlist_reviewed"],
    "automation_agents": ["agent_risk_reviews_complete", "write_actions_reviewed", "rollback_tested"],
}
REASSESSMENT = ["security", "privacy", "retention", "sharing", "support_readiness"]


def validate_gate(record: dict, siblings: list[dict]) -> None:
    if record["status"] == "planned":
        return
    phase = record["phase"]
    index = PHASES.index(phase)
    if index and not any(item["phase"] == PHASES[index - 1] and item["status"] == "completed" for item in siblings):
        raise ValueError("The preceding rollout phase must be completed first")
    if not all(record["entry_criteria"].get(key) is True for key in ENTRY_CRITERIA[phase]):
        raise ValueError("All required phase entry criteria must pass")
    if not all(record["reassessment"].get(key) is True for key in REASSESSMENT):
        raise ValueError("The governance reassessment checklist must be complete")
    if record["status"] == "completed" and not all(record["retrospective"].get(key) for key in ["use_cases", "barriers", "next_changes"]):
        raise ValueError("Completion requires use cases, barriers, and next-phase changes")