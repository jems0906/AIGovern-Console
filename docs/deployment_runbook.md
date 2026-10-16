# Deployment Operations

## Deployment Record

Deployed on 2026-10-15 with the owner's approval to create isolated Railway resources. Project: AIGovern-Console, ID `56e54173-8191-4701-91cc-052cb6d3aa8f`, production environment, us-west2.

Public application: https://frontend-production-033cb.up.railway.app

Dashboard: https://railway.com/project/56e54173-8191-4701-91cc-052cb6d3aa8f

Services: frontend (nginx, public HTTPS), backend (FastAPI, private), Postgres (managed, private connection used by the API). Both application services connect to `jems0906/AIGovern-Console` on `main`. Repository-root builds use separate Dockerfiles. Database schema changes run through Alembic before API startup.

The imported `.railway/railway.ts` is the current reproducible environment definition. Secrets are `preserve()` references, never inline values. Run `railway config plan` after installing the root tooling package to compare it with the live environment. Review changes before applying; never use destructive confirmation flags casually. Creating a fresh environment requires provisioning its secrets separately.

## Access

1. Open Railway backend > Variables as the project owner and retrieve `ADMIN_API_KEY` directly. Do not paste it into chat or commit it.
2. Open the application's key button, enter the credential, and connect. It remains in that browser tab's session storage.
3. Anonymous API reads return 401. Production has no local-demo authentication bypass. Viewer/reviewer role keys are optional and can be provisioned in Railway, but the current deployed admin key is a shared role credential, not an employee SSO identity.
4. Sign out on shared devices. Never place credentials in a URL, screenshots, test trace, support ticket, or public CI log.

## Verification

Local and GitHub CI cover API guard rules, PostgreSQL migration/seed checks, frontend tests/build, and local browser workflows. The opt-in live Playwright test verifies all seven governance areas using a fresh `deployment-validation-*` tenant: disabled-agent activation guards, review approvals, inventory shadow detection/sign-off, Skills history, sharing drift, source activation guards, rollout gates, baseline change/rollback, retention/evidence records, normalized audit ingestion, incident records, audit ZIP download, and responsive UI.

Live tests require `AIGOVERN_DEPLOYMENT_URL` and `AIGOVERN_DEPLOYMENT_TOKEN` through a local secret environment. Traces are disabled for deployment tests. Cloud test records are deliberately synthetic and retained as acceptance history. They are not real approvals and must not be mistaken for operational governance data.

After each release verify: `/api/health` returns `ok`, unauthenticated `/api/session` returns 401, authenticated session reports production with `demo=false`, an authorized register read succeeds, and the frontend renders on desktop/mobile. Validate evidence upload/download and a scoped package after storage changes.

nginx uses the container's DNS resolvers and refreshes backend DNS every 10 seconds. This avoids stale upstream addresses when API deployments rotate their private address. API connection timeout is bounded to 5 seconds rather than allowing a long silent hang.

## Credential Rotation

Generate a new random credential with at least 32 characters directly in an approved local secret manager. Set it in Railway backend Variables without displaying it in logs, then deploy/restart the backend. Sign out old browser sessions and reconnect using the new value. Verify the old credential returns 401. Store recovery access in the approved password vault; this repository does not store a recovery key.

## Recovery and Data Protection

- Roll back an application image using Railway deployment history. Review whether a database migration is backward compatible first; do not automatically downgrade or drop tables.
- Evidence files live in PostgreSQL, not an ephemeral container filesystem. A valid backup must include both record metadata and file bytes.
- Configure and verify the workspace's approved backup schedule, retention, and restore procedure. A restore drill has not been performed by this deployment task; do not claim a recovery objective until one succeeds.
- Configure budget alerts and inspect usage in Railway. No plan upgrades or unrelated project changes were authorized or performed.
- Production synthetic bulk seeding remains disabled. Operators may import approved files or create genuine records through authenticated workflows.
- Apply organization-specific retention and legal holds before onboarding real data. The console records positions; it does not automatically delete retained evidence.

## Remaining Organizational Acceptance

The deployment is a working governance demonstrator, not a compliance certification. Real approvals, contracts, tenant access verification, individual SSO/tenant authorization, malware scanning for externally supplied files, immutable external evidence retention, backup restore drills, alert routing, and human release approval require the organization's own controls and owners. These are not satisfied by synthetic acceptance records.