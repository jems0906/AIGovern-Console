def inventory_diff(current: list[dict], previous: list[dict], approvals: list[dict]) -> dict:
    previous_keys = {(item["kind"], item["external_id"]) for item in previous}
    current_keys = {(item["kind"], item["external_id"]) for item in current}
    approved_keys = {
        (item["kind"], item["external_id"]) for item in approvals
        if item["status"] in {"approved", "enabled"}
    }
    return {
        "new": [item for item in current if (item["kind"], item["external_id"]) not in previous_keys],
        "shadow": [item for item in current if (item["kind"], item["external_id"]) not in approved_keys],
        "removed": [item for item in previous if (item["kind"], item["external_id"]) not in current_keys],
    }