import json


def normalize(row: dict) -> dict:
    if row.get("AuditData"):
        row = {**row, **json.loads(row["AuditData"])}
    return {"external_id": row.get("Id", row.get("external_id", "")),
            "timestamp": row.get("CreationTime", row.get("timestamp")),
            "actor": row.get("UserId", row.get("actor", "")),
            "action": row.get("Operation", row.get("action", "")),
            "target": row.get("ObjectId", row.get("target", "")),
            "outcome": row.get("ResultStatus", row.get("outcome", "success"))}