# AIGovern Console

An AI platform governance, change-control, and audit-evidence workspace for Claude, ChatGPT Enterprise, and Microsoft 365 Copilot.

Python/FastAPI, SQLAlchemy, Pydantic, PostgreSQL, React/Vite, Recharts, TanStack Table, pytest, Docker, Railway, and GitHub Actions. The repository root is the project root; no extra nested `aigovern-console` directory is required.

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
| Compliance evidence | Retention decisions, certification/DPA/BAA references, obligations, expiry and vendor-control impact |
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

Generate extra inventory fixtures with `python scripts/generate_synthetic_tenant.py --count 25 --output synthetic_inventory`. This creates data only; it does not grant approvals.

## Docker

Set `POSTGRES_PASSWORD` and `ADMIN_API_KEY` in your shell/secret manager. The database password must be URL encoded if it contains reserved connection-URL characters. Then from the repository root:

```powershell
docker compose up --build
```

Open http://localhost:8080 and connect with the admin credential. PostgreSQL persists in the named volume. Migrations run before API startup. Containers do not seed synthetic data. The backend is private to the Compose network. Do not use development bypass authentication on an exposed host.

## Railway Deployment

1. Push the repository to your GitHub account. Create a Railway project with a managed PostgreSQL service.
2. Add a backend service from this repository with root `/`, config `/railway.json`, and Dockerfile `backend/Dockerfile`. Set `DATABASE_URL=${{Postgres.DATABASE_URL}}`, `ENVIRONMENT=production`, `PORT=8000`, and a strong `ADMIN_API_KEY`. Optional `REVIEWER_API_KEY` and `VIEWER_API_KEY` enable distinct role credentials. Do not expose the API publicly unless required; frontend proxying uses private networking.
3. Add a frontend service from the same repository, root `/`, config `/frontend/railway.json`, Dockerfile `frontend/Dockerfile`. Set `PORT=8080` and `BACKEND_UPSTREAM=${{backend.RAILWAY_PRIVATE_DOMAIN}}:8000` using your actual service names. nginx proxies same-origin `/api` traffic; no browser secret or API URL is baked into the build.
4. Enable a public HTTPS domain only for the frontend. Health checks use `/api/health` for backend and `/` for frontend. Migrations run on backend startup; use one deployment replica for this template or move migrations to a serialized pre-deploy job before scaling.
5. Configure backup/restore, credential rotation, access restrictions, monitoring, and the approved evidence-retention policy. Verify a restore and a scoped export before production acceptance.
6. Enable the GitHub Actions workflow and inspect backend, frontend, and browser jobs. CI service passwords are isolated disposable test values, not production credentials.

See [Railway monorepo guide](https://docs.railway.com/guides/monorepo) and verify current deployment UI settings. Deploying to your Railway/GitHub accounts requires your authorization and account access; no remote resources are created by this repository.

## Security and Deliberate Boundaries

- This is a governance system of record with simulated audit ingestion, not live tenant enforcement. No vendor credentials are requested and no connector is actually enabled by this application.
- Production role credentials are shared role identities, not per-person SSO. They authorize all tenants. Add OIDC/SAML-backed identities, tenant-level authorization, separation of duties, and signed approval evidence before regulated use.
- Evidence references are not downloaded artifacts. Review presence checks cannot verify that a legal document, certification, ACL test, or approval is authentic.
- Incident escalation is recorded, not sent to an external service. Approved retention positions do not automatically configure vendors or delete console data.
- Application history has no edit/delete API but is not a WORM store. Export checksums are integrity aids, not signatures. Use approved external immutable storage and release controls.
- Audit adapters implement the supplied synthetic shapes, not complete vendor contracts. Validate real feeds and licensing against current documentation before connecting production data.
- Demo names, approvals, legal references, and positions are synthetic and do not establish compliance.

Read the [governance policy](docs/governance_operating_policy.md) and [audit runbook](docs/audit_request_runbook.md) before operating the console.