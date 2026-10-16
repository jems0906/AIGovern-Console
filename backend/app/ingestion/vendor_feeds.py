import asyncio
import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit

import httpx
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import SessionLocal
from app.ingestion import chatgpt_compliance, claude_audit, purview_audit
from app.ingestion.normalizer import NormalizedEvent
from app.models import Record
from app.services import log_event

logger = logging.getLogger(__name__)
MAX_PAGES = 1000
MAX_EVENTS_PER_SYNC = 50000
MAX_CONTENT_BYTES = 50_000_000
O365_HOSTS = {"manage.office.com"}


class VendorFeedError(Exception):
    pass


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _string(value, fallback: str = "unknown") -> str:
    if isinstance(value, dict):
        value = value.get("email_address") or value.get("email") or value.get("user_id") or value.get("id") or value.get("name")
    if value is None or value == "":
        return fallback
    return str(value)


def normalize_openai_event(row: dict, log_id: str, index: int) -> dict:
    """Reduce Compliance Logs payloads to the existing minimal audit schema."""
    return {
        "external_id": _string(row.get("event_id") or row.get("id"), f"{log_id}:{index}"),
        "timestamp": row.get("occurred_at") or row.get("created_at") or row.get("timestamp") or row.get("time"),
        "actor": _string(row.get("user_email") or row.get("email") or row.get("user_id") or row.get("actor")),
        "action": _string(row.get("event_type") or row.get("type") or row.get("action") or row.get("operation")),
        "target": _string(row.get("resource_id") or row.get("resource") or row.get("target") or row.get("endpoint")),
        "outcome": _string(row.get("result") or row.get("status") or row.get("outcome"), "recorded"),
    }


def _parse_event_file(content: bytes, log_id: str) -> list[dict]:
    try:
        payload = json.loads(content)
    except (json.JSONDecodeError, UnicodeDecodeError):
        try:
            payload = [json.loads(line) for line in content.decode("utf-8-sig").splitlines() if line.strip()]
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise VendorFeedError("Downloaded compliance log is not valid JSON") from exc
    if isinstance(payload, dict):
        payload = payload.get("data", payload.get("events", [payload]))
    if not isinstance(payload, list) or not all(isinstance(item, dict) for item in payload):
        raise VendorFeedError("Downloaded compliance log has an unsupported shape")
    if len(payload) > MAX_EVENTS_PER_SYNC:
        raise VendorFeedError("Downloaded compliance log exceeds the event limit")
    return [normalize_openai_event(row, log_id, index) for index, row in enumerate(payload)]


def _checkpoint_id(platform: str, tenant: str, source: str) -> str:
    return hashlib.sha256(f"{platform}:{tenant}:{source}".encode()).hexdigest()


def _checkpoint(db: Session, platform: str, tenant: str, source: str) -> Record | None:
    return db.scalar(select(Record).where(
        Record.resource == "vendor_feed_states",
        Record.platform == platform,
        Record.tenant == tenant,
        Record.dedup_key == _checkpoint_id(platform, tenant, source),
    ))


def _save_checkpoint(platform: str, tenant: str, source: str, cursor, error: str = "") -> None:
    with SessionLocal() as db:
        record = _checkpoint(db, platform, tenant, source)
        previous = record.data if record else {}
        data = {
            "source": source,
            "cursor": cursor if cursor is not None else previous.get("cursor"),
            "last_success_at": _iso(_utc_now()) if not error else previous.get("last_success_at"),
            "status": "error" if error else "ok",
            "last_error": error,
        }
        if record:
            record.data = data
        else:
            db.add(Record(resource="vendor_feed_states", platform=platform, tenant=tenant,
                          dedup_key=_checkpoint_id(platform, tenant, source), data=data))
        db.commit()


def _store_events(platform: str, tenant: str, raw_events: list[dict], normalizer, actor: str) -> int:
    if len(raw_events) > MAX_EVENTS_PER_SYNC:
        raise VendorFeedError("Feed response exceeds the event limit")
    normalized = [NormalizedEvent.model_validate(normalizer(row)).model_dump(mode="json") for row in raw_events]
    inserted = 0
    with SessionLocal() as db:
        for event in normalized:
            dedup = hashlib.sha256(f"{platform}:{tenant}:{event['external_id']}".encode()).hexdigest()
            if db.scalar(select(Record).where(Record.resource == "audit_logs", Record.dedup_key == dedup)):
                continue
            record = Record(resource="audit_logs", platform=platform, tenant=tenant, dedup_key=dedup,
                            data={**event, "platform": platform, "tenant": tenant,
                                  "name": event["action"], "owner": event["actor"]})
            try:
                with db.begin_nested():
                    db.add(record)
                    db.flush()
                    log_event(db, record, {}, actor, "ingest")
                inserted += 1
            except IntegrityError:
                continue
        db.commit()
    return inserted


def _event_rows(payload) -> list[dict]:
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict):
        rows = payload.get("data", payload.get("items", payload.get("events", [payload])))
    else:
        rows = []
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise VendorFeedError("Vendor feed returned an unsupported event shape")
    return rows


async def _request(client: httpx.AsyncClient, method: str, url: str, *, headers: dict,
                   params: dict | None = None, data: dict | None = None, json_body=None) -> httpx.Response:
    for attempt in range(4):
        try:
            response = await client.request(method, url, headers=headers, params=params, data=data, json=json_body)
        except httpx.HTTPError as exc:
            if attempt == 3:
                raise VendorFeedError("Vendor service is unreachable") from exc
            await asyncio.sleep(2 ** attempt)
            continue
        if response.status_code == 429 or response.status_code >= 500:
            if attempt == 3:
                raise VendorFeedError(f"Vendor service returned HTTP {response.status_code}")
            retry_after = response.headers.get("Retry-After", "")
            delay = int(retry_after) if retry_after.isdigit() else 2 ** attempt
            await asyncio.sleep(min(delay, 30))
            continue
        if not response.is_success:
            raise VendorFeedError(f"Vendor service returned HTTP {response.status_code}")
        return response
    raise VendorFeedError("Vendor request retry limit reached")


def _csv_values(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _configured_sources(settings: Settings) -> list[dict]:
    sources = [{"platform": "claude", "source": "activities", "tenant": settings.anthropic_compliance_tenant,
                "configured": bool(settings.anthropic_compliance_api_key and settings.anthropic_compliance_tenant)}]
    sources.extend({"platform": "chatgpt", "source": f"event_type:{event_type}",
                    "tenant": settings.openai_compliance_principal_id,
                    "configured": bool(settings.openai_compliance_api_key and settings.openai_compliance_principal_id)}
                   for event_type in _csv_values(settings.openai_compliance_event_types))
    sources.extend({"platform": "copilot", "source": f"content_type:{content_type}",
                    "tenant": settings.o365_tenant_id,
                    "configured": bool(settings.o365_tenant_id and settings.o365_client_id and settings.o365_client_secret
                                        and settings.o365_publisher_id)}
                   for content_type in _csv_values(settings.o365_content_types))
    return sources


def feed_source_status(db: Session, settings: Settings | None = None) -> list[dict]:
    settings = settings or get_settings()
    items = []
    for source in _configured_sources(settings):
        record = _checkpoint(db, source["platform"], source["tenant"], source["source"]) if source["tenant"] else None
        data = record.data if record else {}
        items.append({"platform": source["platform"], "source": source["source"],
                      "configured": source["configured"], "enabled": settings.vendor_feeds_enabled,
                      "status": data.get("status", "not_configured" if not source["configured"] else "waiting"),
                      "last_success_at": data.get("last_success_at"), "last_error": data.get("last_error", "")})
    return items


async def _sync_claude(client: httpx.AsyncClient, settings: Settings) -> None:
    platform, tenant, source = "claude", settings.anthropic_compliance_tenant, "activities"
    headers = {"x-api-key": settings.anthropic_compliance_api_key,
               "anthropic-version": "2023-06-01", "Accept": "application/json"}
    cursor = None
    after_id = None
    start = _utc_now() - timedelta(seconds=settings.vendor_sync_overlap_seconds)
    total = 0
    try:
        for _ in range(MAX_PAGES):
            params = {"limit": 5000, "order": "asc", "created_at[gte]": _iso(start)}
            if after_id:
                params["after_id"] = after_id
            payload = (await _request(client, "GET", "https://api.anthropic.com/v1/compliance/activities",
                                      headers=headers, params=params)).json()
            rows = _event_rows(payload)
            if rows:
                total += _store_events(platform, tenant, rows, claude_audit.normalize, "vendor-feed:claude")
                cursor = payload.get("last_id") if isinstance(payload, dict) else None
                after_id = cursor
            if not isinstance(payload, dict) or not payload.get("has_more"):
                break
            if not after_id:
                raise VendorFeedError("Anthropic feed indicated another page without a last_id cursor")
        else:
            raise VendorFeedError("Anthropic feed exceeded the page limit")
        _save_checkpoint(platform, tenant, source, cursor)
        logger.info("Vendor feed sync complete: platform=%s imported=%d", platform, total)
    except Exception as exc:
        _save_checkpoint(platform, tenant, source, None, type(exc).__name__)
        logger.warning("Vendor feed sync failed: platform=%s error=%s", platform, type(exc).__name__)


async def _sync_openai(client: httpx.AsyncClient, settings: Settings, event_type: str) -> None:
    platform, tenant, source = "chatgpt", settings.openai_compliance_principal_id, f"event_type:{event_type}"
    scope = "organizations" if tenant.startswith("org-") else "workspaces"
    base = f"https://api.chatgpt.com/v1/compliance/{scope}/{tenant}"
    headers = {"Authorization": f"Bearer {settings.openai_compliance_api_key}", "Accept": "application/json"}
    with SessionLocal() as db:
        state = _checkpoint(db, platform, tenant, source)
        previous_cursor = (state.data or {}).get("cursor") if state else None
    try:
        after = datetime.fromisoformat(previous_cursor.replace("Z", "+00:00")) - timedelta(seconds=settings.vendor_sync_overlap_seconds) if previous_cursor else _utc_now() - timedelta(hours=settings.vendor_initial_lookback_hours)
        after_value = _iso(after)
        latest = previous_cursor
        total = 0
        for _ in range(MAX_PAGES):
            response = await _request(client, "GET", f"{base}/logs", headers=headers,
                                      params={"limit": 100, "event_type": event_type, "after": after_value})
            payload = response.json()
            if not isinstance(payload, dict):
                raise VendorFeedError("OpenAI feed returned an unsupported page")
            for log in _event_rows(payload):
                log_id = _string(log.get("id"), "unknown-log")
                content = await _request(client, "GET", f"{base}/logs/{log_id}", headers=headers)
                if len(content.content) > MAX_CONTENT_BYTES:
                    raise VendorFeedError("OpenAI compliance log exceeds the 50 MB limit")
                rows = _parse_event_file(content.content, log_id)
                total += _store_events(platform, tenant, rows, chatgpt_compliance.normalize, "vendor-feed:chatgpt")
                if total > MAX_EVENTS_PER_SYNC:
                    raise VendorFeedError("OpenAI feed exceeded the event limit")
            latest = payload.get("last_end_time") or latest or _iso(_utc_now())
            if not payload.get("has_more"):
                break
            if not payload.get("last_end_time") or payload["last_end_time"] == after_value:
                raise VendorFeedError("OpenAI feed did not advance its paging cursor")
            after_value = payload["last_end_time"]
        else:
            raise VendorFeedError("OpenAI feed exceeded the page limit")
        _save_checkpoint(platform, tenant, source, latest)
        logger.info("Vendor feed sync complete: platform=%s imported=%d", platform, total)
    except Exception as exc:
        _save_checkpoint(platform, tenant, source, None, type(exc).__name__)
        logger.warning("Vendor feed sync failed: platform=%s source=%s error=%s", platform, event_type, type(exc).__name__)


def _trusted_o365_url(value: str) -> str:
    parsed = urlsplit(value)
    if parsed.scheme != "https" or parsed.hostname not in O365_HOSTS or parsed.port not in (None, 443):
        raise VendorFeedError("Microsoft feed returned an untrusted content URL")
    return value


async def _sync_o365(client: httpx.AsyncClient, settings: Settings, content_type: str, token: str) -> None:
    platform, tenant, source = "copilot", settings.o365_tenant_id, f"content_type:{content_type}"
    root = f"https://manage.office.com/api/v1.0/{tenant}/activity/feed"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    try:
        subscriptions = (await _request(client, "GET", f"{root}/subscriptions/list", headers=headers,
                                        params={"PublisherIdentifier": settings.o365_publisher_id})).json()
        active = next((item for item in subscriptions if item.get("contentType") == content_type and item.get("status") == "enabled"), None)
        if not active:
            await _request(client, "POST", f"{root}/subscriptions/start", headers=headers,
                           params={"contentType": content_type, "PublisherIdentifier": settings.o365_publisher_id})

        with SessionLocal() as db:
            state = _checkpoint(db, platform, tenant, source)
            previous_cursor = (state.data or {}).get("cursor") if state else None
        now = _utc_now()
        if previous_cursor:
            prior = datetime.fromisoformat(previous_cursor.replace("Z", "+00:00"))
            if now - prior > timedelta(days=7):
                raise VendorFeedError("Microsoft checkpoint is outside the seven-day content retention window")
            start = prior - timedelta(seconds=settings.vendor_sync_overlap_seconds)
        else:
            start = now - timedelta(hours=settings.vendor_initial_lookback_hours)
        total = 0
        next_url = f"{root}/subscriptions/content"
        params = {"contentType": content_type, "startTime": start.strftime("%Y-%m-%dT%H:%M:%S"),
                  "endTime": now.strftime("%Y-%m-%dT%H:%M:%S"), "PublisherIdentifier": settings.o365_publisher_id}
        for _ in range(MAX_PAGES):
            page = await _request(client, "GET", next_url, headers=headers, params=params)
            params = None
            for item in _event_rows(page.json()):
                content = await _request(client, "GET", _trusted_o365_url(item["contentUri"]), headers=headers)
                if len(content.content) > MAX_CONTENT_BYTES:
                    raise VendorFeedError("Microsoft content blob exceeds the 50 MB limit")
                rows = _event_rows(content.json())
                total += _store_events(platform, tenant, rows, purview_audit.normalize, "vendor-feed:copilot")
                if total > MAX_EVENTS_PER_SYNC:
                    raise VendorFeedError("Microsoft feed exceeded the event limit")
            next_url = page.headers.get("NextPageUri")
            if not next_url:
                break
            next_url = _trusted_o365_url(next_url)
        else:
            raise VendorFeedError("Microsoft feed exceeded the page limit")
        _save_checkpoint(platform, tenant, source, _iso(now))
        logger.info("Vendor feed sync complete: platform=%s imported=%d", platform, total)
    except Exception as exc:
        _save_checkpoint(platform, tenant, source, None, type(exc).__name__)
        logger.warning("Vendor feed sync failed: platform=%s source=%s error=%s", platform, content_type, type(exc).__name__)


async def sync_configured_vendors(settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    if not settings.vendor_feeds_enabled:
        return
    timeout = httpx.Timeout(30, connect=10)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
        if settings.anthropic_compliance_api_key and settings.anthropic_compliance_tenant:
            await _sync_claude(client, settings)
        for event_type in _csv_values(settings.openai_compliance_event_types):
            if settings.openai_compliance_api_key and settings.openai_compliance_principal_id:
                await _sync_openai(client, settings, event_type)
        if settings.o365_tenant_id and settings.o365_client_id and settings.o365_client_secret and settings.o365_publisher_id:
            try:
                token_response = await _request(
                    client, "POST",
                    f"https://login.microsoftonline.com/{settings.o365_tenant_id}/oauth2/v2.0/token",
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    data={"client_id": settings.o365_client_id, "client_secret": settings.o365_client_secret,
                          "grant_type": "client_credentials", "scope": "https://manage.office.com/.default"},
                )
                token = token_response.json().get("access_token")
                if not token:
                    raise VendorFeedError("Microsoft Entra token response omitted an access token")
                for content_type in _csv_values(settings.o365_content_types):
                    await _sync_o365(client, settings, content_type, token)
            except Exception as exc:
                for content_type in _csv_values(settings.o365_content_types):
                    _save_checkpoint("copilot", settings.o365_tenant_id, f"content_type:{content_type}", None, type(exc).__name__)
                logger.warning("Vendor feed authentication failed: platform=copilot error=%s", type(exc).__name__)


async def vendor_feed_loop() -> None:
    while True:
        try:
            await sync_configured_vendors()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("Vendor feed poll failed: error=%s", type(exc).__name__)
        await asyncio.sleep(get_settings().vendor_sync_interval_seconds)