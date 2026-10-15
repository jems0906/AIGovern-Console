import { useState } from 'react'
import { Save } from 'lucide-react'
import Dialog from './Dialog'
import { cleanRecord, defaults, entryCriteria, label, platforms, reassessment, resources } from '../config'
import { api } from '../api/client'

const optional = new Set(['data_owner_approval', 'reviewer', 'reviewed_at', 'next_review_due', 'description', 'retirement_date', 'approval_reference', 'permission_verified_at', 'approver', 'rollback_plan', 'outcome', 'expires_at', 'obligations', 'control_change', 'posture_impact', 'escalated_to', 'escalation_reference', 'resolution'])
const transitions = {
  allowlist: { submitted: ['security_review'], security_review: ['data_owner_approval', 'denied'], data_owner_approval: ['approved', 'denied'], approved: ['enabled', 'retired'], enabled: ['retired'], denied: ['retired'], retired: [] },
  changes: { draft: ['approved'], approved: ['implemented', 'failed'], implemented: ['rolled_back'], failed: ['rolled_back'], rolled_back: [] },
}

export default function RecordForm({ resource, record, platform, tenant, baselines, onClose, onSaved }) {
  const [values, setValues] = useState(() => {
    const data = record ? { ...record } : defaults(resource, platform, tenant)
    for (const item of resources[resource].fields || []) if (item.type === 'datetime-local' && data[item.key]) {
      const time = new Date(data[item.key])
      data[item.key] = new Date(time.getTime() - time.getTimezoneOffset() * 60000).toISOString().slice(0, 16)
    }
    return data
  })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const set = (key, value) => setValues((old) => ({ ...old, [key]: value }))
  const nested = (key, field, value) => setValues((old) => ({ ...old, [key]: { ...(old[key] || {}), [field]: value } }))
  async function submit(event) {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      const body = cleanRecord(resource, values)
      if (record) body.revision = record.revision
      await api(`/${resource}${record ? `/${record.id}` : ''}`, { method: record ? 'PATCH' : 'POST', body: JSON.stringify(body) })
      onSaved()
    } catch (exception) { setError(exception.message) } finally { setBusy(false) }
  }
  function renderField(item) {
    const { key, type } = item
    const value = values[key] ?? ''
    const title = label(key)
    if (type === 'risk') return <fieldset key={key} className="form-section"><legend>Security Risk Review</legend><label className="check"><input type="checkbox" checked={Boolean(value)} onChange={(event) => set(key, event.target.checked ? { reviewer: '', reviewed_at: '', data_access_scope: '', publishing_identity: 'shared_connection', external_write_actions: false, notes: '' } : null)} />Risk review recorded</label>{value && <div className="form-grid"><label>Reviewer<input required value={value.reviewer || ''} onChange={(event) => nested(key, 'reviewer', event.target.value)} /></label><label>Reviewed at<input type="date" required value={value.reviewed_at || ''} onChange={(event) => nested(key, 'reviewed_at', event.target.value)} /></label><label>Data access scope<input required value={value.data_access_scope || ''} onChange={(event) => nested(key, 'data_access_scope', event.target.value)} /></label><label>Publishing identity<select value={value.publishing_identity} onChange={(event) => nested(key, 'publishing_identity', event.target.value)}><option value="personal">Personal</option><option value="shared_connection">Shared connection</option></select></label><label className="check"><input type="checkbox" checked={value.external_write_actions || false} onChange={(event) => nested(key, 'external_write_actions', event.target.checked)} />External write actions</label><label>Review notes<textarea value={value.notes || ''} onChange={(event) => nested(key, 'notes', event.target.value)} /></label></div>}</fieldset>
    if (['criteria', 'reassessment'].includes(type)) return <fieldset key={key} className="form-section"><legend>{title}</legend><div className="checklist">{(type === 'criteria' ? entryCriteria[values.phase] : reassessment).map((criterion) => <label key={criterion} className="check"><input type="checkbox" checked={value[criterion] || false} onChange={(event) => nested(key, criterion, event.target.checked)} />{label(criterion)}</label>)}</div></fieldset>
    if (type === 'retrospective') return <fieldset key={key} className="form-section"><legend>Phase Retrospective</legend><div className="form-grid">{['use_cases', 'barriers', 'next_changes'].map((field) => <label key={field}>{label(field)}<textarea value={value[field] || ''} onChange={(event) => nested(key, field, event.target.value)} /></label>)}</div></fieldset>
    if (type === 'checkbox') return <label key={key} className="check"><input type="checkbox" checked={Boolean(value)} onChange={(event) => set(key, event.target.checked)} />{title}</label>
    if (type === 'baseline') return <label key={key}>Configuration baseline<select required value={value} onChange={(event) => {
      const baseline = baselines.find((row) => row.id === event.target.value)
      setValues((old) => ({ ...old, baseline_id: event.target.value, before_value: baseline?.approved_value || '' }))
    }}><option value="">Select baseline</option>{baselines.filter((row) => row.platform === values.platform && row.tenant === values.tenant).map((row) => <option key={row.id} value={row.id}>{row.name}</option>)}</select></label>
    let options = item.options
    if (key === 'status' && transitions[resource]) options = record ? [record.status, ...transitions[resource][record.status]] : [item.options[0]]
    const readOnly = Boolean(record && ((resource === 'baseline' && key === 'approved_value') || (resource === 'allowlist' && ['kind', 'external_id', 'workspace_agent'].includes(key))))
    return <label key={key} className={type === 'textarea' ? 'full' : ''}>{title}{type === 'select' ? <select aria-label={title} disabled={readOnly} value={value} onChange={(event) => set(key, event.target.value)}>{options.map((option) => <option key={option} value={option}>{label(option)}</option>)}</select> : type === 'textarea' ? <textarea value={value} onChange={(event) => set(key, event.target.value)} /> : <input required={!optional.has(key)} readOnly={readOnly} type={type} value={value} onChange={(event) => set(key, event.target.value)} />}</label>
  }
  return <Dialog wide title={`${record ? 'Edit' : 'New'} ${resources[resource].singular}`} onClose={onClose}><form onSubmit={submit}><div className="dialog-body"><div className="form-grid"><label>Name<input autoFocus required maxLength={200} value={values.name} onChange={(event) => set('name', event.target.value)} /></label><label>Owner<input required value={values.owner} onChange={(event) => set('owner', event.target.value)} /></label><label>Platform<select disabled={Boolean(record)} value={values.platform} onChange={(event) => set('platform', event.target.value)}>{Object.entries(platforms).map(([key, title]) => <option key={key} value={key}>{title}</option>)}</select></label><label>Tenant<input required readOnly={Boolean(record)} value={values.tenant} onChange={(event) => set('tenant', event.target.value)} /></label>{resources[resource].fields.map(renderField)}</div>{error && <div className="form-error" role="alert">{error}</div>}</div><footer><button type="button" className="button" onClick={onClose}>Cancel</button><button type="submit" className="button primary" disabled={busy}><Save size={16} />{busy ? 'Saving…' : 'Save record'}</button></footer></form></Dialog>
}