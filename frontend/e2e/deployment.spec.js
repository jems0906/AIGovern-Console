import { test, expect } from '@playwright/test'
import { entryCriteria, phases, reassessment } from '../src/config'

test('deployed production governance workflows and responsive UI', async ({ page, request }) => {
  test.skip(!process.env.AIGOVERN_DEPLOYMENT_URL || !process.env.AIGOVERN_DEPLOYMENT_TOKEN, 'Requires an explicit deployment URL and credential')
  test.setTimeout(120000)
  const token = process.env.AIGOVERN_DEPLOYMENT_TOKEN
  const headers = { Authorization: `Bearer ${token}` }
  const tenant = `deployment-validation-${Date.now()}`
  const today = new Date().toISOString().slice(0, 10)
  const future = new Date(Date.now() + 30 * 86400000).toISOString().slice(0, 10)
  const common = { platform: 'claude', tenant, name: 'Synthetic cloud acceptance', owner: 'Synthetic Deployment Reviewer' }
  const errors = []
  page.on('pageerror', (error) => errors.push(error.message))
  async function create(resource, fields) {
    const response = await request.post(`/api/${resource}`, { headers, data: { ...common, ...fields } })
    expect(response.status()).toBe(201)
    return response.json()
  }
  async function patch(resource, record, fields, status = 200) {
    const response = await request.patch(`/api/${resource}/${record.id}`, { headers, data: { revision: record.revision, ...fields } })
    expect(response.status()).toBe(status)
    return response.json()
  }
  expect((await request.get('/api/health')).status()).toBe(200)
  expect((await request.get('/api/session')).status()).toBe(401)
  expect((await request.get('/api/allowlist')).status()).toBe(401)
  const session = await (await request.get('/api/session', { headers })).json()
  expect(session).toMatchObject({ role: 'admin', environment: 'production', demo: false })

  let capability = await create('allowlist', { kind: 'agent', external_id: `cloud-agent-${tenant}`, workspace_agent: true, justification: 'Synthetic deployment acceptance, no vendor activation' })
  expect(capability.activation_status).toBe('disabled')
  await patch('allowlist', capability, { status: 'enabled' }, 422)
  const riskReview = { reviewer: 'Synthetic Security Reviewer', reviewed_at: today, data_access_scope: 'Synthetic documents only', publishing_identity: 'shared_connection', external_write_actions: false }
  for (const status of ['security_review', 'data_owner_approval', 'approved', 'enabled']) {
    capability = await patch('allowlist', capability, { status, risk_review: riskReview, data_owner_approval: 'SYNTHETIC-OWNER-APPROVAL' })
  }
  expect(capability.activation_status).toBe('enabled')

  const snapshot = await create('inventory', { items: [{ kind: 'agent', external_id: capability.external_id, name: capability.name }, { kind: 'extension', external_id: 'unapproved-cloud-extension', name: 'Synthetic shadow capability' }], captured_at: new Date().toISOString() })
  const diff = await (await request.get(`/api/inventory/${snapshot.id}/diff`, { headers })).json()
  expect(diff.shadow).toHaveLength(1)
  await patch('inventory', snapshot, { reviewer: common.owner, reviewed_at: today, next_review_due: future })
  let skill = await create('skills', { version: '1.0', description: 'Synthetic cloud acceptance Skill' })
  skill = await patch('skills', skill, { version: '2.0' })
  expect(skill.versions).toHaveLength(2)
  await patch('skills', skill, { status: 'retired', retirement_date: today })

  const sharing = await create('sharing', { setting: 'project_visibility', approved_value: 'private', observed_value: 'workspace', rationale: 'Synthetic drift detection check' })
  expect(sharing.drift).toBe(true)
  let source = await create('datasources', { scope: 'Synthetic read-only source' })
  await patch('datasources', source, { status: 'enabled' }, 422)
  source = await patch('datasources', source, { status: 'enabled', approval_reference: 'SYNTHETIC-APPROVAL', permission_verified_at: today })
  await patch('datasources', source, { status: 'retired' })

  for (const phase of phases) {
    await create('rollout', { name: `Synthetic ${phase}`, phase, status: 'completed', entry_criteria: Object.fromEntries(entryCriteria[phase].map((key) => [key, true])), reassessment: Object.fromEntries(reassessment.map((key) => [key, true])), retrospective: { use_cases: 'Synthetic acceptance', barriers: 'None in synthetic test', next_changes: 'No tenant action authorized' } })
  }
  const baseline = await create('baseline', { setting: 'synthetic_scope', approved_value: 'private', observed_value: 'private', rationale: 'Synthetic rollback acceptance' })
  await patch('baseline', baseline, { approved_value: 'public' }, 422)
  let change = await create('changes', { description: 'Synthetic register-only change', baseline_id: baseline.id, before_value: 'private', after_value: 'restricted', risk_level: 'high', privileged: true, approver: 'Synthetic CAB', scheduled_start: new Date(Date.now() - 3600000).toISOString(), scheduled_end: new Date(Date.now() + 3600000).toISOString(), rollback_plan: 'Restore private in synthetic register' })
  for (const status of ['approved', 'implemented', 'rolled_back']) change = await patch('changes', change, { status, outcome: 'Synthetic acceptance verified' })
  expect((await (await request.get(`/api/baseline/${baseline.id}`, { headers })).json()).approved_value).toBe('private')

  await create('retention', { position: 'Synthetic acceptance record; not a legal or vendor retention approval', approved_by: common.owner, approved_at: today, review_due: future, reference: 'SYNTHETIC-RETENTION' })
  const evidence = await create('evidence', { artifact_type: 'certification', reference: 'SYNTHETIC-NOT-A-REAL-CERTIFICATION', expires_at: future })
  const artifactResponse = await request.post(`/api/evidence/${evidence.id}/artifacts`, { headers, multipart: { file: { name: 'synthetic-certification.txt', mimeType: 'text/plain', buffer: Buffer.from('Synthetic fixture; not a certification') } } })
  expect(artifactResponse.status()).toBe(201)
  const artifact = await artifactResponse.json()
  const artifactDownload = await request.get(`/api/evidence/${evidence.id}/artifacts/${artifact.id}`, { headers })
  expect((await artifactDownload.body()).toString()).toBe('Synthetic fixture; not a certification')
  await create('aup_incidents', { category: 'employee', severity: 'high', occurred_at: new Date().toISOString(), description: 'Synthetic incident with no personal data', status: 'resolved', escalated_to: 'Synthetic Information Security', escalation_reference: 'SYNTHETIC-SECURITY-TICKET', resolution: 'Synthetic test only; no actual disclosure' })
  const ingest = await request.post('/api/audit_logs/ingest', { headers, multipart: { platform: 'claude', tenant, file: { name: 'synthetic.json', mimeType: 'application/json', buffer: Buffer.from(JSON.stringify([{ id: 'cloud-acceptance-event', created_at: new Date().toISOString(), actor_email: 'synthetic@example.test', event_type: 'acceptance.checked', resource: 'synthetic-register' }])) } } })
  expect(ingest.status()).toBe(201)
  const bundle = await request.get(`/api/evidence/export/package?${new URLSearchParams({ platform: 'claude', tenant, start: today, end: today, format: 'json' })}`, { headers })
  expect(bundle.status()).toBe(200)
  expect(bundle.headers()['content-type']).toContain('application/zip')
  expect((await bundle.body()).subarray(0, 2).toString()).toBe('PK')
  await patch('allowlist', capability, { status: 'retired' })

  await page.goto('/')
  await expect(page.getByRole('alert').getByText('Valid bearer credential required')).toBeVisible()
  await page.locator('.topbar-right').getByRole('button', { name: 'Credentials' }).click()
  await page.getByLabel('Railway API key').fill(`Bearer ${token}`)
  await page.getByRole('button', { name: 'Connect', exact: true }).click()
  await expect(page.getByRole('dialog')).not.toBeVisible()
  await expect(page.getByText('Connected to governance API')).toBeVisible()
  await page.getByLabel('Tenant', { exact: true }).fill(tenant)
  await page.getByRole('button', { name: 'Apply tenant', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Governance overview' })).toBeVisible()
  await expect(page.locator('.loading-state')).toHaveCount(0)
  await expect(page.getByText('Connected to governance API')).toBeVisible()
  await page.screenshot({ path: 'test-results/deployment-desktop.png', fullPage: true, animations: 'disabled' })
  await page.getByRole('button', { name: 'Evidence Library', exact: true }).click()
  await page.getByRole('button', { name: common.name, exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Evidence Files', exact: true })).toBeVisible()
  await page.getByLabel('Evidence file', { exact: true }).setInputFiles({ name: 'browser-acceptance.txt', mimeType: 'text/plain', buffer: Buffer.from('Synthetic browser upload acceptance') })
  await page.getByRole('button', { name: 'Upload file', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Download browser-acceptance.txt', exact: true })).toBeVisible()
  const downloadEvent = page.waitForEvent('download')
  await page.getByRole('button', { name: 'Download browser-acceptance.txt', exact: true }).click()
  expect((await downloadEvent).suggestedFilename()).toBe('browser-acceptance.txt')
  await page.getByRole('button', { name: 'Close', exact: true }).last().click()
  await page.setViewportSize({ width: 390, height: 844 })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
  await expect(page.locator('.nav-scrim')).toHaveCount(0)
  await page.screenshot({ path: 'test-results/deployment-mobile.png', fullPage: true, animations: 'disabled' })
  expect(errors).toEqual([])
})