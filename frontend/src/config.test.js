import { describe, expect, it } from 'vitest'
import { normalizeCredential } from './api/client'
import { cleanRecord, defaults } from './config'
import { summarize } from './pages/Overview'

describe('governance form data', () => {
  it('accepts either a raw API key or a Bearer header value', () => {
    expect(normalizeCredential('  secret-key  ')).toBe('secret-key')
    expect(normalizeCredential('Bearer secret-key')).toBe('secret-key')
    expect(normalizeCredential('bearer secret-key')).toBe('secret-key')
  })
  it('starts every capability submitted without a risk review', () => {
    expect(defaults('allowlist')).toMatchObject({ status: 'submitted', risk_review: null, workspace_agent: false })
  })
  it('strips server fields and normalizes empty optional dates', () => {
    const clean = cleanRecord('skills', { ...defaults('skills'), id: 'server', revision: 3 })
    expect(clean).not.toHaveProperty('id')
    expect(clean.retirement_date).toBeNull()
  })
  it('does not let another tenant approval hide a shadow capability', () => {
    const data = { allowlist: [{ platform: 'claude', tenant: 'other', status: 'approved', kind: 'agent', external_id: 'agent' }], sharing: [], baseline: [], inventory: [{ platform: 'claude', tenant: 'demo', created_at: '2026-01-01', items: [{ kind: 'agent', external_id: 'agent' }] }] }
    expect(summarize(data).shadow).toHaveLength(1)
  })
})