# Audit Request Runbook

1. Authenticate with an authorized credential. Agree the platform, tenant, inclusive UTC date range, format, purpose, recipient, and handling classification.
2. Verify inventory sign-offs, allowlist approvals, current baseline, change outcomes, source approvals, retention position, and evidence expiry. Investigate open exceptions; do not imply they are resolved by exporting them.
3. Import the relevant synthetic or authorized audit files into Audit Explorer. Choose a single platform per upload. Review source event IDs, timestamp/timezone, actor, action, target, and result. No raw prompt/response bodies are stored by the adapter.
4. Select Audit package, platform, tenant, date range, and CSV or JSON. Export the ZIP. The API equivalent is `GET /api/evidence/export/package?platform=claude&tenant=demo&start=2026-01-01&end=2026-12-31&format=json`.
5. Inspect the manifest and verify each listed SHA-256 digest. Checksums detect accidental modification, not malicious replacement of both content and manifest; they are not a digital signature.
6. Confirm scope and time semantics, identify missing external documents, and obtain release approval. Store the released bundle in the approved evidence repository and record receipt in the external audit-request process.

## Bundle Contents

| File | Content |
| --- | --- |
| configuration | Baseline, sharing, and retention state known as of the end date |
| entitlements | Allowlist, sources, Skills, and snapshots known as of the end date |
| changes | Change request state known as of the end date |
| evidence | Evidence register references known as of the end date, not binary artifacts |
| governance_activity | Before/after history within the inclusive date range |
| audit_events | Normalized events within the date range, present in state known as of the end date |
| manifest.json | Scope, generated time/actor, semantics, file checksums |

An event imported after the selected end date is not part of that historical knowledge state, even if its source timestamp is earlier. Use an end date covering ingestion when packaging newly loaded historical samples, or explicitly describe the evidence cutoff to the auditor. Initial records created after the requested end date do not appear. No current-state fallback silently substitutes for missing historical evidence.

CSV cells beginning with spreadsheet formula prefixes are escaped. Nested data is JSON encoded inside CSV cells. All resources are tenant/platform scoped. No evidence attachments are fetched or embedded; the register stores references only. Never distribute bearer credentials with the bundle.

## Import Contract

Files must be UTF-8 CSV or JSON arrays (or `items`/`events` envelopes), at most 5 MB and 10,000 rows. Imports are validated before writes. Duplicate audit events use platform + tenant + vendor event ID and are skipped. Reusing an ID with changed content does not overwrite an event; investigate upstream identity issues.

Inventory rows: `external_id`, `name`, `kind`, optional `owner` and `version`. Audit normalized rows: `external_id`, `timestamp` with timezone, `actor`, `action`, `target`, optional `outcome`. The three vendor-shaped JSON samples exercise separate adapters. These are illustrative fixtures, not full or certified vendor API schemas. Production adapters require validation against real contracted exports, pagination, authentication, source completeness, and version changes.

The mixed-platform sample CSV is intended for the seed script. Split it by platform before manual imports; a mismatched row is rejected to prevent silent misattribution.