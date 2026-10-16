import { useEffect, useState } from 'react'
import { Download, FileCheck2, Upload } from 'lucide-react'
import { api, download } from '../api/client'

export default function EvidenceFiles({ recordId, canWrite }) {
  const [files, setFiles] = useState([])
  const [selected, setSelected] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  useEffect(() => {
    let active = true
    api(`/evidence/${recordId}/artifacts`).then((data) => { if (active) setFiles(data.items) }).catch((exception) => { if (active) setError(exception.message) })
    return () => { active = false }
  }, [recordId])
  async function upload(event) {
    event.preventDefault()
    const form = event.currentTarget
    const body = new FormData()
    body.append('file', selected)
    setBusy(true)
    setError('')
    try {
      const artifact = await api(`/evidence/${recordId}/artifacts`, { method: 'POST', body })
      setFiles((current) => [artifact, ...current])
      setSelected(null)
      form.reset()
    } catch (exception) { setError(exception.message) } finally { setBusy(false) }
  }
  async function fetchFile(file) {
    setError('')
    try { download(await api(`/evidence/${recordId}/artifacts/${file.id}`, { blob: true }), file.filename) }
    catch (exception) { setError(exception.message) }
  }
  return <section className="evidence-files"><h3><FileCheck2 size={17} />Evidence Files</h3>
    {files.length === 0 && <p className="muted">No files attached</p>}
    {files.map((file) => <div className="evidence-file" key={file.id}><div><b>{file.filename}</b><small>{(file.size_bytes / 1024).toFixed(1)} KB · {file.uploaded_by} · {new Date(file.created_at).toLocaleDateString()}</small><code>SHA-256 {file.sha256}</code></div><button className="icon-button" title={`Download ${file.filename}`} aria-label={`Download ${file.filename}`} onClick={() => fetchFile(file)}><Download size={17} /></button></div>)}
    {canWrite && <form className="evidence-upload" onSubmit={upload}><label>Evidence file<input type="file" required accept=".pdf,.txt,.json,.csv,.png,.jpg,.jpeg" onChange={(event) => setSelected(event.target.files[0])} /></label><button className="button" disabled={busy || !selected}><Upload size={16} />{busy ? 'Uploading…' : 'Upload file'}</button></form>}
    {error && <div className="form-error" role="alert">{error}</div>}
  </section>
}