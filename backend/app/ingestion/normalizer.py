import csv
import io
import json
from datetime import datetime, timezone

from fastapi import HTTPException, UploadFile
from pydantic import BaseModel, Field, field_validator


class NormalizedEvent(BaseModel):
    external_id: str = Field(min_length=1)
    timestamp: datetime
    actor: str = Field(min_length=1)
    action: str = Field(min_length=1)
    target: str = Field(min_length=1)
    outcome: str = "success"

    @field_validator("timestamp")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if not value.tzinfo:
            raise ValueError("Audit timestamps must include a timezone")
        return value.astimezone(timezone.utc)


async def load_upload(file: UploadFile) -> list[dict]:
    raw = await file.read(5_000_001)
    if len(raw) > 5_000_000:
        raise HTTPException(413, "Import exceeds the 5 MB limit")
    try:
        text = raw.decode("utf-8-sig")
        if (file.filename or "").lower().endswith(".csv"):
            result = list(csv.DictReader(io.StringIO(text)))
        else:
            result = json.loads(text)
            if isinstance(result, dict):
                result = result.get("items", result.get("events"))
        if not isinstance(result, list) or not all(isinstance(item, dict) for item in result):
            raise ValueError("Expected a JSON array, items/events envelope, or CSV rows")
        if len(result) > 10000:
            raise ValueError("An import may contain at most 10,000 rows")
        return result
    except (ValueError, UnicodeError) as exc:
        raise HTTPException(422, f"Invalid import: {exc}") from exc