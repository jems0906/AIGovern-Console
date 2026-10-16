# AIGovern Console

An AI platform governance, change-control, and audit-evidence workspace for Claude, ChatGPT Enterprise, and Microsoft 365 Copilot.

Python/FastAPI, SQLAlchemy, Pydantic, PostgreSQL, React/Vite, Recharts, TanStack Table, pytest, Docker, Railway, and GitHub Actions. The repository root is the project root; no extra nested `aigovern-console` directory is required.

## Live Deployment

- Application: https://frontend-production-033cb.up.railway.app
- Railway project: https://railway.com/project/56e54173-8191-4701-91cc-052cb6d3aa8f
- Source and CI: https://github.com/jems0906/AIGovern-Console
- Environment: production, us-west2; public frontend with private API and managed PostgreSQL.

Open the key button in the console to connect. The owner can retrieve `ADMIN_API_KEY` directly from the backend service's Railway Variables page. Never paste that value into a chat, commit, issue, screenshot, or documentation. The public site does not grant anonymous data access. Production demo bypass is disabled. Cloud acceptance records use isolated `deployment-validation-*` tenants and synthetic data; they are not actual organizational approvals.

See [deployment operations](docs/deployment_runbook.md) for credential rotation, release verification, recovery, and remaining operational acceptance requirements.

## Local Development

Prerequisites: Python 3.13+, Node 22+, npm. Docker is needed only for PostgreSQL/container validation. Local development defaults to a persistent SQLite database under `backend/`; deployment uses PostgreSQL.

From the repository root in PowerShell:

```powershell
python -m venv .venv
& ./.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
& ./.venv/Scripts/python.exe scripts/seed_database.py
& ./.venv/Scripts/python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

In a second terminal:

```powershell
Set-Location frontend
npm ci
npm run dev -- --port 5173
```

Open **http://127.0.0.1:5173**. API documentation: **http://127.0.0.1:8000/docs**. Health: `/api/health`. The development seed is idempotent and never overwrites an existing demo tenant. Linux uses `.venv/bin/python` instead of `.venv/Scripts/python.exe`.

Without `ADMIN_API_KEY`, development grants an explicitly labeled local-demo admin session. Bind it to localhost only. Production defaults to API-key mode and requires a 32-character admin credential. Entra OIDC is available as an opt-in production mode after its app registration and roles are configured. Set environment variables through your deployment secret manager, not committed files.

### Microsoft Entra Sign-In

The API validates Microsoft Entra access-token signature, tenant-specific issuer, expiry, API audience, tenant ID, and assigned app role. It maps `AIGovern.Admin`, `AIGovern.Reviewer`, and `AIGovern.Viewer` to console permissions. The browser uses MSAL and requests an API access token; a client ID alone is not sufficient.

1. In Entra, configure a **single-tenant** app registration for the API. Expose a delegated API scope (for example `api://<API_CLIENT_ID>/AIGovern.Access`) and define app roles with values `AIGovern.Admin`, `AIGovern.Reviewer`, and `AIGovern.Viewer`, allowed for users/groups.
2. Add a **Single-page application** platform redirect URI exactly matching `https://frontend-production-033cb.up.railway.app`. Add `http://localhost:5173` for local development. Do not create a browser client secret.
3. Assign users/groups to the API app roles. Grant tenant consent for the delegated API scope. The same registration may serve as SPA and API; if separate registrations are used, set their IDs independently.
4. Set the following backend Railway variables only after testing the registered configuration: `AUTH_MODE=entra`, `ENTRA_TENANT_ID`, `ENTRA_SPA_CLIENT_ID`, `ENTRA_API_CLIENT_ID`, `ENTRA_API_AUDIENCE` (must exactly match the access token's `aud` claim), and `ENTRA_API_SCOPE` (the full exposed scope URI). Never set Entra mode with placeholder IDs. Restart/deploy the backend and frontend after variables and redirect URIs are configured.
5. Confirm the public `/api/auth/config` response contains only public IDs/scope (never credentials), the Microsoft login popup returns a token for this API, role claims produce the expected role, and unassigned users receive 403. Keep `ADMIN_API_KEY` available only as a controlled rollback until the sign-in change is accepted; then rotate/remove it according to your access policy.

The current deployment remains in API-key mode until the real tenant GUID and app registration IDs are configured. Do not send client secrets, tokens, or the Railway admin key in chat.

## Implemented Scope

| Requirement | Implementation |
| --- | --- |
| Allowlist and intake | Seven capability types, three platforms, guarded submitted/review/owner/approval/activation/retirement workflow; Workspace Agent disabled by default; explicit risk record |
| Inventory cadence | CSV/JSON imports, immutable snapshots, signed-review comparison, new/removed/shadow detection, reviewer and next-due tracking |
| Skills | Ownership, server-maintained version history, superseded flag, retirement dates |
| Sharing | Platform-specific policy register, target/observed values and drift |
| Grounding | Data owner, approval reference, permission verification and activation guard |
| Rollout | Four ordered phase gates, required entry and reassessment checks, completion retrospective |
| Baselines and changes | Approved/observed settings, rationale, ownership, scheduled change state machine, rollback requirements, transactional baseline application and rollback, before/after history |
| Compliance evidence | Retention decisions, certification/DPA/BAA references and attached files, checksum verification, obligations, expiry and vendor-control impact |
| Audit ingestion | Claude Activity Feed, OpenAI Compliance Logs, and Microsoft 365 Management Activity feed adapters; cursor/overlap polling, deduplication, normalized event search, filters, and source status |
| Audit packages | Historical configuration, entitlements, changes, evidence, activity and normalized logs as CSV/JSON ZIP with checksum manifest |
| Acceptable use | Incident categories, severity, Information Security escalation references and resolution |
| Delivery | Migrations, Dockerfiles, Compose PostgreSQL, Railway configs, CI, unit/API/browser tests, synthetic data and six operating documents |

All registers support search, platform/tenant scope, sorting, pagination, detail/history, and appropriate create/edit or import actions. API validation remains authoritative. Stale updates return 409; invalid governance decisions return 422. There are intentionally no delete endpoints.

## Architecture

React calls `/api` through Vite locally and nginx in containers. FastAPI routes delegate to validated governance services. SQLAlchemy stores typed, schema-validated JSON records in a common indexed table plus append-only application history. Pydantic models are exposed in OpenAPI. Revisions enforce optimistic concurrency. Alembic owns the production schema; development/test creation uses metadata.

This shared record model keeps the many small governance registers consistent without duplicating CRUD implementations. Indexed resource, tenant, and platform columns provide scope; JSON payloads preserve platform-specific detail. Listing/search currently filters bounded governance datasets in application memory. Large enterprise feeds should add database-side JSON filtering, retention/partitioning, background ingestion, and streaming exports.

`backend/app/api/routes/` owns each requested module. `governance/` owns workflow, diff, drift, and rollout rules. `ingestion/` owns vendor normalization. `scripts/` contains seeding and a synthetic inventory generator. `docs/` contains the operating policy, change procedure, rollout playbook, acceptable-use standard, retention decision guide, and audit runbook.

### Live Vendor Audit Feeds

Feed polling is disabled unless `VENDOR_FEEDS_ENABLED=true`. When enabled, the backend polls configured sources every five minutes by default, stores only normalized event fields, deduplicates by vendor event ID, and persists per-source cursors/checkpoints in PostgreSQL. `GET /api/audit_logs/sources` reports configuration and last-sync status without exposing credentials. Failed syncs leave the last successful checkpoint unchanged and show a sanitized error class. Review backend logs for operational details.

- Anthropic: set `ANTHROPIC_COMPLIANCE_API_KEY` with `read:compliance_activities` and a display label in `ANTHROPIC_COMPLIANCE_TENANT`. The poller queries the Activity Feed with a configurable overlap window.
- OpenAI: set `OPENAI_COMPLIANCE_API_KEY` to an eligible ChatGPT Enterprise/Edu Compliance API key, `OPENAI_COMPLIANCE_PRINCIPAL_ID` to the workspace or organization ID, and select comma-separated `OPENAI_COMPLIANCE_EVENT_TYPES`. The poller downloads listed logs; it does not use the retired stateful endpoint.
- Microsoft 365: register a confidential Entra application with admin-consented `ActivityFeed.Read` application permission and set `O365_TENANT_ID`, `O365_CLIENT_ID`, `O365_CLIENT_SECRET`, and `O365_PUBLISHER_ID`. Set `O365_CONTENT_TYPES` as needed. The app starts subscriptions before polling, which can take up to 12 hours to produce the first content. Microsoft content is retrievable for seven days; an older checkpoint is flagged instead of silently advanced.

Keep these credentials in Railway Variables or another secret manager. Do not paste them into this repository or chat. Configure each vendor's access and permission before enabling polling. No vendor feed or tenant access is active in the current production deployment.

## Tests

```powershell
Set-Location backend
& ../.venv/Scripts/python.exe -m pytest -q
Set-Location ../frontend
npm test
npm run build
npx playwright install chromium
npx playwright test
```

Seed the demo tenant before browser tests. Playwright starts servers if none are running and captures desktop/mobile screenshots under `frontend/test-results/`. It checks navigation across all registers, platform filtering, a disabled-by-default request, audit download, rendered charts, and horizontal overflow. Browser tests add a synthetic request to the demo tenant; use an isolated test database for repeated CI runs. PostgreSQL integration tests require `POSTGRES_TEST_URL`; CI provisions PostgreSQL, migrates, seeds, and runs that check.

The opt-in `deployment.spec.js` test targets a real deployment only when `AIGOVERN_DEPLOYMENT_URL` and `AIGOVERN_DEPLOYMENT_TOKEN` are explicitly supplied through your local environment or secret manager. Run `npx playwright test deployment.spec.js` from `frontend/`. It validates the seven governance areas and creates isolated synthetic acceptance records. It disables traces when a deployment URL is set so bearer credentials are not captured. Do not run the local-demo suite against production. Clear the two variables afterward.

Generate extra inventory fixtures with `python scripts/generate_synthetic_tenant.py --count 25 --output synthetic_inventory`. This creates data only; it does not grant approvals.

## Docker

Set `POSTGRES_PASSWORD` and `ADMIN_API_KEY` in your shell/secret manager. The database password must be URL encoded if it contains reserved connection-URL characters. Then from the repository root:

```powershell
docker compose up --build
```

Open http://localhost:8080 and connect with the admin credential. PostgreSQL persists in the named volume. Migrations run before API startup. Containers do not seed synthetic data. The backend is private to the Compose network. Do not use development bypass authentication on an exposed host.

## Railway Deployment

The project is deployed and both application services are connected to GitHub `main`. Repository-root build contexts use `backend/Dockerfile` and `frontend/Dockerfile` respectively. Health gates are `/api/health` and `/`. Migrations run at API startup; retain one replica until migrations are moved to a serialized deployment job.

The current project-level configuration is [.railway/railway.ts](.railway/railway.ts). It was imported from the deployed environment without secret values: `preserve()` retains secrets already stored on Railway. After linking the correct project, run `npm ci` at the repository root and `railway config plan` to inspect infrastructure drift. Apply changes only after reviewing the exact target and plan. Never use `--include-variables` when exporting configuration for this public repository. The root package contains infrastructure tooling only; application npm commands still run in `frontend/`.

On Windows, if the SDK reports an incorrect CLI-version error despite a current CLI, set the SDK's executable hint to the actual `railway.exe` rather than the PowerShell wrapper: `$env:_ = "$env:APPDATA/npm/node_modules/@railway/cli/bin/railway.exe"` for a user npm installation, then retry `railway config plan`.

The two original Railway JSON files remain as legacy examples requested in the project layout; they are not the source of truth for this new deployment. Railway's current docs deprecate Config as Code and state a 2026-12-01 cutoff. Use project configuration/Infrastructure as Code for new services instead of opting into those legacy files. See [Railway IaC](https://docs.railway.com/infrastructure-as-code) and [monorepo deployment](https://docs.railway.com/guides/monorepo).

Production variables: backend uses the private PostgreSQL reference, `ENVIRONMENT=production`, `PORT=8000`, and a generated admin credential. Frontend uses `PORT=8080` and a private backend DNS reference. nginx refreshes DNS at runtime, avoiding stale upstream addresses after API redeploys. No browser secret is embedded in the build. Only the frontend has a public domain. Optional reviewer/viewer keys can be added through Railway Variables.

Cloud resources incur workspace usage charges. Backups/restore drills, budget alerts, access restrictions, and legally approved evidence lifecycle remain operator responsibilities; a healthy deployment is not a compliance certification.

## Security and Deliberate Boundaries

- This is a governance system of record, not live tenant enforcement. Vendor audit polling is opt-in and has no credentials in the current deployment; it does not change vendor policies, connectors, or approvals.
- Production role credentials are shared role identities, not per-person SSO. They authorize all tenants. Add OIDC/SAML-backed identities, tenant-level authorization, separation of duties, and signed approval evidence before regulated use.
- Evidence files are persisted in PostgreSQL, limited to 5 MB each and approved document/image extensions, delivered only as authenticated downloads, and included in scoped packages with SHA-256 checksums. Uploaded bytes are untrusted: files are not malware-scanned, legally validated, or rendered inline. Review presence checks cannot verify that a legal document, certification, ACL test, or approval is authentic. Add malware scanning before allowing untrusted external submitters.
- Incident escalation is recorded, not sent to an external service. Approved retention positions do not automatically configure vendors or delete console data.
- Application history has no edit/delete API but is not a WORM store. Export checksums are integrity aids, not signatures. Use approved external immutable storage and release controls.
- Feed adapters support the documented Anthropic Activity Feed, OpenAI Compliance Logs, and Microsoft 365 Management Activity API shapes. Validate vendor licensing, tenant consent, access scope, and data handling before enabling production ingestion.
- Demo names, approvals, legal references, and positions are synthetic and do not establish compliance.

Read the [governance policy](docs/governance_operating_policy.md) and [audit runbook](docs/audit_request_runbook.md) before operating the console.