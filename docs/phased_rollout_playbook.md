# Phased Rollout Playbook

Each platform/tenant has at most one record for each phase. Phases cannot activate until their predecessor is completed. Create the records as planned, then complete their checklists. Completed phase records are immutable.

## 1. Core

Entry criteria: `sso_scim_ready`, `acceptable_use_approved`, `retention_approved`.

Validate tenant authentication, provisioning, seat ownership, basic approved use cases, and user training. For Claude Code, account-level provisioning/seat setup must be verified in the relevant Claude administration surface, not inferred from this console.

## 2. Intelligence

Entry criteria: `core_use_cases_validated`, `training_complete`, `audit_verified`.

Evaluate knowledge quality, approved search use cases, access trimming, user outcomes, and usable audit records. Confirm that the tenant's contracted capabilities and licensing support the planned workflow.

## 3. Integrations

Entry criteria: `data_owners_approved`, `permissions_verified`, `connector_allowlist_reviewed`.

Approve each grounding source and connector. Verify source ACLs with actual tenant tests and retain results. No pending source may be enabled.

## 4. Automation and Agents

Entry criteria: `agent_risk_reviews_complete`, `write_actions_reviewed`, `rollback_tested`.

Review identities, shared connections, tool scope, publishing scope, external writes, monitoring, and rollback. Workspace Agents remain disabled until the documented risk and owner gates have passed.

## Every Phase

Before activation, all five governance reassessment checks must pass: `security`, `privacy`, `retention`, `sharing`, and `support_readiness`. Checklist values are operator attestations; they do not automatically evaluate tenant controls.

To complete a phase, record a retrospective with `use_cases`, `barriers`, and `next_changes`. Capture measurable outcomes, problems, remaining exceptions, owners, and changes required before the next phase. The next phase cannot activate with an incomplete predecessor.