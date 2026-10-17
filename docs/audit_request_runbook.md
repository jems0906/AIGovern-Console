# Audit Request Runbook

1. Authenticate with an authorized credential. Agree the platform, tenant, inclusive UTC date range, format, purpose, recipient, and handling classification.
2. Verify inventory sign-offs, allowlist approvals, current baseline, change outcomes, source approvals, retention position, and evidence expiry. Investigate open exceptions; do not imply they are resolved by exporting them.
3. In Audit Explorer, review the normalized feed records or import authorized audit files. Manual uploads must contain one platform per file. Live polling is disabled by default; when an administrator enables it with vendor credentials, check `GET /api/audit_logs/sources` for per-source configuration and last-sync status. Review source event IDs, timestamp/timezone, actor, action, target, and result. The adapters store normalized fields only, not raw prompt/response bodies.
4. Select Audit package, platform, tenant, date range, and CSV or JSON. Export the ZIP. The API equivalent is `GET /api/evidence/export/package?platform=claude&tenant=demo&start=2026-01-01&end=2026-12-31&format=json`.
5. Inspect the manifest and verify each listed SHA-256 digest. Checksums detect accidental modification, not malicious replacement of both content and manifest; they are not a digital signature.
6. Confirm scope and time semantics, identify missing external documents, and obtain release approval. Store the released bundle in the approved evidence repository and record receipt in the external audit-request process.

## Bundle Contents

| File | Content |
| --- | --- |
| configuration | Baseline, sharing, and retention state known as of the end date |
| entitlements | Allowlist, sources, Skills, and snapshots known as of the end date |
| changes | Change request state known as of the end date |
| evidence | Evidence register state known as of the end date |
| evidence_files | Attachment metadata, upload actor, file size, timestamp, and SHA-256 |
| artifacts/ | Attached files uploaded by the end date, scoped to the platform and tenant |
| governance_activity | Before/after history within the inclusive date range |
| audit_events | Normalized events within the date range, present in state known as of the end date |
| manifest.json | Scope, generated time/actor, semantics, file checksums |

An event imported after the selected end date is not part of that historical knowledge state, even if its source timestamp is earlier. Use an end date covering ingestion when packaging newly loaded historical samples, or explicitly describe the evidence cutoff to the auditor. Initial records created after the requested end date do not appear. No current-state fallback silently substitutes for missing historical evidence.

CSV cells beginning with spreadsheet formula prefixes are escaped. Nested data is JSON encoded inside CSV cells. All resources and attachments are tenant/platform scoped. Attached files are packaged under sanitized, unique names and included in the manifest's checksums. Downloads and export verify stored digests and reject integrity mismatches. External document-reference URLs are not fetched automatically. Never distribute bearer credentials with the bundle.

Evidence detail views support file upload and download. Allowed extensions are PDF, TXT, JSON, CSV, PNG, JPG, and JPEG, with a 5 MB per-file limit. Empty files are rejected. Files are stored in PostgreSQL rather than ephemeral container storage; uploads append immutable attachment metadata and audit history. Duplicate bytes within one evidence record are rejected. Do not upload secrets or unnecessary personal data. Attached files are not malware-scanned or legally authenticated; handle them as untrusted documents and follow the organization's review procedure.

## Import Contract

Manual files must be UTF-8 CSV or JSON arrays (or `items`/`events` envelopes), at most 5 MB and 10,000 rows. Imports are validated before writes. Duplicate audit events use platform + tenant + vendor event ID and are skipped. Reusing an ID with changed content does not overwrite an event; investigate upstream identity issues. Live polling has separate per-source checkpoints, overlap windows, pagination, retry handling, and a 50 MB per-download limit; Microsoft 365 content is only retrievable within seven days. Investigate a source status of `error` before relying on completeness.

Inventory rows: `external_id`, `name`, `kind`, optional `owner` and `version`. Audit normalized rows: `external_id`, `timestamp` with timezone, `actor`, `action`, `target`, optional `outcome`. The vendor-shaped JSON samples exercise the manual upload normalizers. Live feed integration supports Anthropic's Compliance Activity Feed, OpenAI's Compliance Logs API, Microsoft's Office 365 Management Activity API, and Microsoft Entra directory audits. Confirm vendor eligibility, contractual access, tenant consent, configured scopes, and source completeness before enabling production polling.

## Entra Directory Audit Feed

The Entra source reads `GET /v1.0/auditLogs/directoryAudits` through Microsoft Graph. Microsoft Entra Free retains up to seven days of audit logs; this source does not include the Microsoft 365 Unified Audit Log for Exchange, SharePoint, or Copilot activity. The backend API app needs the Microsoft Graph **Application** permission `AuditLog.Read.All` with administrator consent.

Keep `ENTRA_AUDIT_ENABLED` false while provisioning. Use the existing `ENTRA_TENANT_ID` and `ENTRA_API_CLIENT_ID`, create a server-side credential for that API app, and store its value as `ENTRA_AUDIT_CLIENT_SECRET` directly in Railway. Never add the credential to the SPA, repository, or chat. Do not set `VENDOR_FEEDS_ENABLED` for this source; Anthropic, OpenAI, and Office 365 polling use that separate switch.

After granting consent and configuring the Railway secret, run one limited sync from the backend container while recurring polling remains disabled:

```sh
python -c "import asyncio; from app.ingestion.vendor_feeds import sync_entra_audits; print('Imported:', asyncio.run(sync_entra_audits()))"
```

Verify the imported rows with `GET /api/audit_logs?platform=entra` and confirm `GET /api/audit_logs/sources` reports the Entra checkpoint as successful and disabled. Only after verification, set `ENTRA_AUDIT_ENABLED=true` to start recurring polling. The poll interval uses `VENDOR_SYNC_INTERVAL_SECONDS` (default 300 seconds).

The mixed-platform sample CSV is intended for the seed script. Split it by platform before manual imports; a mismatched row is rejected to prevent silent misattribution.