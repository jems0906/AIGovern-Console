import { useState } from 'react'
import { Upload } from 'lucide-react'
import Dialog from './Dialog'
import { platforms } from '../config'
import { api } from '../api/client'

export default function ImportDialog({ resource, platform, tenant, onClose, onSaved }) {
  const [selected, setSelected] = useState(platform === 'all' ? 'claude' : platform)
  const [file, setFile] = useState(null)
  const [owner, setOwner] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  async function submit(event) {
    event.preventDefault()
    const body = new FormData()
    body.append('platform', selected)
    body.append('tenant', tenant)
    body.append('file', file)
    if (resource === 'inventory') body.append('owner', owner)
    setBusy(true)
    setError('')
    try {
      const result = await api(resource === 'inventory' ? '/inventory/import/snapshot' : '/audit_logs/ingest', { method: 'POST', body })
      onSaved(resource === 'audit_logs' ? `${result.imported} events imported · ${result.duplicates} duplicates skipped` : 'Inventory snapshot imported')
    } catch (exception) { setError(exception.message) } finally { setBusy(false) }
  }
  return <Dialog title={resource === 'inventory' ? 'Import Inventory Snapshot' : 'Import Audit Events'} onClose={onClose}><form onSubmit={submit}><div className="dialog-body form-grid"><label>Platform<select value={selected} onChange={(event) => setSelected(event.target.value)}>{Object.entries(platforms).map(([key, value]) => <option key={key} value={key}>{value}</option>)}</select></label><label>Tenant<input readOnly value={tenant} /></label>{resource === 'inventory' && <label className="full">Inventory owner<input required value={owner} onChange={(event) => setOwner(event.target.value)} /></label>}<label className="full file-input">CSV / JSON file<input required type="file" accept=".csv,.json" onChange={(event) => setFile(event.target.files[0])} /></label>{error && <div className="form-error full" role="alert">{error}</div>}</div><footer><button className="button" type="button" onClick={onClose}>Cancel</button><button className="button primary" disabled={busy || !file}><Upload size={16} />{busy ? 'Importing…' : 'Import'}</button></footer></form></Dialog>
}