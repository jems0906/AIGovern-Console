def normalize(row: dict) -> dict:
    return {"external_id": row.get("id", row.get("external_id", "")),
            "timestamp": row.get("created_at", row.get("timestamp")),
            "actor": row.get("actor_email", row.get("actor", "")),
            "action": row.get("event_type", row.get("action", "")),
            "target": row.get("resource", row.get("target", "")),
            "outcome": row.get("outcome", "success")}