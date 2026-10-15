# Change Control Procedure

Status: operating template. Console changes update the governance register only, not vendor settings.

1. Create an initial baseline for a platform/tenant/setting with approved value, rationale, and accountable owner. Record observed value separately. Setting identity is immutable after creation.
2. Create a draft change that references the baseline. Record description, before/after values, risk, privileged status, approver, and timezone-aware scheduled start/end.
3. Include a rollback plan for every privileged, high, or critical change, even at draft stage. Include recovery steps, responsible operator, validation checks, and communications.
4. Obtain change-authority approval and move `draft -> approved`. Approved scope and scheduling are locked; revisions require a new draft request.
5. Within the approved window, implement the tenant change separately. Verify the tenant configuration and record the outcome. Move `approved -> implemented` to apply the after value to the governance baseline and observed value atomically. The before value must still match the current baseline.
6. On implementation failure, use `approved -> failed` with an outcome. The baseline remains unchanged.
7. When reverting a recorded implementation, perform tenant rollback separately and use `implemented -> rolled_back`. The register restores the before value only if the current baseline still matches this change's after value. Otherwise prepare a separate change; do not overwrite another implementation.
8. For a failed change, `failed -> rolled_back` records the recovery outcome without modifying a baseline that was never applied.
9. Retain the change record and before/after history for audit. The API has no delete endpoint.

Scheduled windows are inclusive UTC instants. Approval outside the window is allowed; implementation outside it is rejected. Rollback is allowed outside the original window for recovery. The API checks record revision to reject stale edits and uses SQLAlchemy optimistic concurrency for concurrent updates.

Observation updates do not change approved values. Direct patches to an existing baseline's approved value are blocked. Initial baseline approval is a procedural attestation, not a CAB integration. Approval records are not cryptographic signatures and the implementation does not enforce that requester and approver are different people.

Emergency changes still require a documented rollback plan and a valid window. Record a narrow emergency window and escalation reference in the description; do not bypass the API guards. Review the emergency decision retrospectively in the change authority meeting.