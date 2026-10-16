# Retention Positions

No bundled retention value is a statement of vendor defaults, contractual commitment, certification, or legal advice. Seeded records are explicitly synthetic. Obtain current tenant-specific contractual and legal approval before production.

## Required Decision Record

For Claude, ChatGPT Enterprise, and Microsoft 365 Copilot separately, record the position, approving authority, approval date, review due date, document reference, tenant, and owner. Keep conversation retention, platform audit retention, source content retention, console evidence retention, and legal holds distinct in the approval document. A review date must follow the approval date.

| Platform | Questions to Resolve With Current Official Documentation and Contract |
| --- | --- |
| Claude | Tenant conversation retention controls, Compliance API availability/access, audit event coverage, account-level provisioning, deletion behavior and exceptions |
| ChatGPT Enterprise | Workspace settings, compliance data access, contract-specific retention, API/feed coverage, export access and permissions |
| Microsoft 365 Copilot | Purview audit licensing/retention, AI interaction coverage, applicable Microsoft 365 retention policies, legal hold and data security controls |

## Decision Workflow

1. Inventory relevant data categories and jurisdictions. Consult Privacy, Legal, Security, and records management.
2. Review current official administrator documentation and executed contract/DPA/BAA. Record references, not assumptions from sample data.
3. Test the available tenant controls and audit access with an authorized administrator.
4. Approve a written position with explicit exceptions and review date.
5. Record the approved position in the console and retain supporting evidence references.
6. Reassess when vendor controls, contract, licensing, data use, or legal requirements change. Supersede the old position rather than erasing it.

The console records approved positions; it does not configure tenant retention or automatically purge records. Configure database backups, evidence lifecycle, deletion/hold procedures, and immutable external storage according to the approved policy before production. Do not ingest sensitive prompt/response payloads merely to demonstrate compliance.

Official starting points:
- [Claude Enterprise Administrator Guide](https://claude.com/resources/tutorials/claude-enterprise-administrator-guide)
- [Claude Code organization setup](https://code.claude.com/docs/en/admin-setup)
- [OpenAI Enterprise help](https://help.openai.com/en/collections/5688074-chatgpt-enterprise)
- [OpenAI Compliance Platform](https://help.openai.com/en/articles/9261474-compliance-api-for-enterprise-customers)
- [Microsoft Purview Copilot audit](https://learn.microsoft.com/en-us/purview/audit-copilot)
- [Microsoft Purview for Copilot](https://learn.microsoft.com/en-us/purview/ai-microsoft-purview)

Availability, URLs, controls, and licensing can change. Verify current vendor documentation at decision time; these links are discovery aids, not evidence of a tenant's posture.

## Documentation Review: 2026-10-15

These findings were checked against official public documentation. They are product-documentation findings, not tenant-specific legal approvals or proof of effective controls.

| Official Source | Verified Finding | Console Implication |
| --- | --- | --- |
| [Claude audit logs](https://support.claude.com/en/articles/9970975-access-audit-logs) | Enterprise Owner/Primary Owner audit export covers the preceding 180 days; audit exports omit chat/project titles and contents. Documented columns include created_at, actor_info, event, event_info, and entity_info. | Retain source export references and avoid assuming the simplified synthetic fixture is the full vendor schema. |
| [Claude Compliance API](https://support.claude.com/en/articles/13015708-access-the-compliance-api) | Primary Owner enables Enterprise Compliance API access; scoped key authority and coverage depend on organizational roles and deployment surface. | Verify tenant role, access scope, coverage, and contract before any live integration. |
| [Claude custom retention](https://support.claude.com/en/articles/10440198-configure-custom-data-retention-controls-for-enterprise-plans) | Custom chat/project retention is an Enterprise owner control with a documented minimum; project and standalone-chat retention are distinct, and the article excludes some other product surfaces. | Separate conversation, project, audit, and console-evidence positions; do not assume one setting governs every Claude deployment. |
| [Claude Code organization setup](https://code.claude.com/docs/en/admin-setup) | SSO, SCIM, and seat assignment are configured at Claude account level; managed Claude Code policy is a separate control surface. | Core rollout checklist is an attestation that these external controls were verified, not an automatic provisioning action. |
| [OpenAI Compliance Platform](https://help.openai.com/en/articles/9261474-compliance-api-for-enterprise-customers) | Enterprise/Edu compliance access uses scoped Admin keys; immutable log access differs from stateful lookup. The current page documents 30-day Compliance Logs retention and a conversation-route migration/removal notice. | Plan continuous export for longer approved retention; validate current endpoints and do not infer conversation retention from log retention. |
| [OpenAI plugin/app administration](https://help.openai.com/en/articles/11509118-admin-controls-security-and-compliance-for-plugins-and-apps) | App availability, plugin installation, role access, provider scopes, action permissions, and future-action defaults are separate controls. Workspace Agent actions have per-agent settings. | Record item kind, publishing identity, scope, writes, owner approval, and vendor-change review independently. |
| [Microsoft Copilot audit](https://learn.microsoft.com/en-us/purview/audit-copilot) | Copilot interaction and admin activities are available through Purview Audit; Microsoft app coverage and non-Microsoft AI pay-as-you-go scenarios differ. | Normalize operation, actor, time, and target without assuming every AI workload has the same licensing, billing, or retention. |
| [Microsoft Purview protections](https://learn.microsoft.com/en-us/purview/ai-microsoft-purview) | Audit, sensitivity labels, source permissions, DLP, eDiscovery, and retention controls are complementary rather than interchangeable. | Keep source permission verification and approved retention decisions separate from audit-log presence. |

Real vendor feeds, contractual evidence, executed DPAs/BAAs, organization approvals, and source permission tests still require authorized tenant owners. No console sample or deployment acceptance test supplies those approvals.