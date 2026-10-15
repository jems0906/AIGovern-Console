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
- [Claude Enterprise help](https://support.claude.com/en/collections/9774931-enterprise-plan)
- [Claude Code organization setup](https://code.claude.com/docs/en/overview)
- [OpenAI Enterprise help](https://help.openai.com/en/collections/5688074-chatgpt-enterprise)
- [OpenAI Compliance Platform](https://help.openai.com/en/articles/9261474-compliance-api-for-enterprise-customers)
- [Microsoft Purview Copilot audit](https://learn.microsoft.com/en-us/purview/audit-copilot)
- [Microsoft Purview for Copilot](https://learn.microsoft.com/en-us/purview/ai-microsoft-purview)

Availability, URLs, controls, and licensing can change. Verify current vendor documentation at decision time; these links are discovery aids, not evidence of a tenant's posture.