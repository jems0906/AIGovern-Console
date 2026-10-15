import { useEffect, useState } from 'react'
import { Pencil, Clock, AlertTriangle } from 'lucide-react'
import Dialog from './Dialog'
import { Cell } from './Table'
import { label, resources } from '../config'
import { api } from '../api/client'

function Value({ value }) {
  if (value === null || value === undefined || value === '') return <span className="muted">Not recorded</span>
  if (typeof value === 'boolean') return value ? 'Yes' : 'No'
  if (Array.isArray(value)) return <div className="detail-list">{value.map((item, index) => <div key={index}><Value value={item} /></div>)}</div>
  if (typeof value === 'object') return <dl className="nested-details">{Object.entries(value).map(([key, item]) => <div key={key}><dt>{label(key)}</dt><dd><Value value={item} /></dd></div>)}</dl>
  return String(value)
}

export default function Detail({ resource, record, canWrite, onClose, onEdit }) {
  const [history, setHistory] = useState([])
  const [diff, setDiff] = useState(null)
  const [error, setError] = useState('')
  useEffect(() => {
    let active = true
    api(`/audit_logs/governance/history?record_id=${record.id}`).then((data) => { if (active) setHistory(data.items) }).catch((exception) => { if (active) setError(exception.message) })
    if (resource === 'inventory') api(`/inventory/${record.id}/diff`).then((data) => { if (active) setDiff(data) }).catch((exception) => { if (active) setError(exception.message) })
    return () => { active = false }
  }, [resource, record.id])
  return <Dialog wide title={record.name || record.action} onClose={onClose}><div className="dialog-body"><div className="detail-top"><span className="eyebrow">{resources[resource].singular} · {record.id.slice(0, 8)}</span>{canWrite && !resources[resource].readonly && <button className="button" onClick={onEdit}><Pencil size={15} />Edit record</button>}</div>{error && <div className="form-error" role="alert">{error}</div>}
    {diff && <section className="diff-section"><h3><AlertTriangle size={17} />Snapshot Findings</h3><div className="diff-counts"><span><b>{diff.new.length}</b> New</span><span className="danger"><b>{diff.shadow.length}</b> Unapproved</span><span><b>{diff.removed.length}</b> Removed</span></div>{diff.shadow.map((item) => <div className="finding" key={`${item.kind}-${item.external_id}`}><span>{item.name}</span><span className="badge state-high">{label(item.kind)}</span></div>)}</section>}
    <dl className="record-details">{Object.entries(record).filter(([key]) => !['id', 'revision', 'items'].includes(key)).map(([key, value]) => <div key={key}><dt>{label(key)}</dt><dd>{['status', 'platform', 'drift', 'activation_status', 'overdue'].includes(key) ? <Cell field={key} value={value} /> : <Value value={value} />}</dd></div>)}</dl>
    {record.items && <section><h3>Inventory Items</h3><Value value={record.items} /></section>}
    <section className="history"><h3><Clock size={17} />Change History</h3>{history.length === 0 ? <p className="muted">No history recorded</p> : history.map((item) => <details key={item.id}><summary><span>{label(item.action)}</span><span className="muted">{item.actor} · {new Date(item.timestamp).toLocaleString()}</span></summary><div className="history-compare"><div><h4>Before</h4><Value value={item.before} /></div><div><h4>After</h4><Value value={item.after} /></div></div></details>)}</section>
  </div><footer><button className="button" onClick={onClose}>Close</button></footer></Dialog>
}