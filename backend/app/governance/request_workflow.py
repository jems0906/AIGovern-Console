TRANSITIONS = {
    "submitted": {"security_review"},
    "security_review": {"data_owner_approval", "denied"},
    "data_owner_approval": {"approved", "denied"},
    "approved": {"enabled", "retired"},
    "enabled": {"retired"},
    "denied": {"retired"},
    "retired": set(),
}


def validate_transition(current: str, target: str, record: dict) -> None:
    if target not in TRANSITIONS.get(current, set()):
        raise ValueError(f"Transition {current} -> {target} is not permitted")
    if target in {"data_owner_approval", "approved", "enabled"}:
        review = record.get("risk_review") or {}
        required = ("reviewer", "reviewed_at", "data_access_scope", "publishing_identity")
        if not all(review.get(field) for field in required):
            raise ValueError("A documented security risk review is required")
        if review["publishing_identity"] not in {"personal", "shared_connection"}:
            raise ValueError("Publishing identity must be personal or shared_connection")
        if not isinstance(review.get("external_write_actions"), bool):
            raise ValueError("External write actions must be explicitly reviewed")
    if target in {"approved", "enabled"} and not record.get("data_owner_approval"):
        raise ValueError("Documented data owner approval is required")


def activation_status(record: dict) -> str:
    return "enabled" if record.get("status") == "enabled" else "disabled"