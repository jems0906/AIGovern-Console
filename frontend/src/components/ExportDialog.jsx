import { useState } from 'react'
import { Download } from 'lucide-react'
import Dialog from './Dialog'
import { platforms } from '../config'
import { api, download } from '../api/client'

export default function ExportDialog({ platform, tenant, onClose }) {
  const today = new Date().toISOString().slice(0, 10)
  const [values, setValues] = useState({ platform: platform === 'all' ? 'claude' : platform, tenant, start: `${today.slice(0, 4)}-01-01`, end: today, format: 'json' })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const set = (key, value) => setValues((old) => ({ ...old, [key]: value }))
  async function submit(event) {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      const blob = await api(`/evidence/export/package?${new URLSearchParams(values)}`, { blob: true })
      download(blob, `aigovern-${values.platform}-${values.end}.zip`)
      onClose()
    } catch (exception) { setError(exception.message) } finally { setBusy(false) }
  }
  return <Dialog title="Export Audit Package" onClose={onClose}><form onSubmit={submit}><div className="dialog-body form-grid"><label>Platform<select value={values.platform} onChange={(event) => set('platform', event.target.value)}>{Object.entries(platforms).map(([key, value]) => <option key={key} value={key}>{value}</option>)}</select></label><label>Tenant<input required value={values.tenant} onChange={(event) => set('tenant', event.target.value)} /></label><label>From (UTC)<input required type="date" value={values.start} max={values.end} onChange={(event) => set('start', event.target.value)} /></label><label>Through (UTC)<input required type="date" value={values.end} min={values.start} onChange={(event) => set('end', event.target.value)} /></label><label>Format<select value={values.format} onChange={(event) => set('format', event.target.value)}><option value="json">JSON</option><option value="csv">CSV</option></select></label>{error && <div className="form-error full" role="alert">{error}</div>}</div><footer><button className="button" type="button" onClick={onClose}>Cancel</button><button className="button primary" disabled={busy}><Download size={16} />{busy ? 'Packaging…' : 'Export package'}</button></footer></form></Dialog>
}