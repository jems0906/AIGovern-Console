def normalize(row: dict) -> dict:
    actor = row.get("actor", row.get("actor_email", ""))
    if isinstance(actor, dict):
        actor = actor.get("email_address") or actor.get("user_id") or actor.get("type") or "unknown"
    target = next((row[key] for key in ("mcp_server_id", "claude_project_id", "claude_chat_id", "skill_id", "artifact_id", "resource") if row.get(key)), "")
    return {"external_id": row.get("id", row.get("external_id", "")),
            "timestamp": row.get("created_at", row.get("timestamp")),
            "actor": actor,
            "action": row.get("type", row.get("event_type", row.get("action", ""))),
            "target": target or row.get("target", "unknown"),
            "outcome": row.get("outcome", "success")}