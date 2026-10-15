# Governance Operating Policy

Status: implementation template, not an organizational approval. All bundled tenant data is synthetic.

## Accountability

The platform owner maintains the register and baseline. Information Security performs capability risk review. The data owner authorizes grounding access. Legal/Privacy approves retention and contractual positions. The change authority authorizes scheduled changes. An auditor receives read-only access or a scoped package.

Production uses server-side admin, reviewer, and viewer bearer credentials. Admin/reviewer credentials can write; viewers cannot. Credentials identify a role, not a named employee. Named reviewers in records are attestations, not verified SSO identities. Add enterprise identity federation, individual authorization, and separation-of-duties enforcement before regulated production use. All credentials currently have cross-tenant access; a tenant filter is not an authorization boundary.

## Capability Request Procedure

1. Record a connector, app, plugin, extension, agent, custom GPT, or Skill request for the correct platform and tenant. Use the vendor's stable identifier and business owner.
2. Enter justification. Every new request starts `submitted`, with activation `disabled`.
3. Move to `security_review`. Record scope, personal vs. shared connection identity, external write actions, reviewer, review date, and risk notes.
4. Move to `data_owner_approval` only after the risk record is complete. Store the approval document reference.
5. Approve or deny. An approved request can be enabled in the governance register; a denied request cannot. Workspace Agents have the same explicit risk gate and never default enabled.
6. Perform the actual enablement separately in the vendor admin system under approved change control. This application does not call tenant administration APIs.
7. Retire a capability when access is removed. Final approval evidence and capability identity cannot be rewritten; material scope changes need a new request.

## Inventory and Skills

Import a CSV or JSON snapshot per tenant/platform monthly, or sooner after a vendor capability release. The diff compares to the most recent earlier signed snapshot, not merely the previous upload. It shows new and removed items; every observed item without a matching approved/enabled request is flagged as shadow, including previously observed unapproved items. Matching uses platform, tenant, kind, and external ID.

Snapshot contents are immutable. Sign off with reviewer, actual review date, and next due date. Unsigned snapshots stay in the review queue. The latest snapshot per tenant/platform controls the dashboard cadence signal. A signed snapshot can retain exceptions; sign-off is acknowledgement, not approval of those capabilities. Approval must use the request workflow.

Skills record owner, current version, server-maintained version history, superseded status, and retirement date. A version identifier cannot be reused; superseded or retired Skills require a retirement date. A catalog entry does not grant allowlist approval.

## Sharing and Sources

For each platform, record target visibility and observed values. Any exact mismatch is drift. Observation is an operator attestation or import, not a live tenant poll. Investigate Claude project visibility, ChatGPT workspace publishing/sharing, and Copilot agent group/organization scope.

Sources require a data owner, scope, approval reference, and non-future permission verification date before approval or enablement. Verification must include access trimming and representative authorized/unauthorized users. The application validates evidence presence, not the actual document or ACL contents. Reverify after permission or source scope changes.

## Review Cadence

| Control | Template cadence | Evidence |
| --- | --- | --- |
| Inventory and shadow capabilities | Monthly and after vendor releases | Snapshot, diff, sign-off |
| Skills versions and retirement | Monthly | Version history and owner decision |
| Sharing and baseline drift | Weekly and after changes | Observed values, change request |
| Grounding access | Quarterly and on scope changes | Owner reference and verification date |
| Vendor controls and contracts | Quarterly and on notices | Evidence artifact and posture impact |
| Retention | Annually and on legal/vendor changes | Approved position and next review |

API before/after history is append-only through the application; database administrators can still alter storage. Use externally retained exports or a managed immutable evidence store where stronger assurance is required.