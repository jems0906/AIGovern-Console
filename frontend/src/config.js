export const platforms = { claude: 'Claude', chatgpt: 'ChatGPT Enterprise', copilot: 'Microsoft 365 Copilot', entra: 'Microsoft Entra ID' }
export const kinds = ['connector', 'app', 'plugin', 'extension', 'agent', 'custom_gpt', 'skill']
export const phases = ['core', 'intelligence', 'integrations', 'automation_agents']
export const entryCriteria = {
  core: ['sso_scim_ready', 'acceptable_use_approved', 'retention_approved'],
  intelligence: ['core_use_cases_validated', 'training_complete', 'audit_verified'],
  integrations: ['data_owners_approved', 'permissions_verified', 'connector_allowlist_reviewed'],
  automation_agents: ['agent_risk_reviews_complete', 'write_actions_reviewed', 'rollback_tested'],
}
export const reassessment = ['security', 'privacy', 'retention', 'sharing', 'support_readiness']
export const label = (value) => String(value ?? '').replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase())
const field = (key, type = 'text', options) => ({ key, type, options })
export const resources = {
  allowlist: { title: 'Allowlist & Requests', singular: 'Request', section: 'CAPABILITIES', fields: [field('kind', 'select', kinds), field('external_id'), field('workspace_agent', 'checkbox'), field('justification', 'textarea'), field('status', 'select', ['submitted', 'security_review', 'data_owner_approval', 'approved', 'denied', 'enabled', 'retired']), field('risk_review', 'risk'), field('data_owner_approval')], columns: ['name', 'kind', 'platform', 'owner', 'status', 'activation_status'] },
  inventory: { title: 'Inventory Reviews', singular: 'Snapshot', section: 'CAPABILITIES', import: true, fields: [field('reviewer'), field('reviewed_at', 'date'), field('next_review_due', 'date')], columns: ['name', 'platform', 'owner', 'reviewer', 'next_review_due', 'overdue'] },
  skills: { title: 'Skills Catalog', singular: 'Skill', section: 'CAPABILITIES', fields: [field('version'), field('description', 'textarea'), field('superseded', 'checkbox'), field('retirement_date', 'date'), field('status', 'select', ['active', 'retired'])], columns: ['name', 'platform', 'owner', 'version', 'superseded', 'retirement_date', 'status'] },
  sharing: { title: 'Sharing & Visibility', singular: 'Sharing Policy', section: 'CONTROLS', fields: [field('setting'), field('approved_value'), field('observed_value'), field('rationale', 'textarea')], columns: ['name', 'platform', 'approved_value', 'observed_value', 'drift', 'owner'] },
  datasources: { title: 'Data Sources', singular: 'Data Source', section: 'CONTROLS', fields: [field('scope', 'textarea'), field('approval_reference'), field('permission_verified_at', 'date'), field('status', 'select', ['pending', 'approved', 'enabled', 'retired'])], columns: ['name', 'platform', 'owner', 'approval_reference', 'permission_verified_at', 'status'] },
  rollout: { title: 'Rollout Gates', singular: 'Rollout Phase', section: 'CONTROLS', fields: [field('phase', 'select', phases), field('entry_criteria', 'criteria'), field('reassessment', 'reassessment'), field('retrospective', 'retrospective'), field('status', 'select', ['planned', 'active', 'completed'])], columns: ['name', 'platform', 'phase', 'owner', 'status'] },
  baseline: { title: 'Configuration Baselines', singular: 'Baseline', section: 'CONTROLS', fields: [field('setting'), field('approved_value'), field('observed_value'), field('rationale', 'textarea')], columns: ['name', 'platform', 'setting', 'approved_value', 'observed_value', 'drift'] },
  changes: { title: 'Change Control', singular: 'Change Request', section: 'CONTROLS', fields: [field('description', 'textarea'), field('baseline_id', 'baseline'), field('before_value'), field('after_value'), field('risk_level', 'select', ['low', 'medium', 'high', 'critical']), field('privileged', 'checkbox'), field('approver'), field('scheduled_start', 'datetime-local'), field('scheduled_end', 'datetime-local'), field('rollback_plan', 'textarea'), field('outcome', 'textarea'), field('status', 'select', ['draft', 'approved', 'implemented', 'failed', 'rolled_back'])], columns: ['name', 'platform', 'risk_level', 'approver', 'scheduled_start', 'status'] },
  evidence: { title: 'Evidence Library', singular: 'Evidence', section: 'ASSURANCE', fields: [field('artifact_type', 'select', ['certification', 'dpa', 'baa', 'vendor_control_change', 'other']), field('reference'), field('expires_at', 'date'), field('obligations', 'textarea'), field('control_change', 'textarea'), field('posture_impact', 'textarea'), field('status', 'select', ['pending', 'approved', 'expired', 'superseded'])], columns: ['name', 'platform', 'artifact_type', 'owner', 'expires_at', 'status'] },
  retention: { title: 'Retention Positions', singular: 'Retention Position', section: 'ASSURANCE', fields: [field('position', 'textarea'), field('approved_by'), field('approved_at', 'date'), field('review_due', 'date'), field('reference'), field('status', 'select', ['approved', 'superseded'])], columns: ['name', 'platform', 'approved_by', 'approved_at', 'review_due', 'status'] },
  audit_logs: { title: 'Audit Explorer', singular: 'Audit Event', section: 'ASSURANCE', import: true, readonly: true, columns: ['timestamp', 'platform', 'actor', 'action', 'target', 'outcome'] },
  aup_incidents: { title: 'Acceptable Use Incidents', singular: 'Incident', section: 'ASSURANCE', fields: [field('category', 'select', ['confidential', 'claimant', 'employee', 'production', 'other']), field('severity', 'select', ['low', 'medium', 'high', 'critical']), field('description', 'textarea'), field('occurred_at', 'datetime-local'), field('escalated_to'), field('escalation_reference'), field('resolution', 'textarea'), field('status', 'select', ['open', 'escalated', 'resolved'])], columns: ['name', 'platform', 'category', 'severity', 'escalated_to', 'status'] },
}

export function defaults(resource, platform = 'claude', tenant = 'demo') {
  const values = { name: '', platform: platform === 'all' ? 'claude' : platform, tenant, owner: '' }
  for (const item of resources[resource].fields || []) {
    values[item.key] = item.type === 'checkbox' ? false : item.options?.[0] ?? (['risk', 'criteria', 'reassessment', 'retrospective'].includes(item.type) ? {} : '')
  }
  if (resource === 'allowlist') values.risk_review = null
  return values
}

export function cleanRecord(resource, values) {
  const keys = ['name', 'platform', 'tenant', 'owner', ...(resources[resource].fields || []).map((item) => item.key)]
  if (resource === 'inventory') keys.push('items', 'captured_at')
  return Object.fromEntries(keys.map((key) => {
    let value = values[key]
    const type = resources[resource].fields?.find((item) => item.key === key)?.type
    if (type === 'date' && !value) value = null
    if (type === 'datetime-local' && value) value = new Date(value).toISOString()
    if (key === 'risk_review' && !value?.reviewer) value = null
    return [key, value]
  }))
}