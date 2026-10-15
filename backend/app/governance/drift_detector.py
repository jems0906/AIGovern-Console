def detect_drift(record: dict) -> bool:
    return record.get("approved_value") != record.get("observed_value")