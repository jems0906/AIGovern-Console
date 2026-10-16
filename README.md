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

Without `ADMIN_API_KEY`, development grants an explicitly labeled local-demo admin session. Bind it to localhost only. Production refuses to start without a 32-character admin credential. Set `ENVIRONMENT=production`, `DATABASE_URL`, and credential variables through your deployment secret manager, not committed files. Enter credentials through the console's key button. Browser credentials live in session storage and are removed on sign-out.

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
| Audit simulation | Claude, ChatGPT and Purview adapters; deduplication; normalized event search, filters and dates |
| Audit packages | Historical configuration, entitlements, changes, evidence, activity and normalized logs as CSV/JSON ZIP with checksum manifest |
| Acceptable use | Incident categories, severity, Information Security escalation references and resolution |
| Delivery | Migrations, Dockerfiles, Compose PostgreSQL, Railway configs, CI, unit/API/browser tests, synthetic data and six operating documents |

All registers support search, platform/tenant scope, sorting, pagination, detail/history, and appropriate create/edit or import actions. API validation remains authoritative. Stale updates return 409; invalid governance decisions return 422. There are intentionally no delete endpoints.

## Architecture

React calls `/api` through Vite locally and nginx in containers. FastAPI routes delegate to validated governance services. SQLAlchemy stores typed, schema-validated JSON records in a common indexed table plus append-only application history. Pydantic models are exposed in OpenAPI. Revisions enforce optimistic concurrency. Alembic owns the production schema; development/test creation uses metadata.

This shared record model keeps the many small governance registers consistent without duplicating CRUD implementations. Indexed resource, tenant, and platform columns provide scope; JSON payloads preserve platform-specific detail. Listing/search currently filters bounded governance datasets in application memory. Large enterprise feeds should add database-side JSON filtering, retention/partitioning, background ingestion, and streaming exports.

`backend/app/api/routes/` owns each requested module. `governance/` owns workflow, diff, drift, and rollout rules. `ingestion/` owns vendor normalization. `scripts/` contains seeding and a synthetic inventory generator. `docs/` contains the operating policy, change procedure, rollout playbook, acceptable-use standard, retention decision guide, and audit runbook.

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

- This is a governance system of record with simulated audit ingestion, not live tenant enforcement. No vendor credentials are requested and no connector is actually enabled by this application.
- Production role credentials are shared role identities, not per-person SSO. They authorize all tenants. Add OIDC/SAML-backed identities, tenant-level authorization, separation of duties, and signed approval evidence before regulated use.
- Evidence files are persisted in PostgreSQL, limited to 5 MB each and approved document/image extensions, delivered only as authenticated downloads, and included in scoped packages with SHA-256 checksums. Uploaded bytes are untrusted: files are not malware-scanned, legally validated, or rendered inline. Review presence checks cannot verify that a legal document, certification, ACL test, or approval is authentic. Add malware scanning before allowing untrusted external submitters.
- Incident escalation is recorded, not sent to an external service. Approved retention positions do not automatically configure vendors or delete console data.
- Application history has no edit/delete API but is not a WORM store. Export checksums are integrity aids, not signatures. Use approved external immutable storage and release controls.
- Audit adapters implement the supplied synthetic shapes, not complete vendor contracts. Validate real feeds and licensing against current documentation before connecting production data.
- Demo names, approvals, legal references, and positions are synthetic and do not establish compliance.

Read the [governance policy](docs/governance_operating_policy.md) and [audit runbook](docs/audit_request_runbook.md) before operating the console.