def normalize(row: dict) -> dict:
    initiated_by = row.get("initiatedBy") or {}
    user = initiated_by.get("user") or {}
    app = initiated_by.get("app") or {}
    actor = (user.get("userPrincipalName") or user.get("displayName") or user.get("id")
             or app.get("displayName") or app.get("appId") or "unknown")
    targets = row.get("targetResources") or []
    target = "unknown"
    if targets and isinstance(targets[0], dict):
        target_resource = targets[0]
        target = target_resource.get("displayName") or target_resource.get("id") or target_resource.get("type") or target
    return {
        "external_id": row.get("id") or row.get("correlationId") or "unknown",
        "timestamp": row.get("activityDateTime"),
        "actor": actor,
        "action": row.get("activityDisplayName") or row.get("operationType") or row.get("category") or "unknown",
        "target": target,
        "outcome": row.get("result") or "recorded",
    }