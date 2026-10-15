def normalize(row: dict) -> dict:
    return {"external_id": row.get("event_id", row.get("external_id", "")),
            "timestamp": row.get("occurred_at", row.get("timestamp")),
            "actor": row.get("user_email", row.get("actor", "")),
            "action": row.get("event_type", row.get("action", "")),
            "target": row.get("resource_id", row.get("target", "")),
            "outcome": row.get("result", row.get("outcome", "success"))}