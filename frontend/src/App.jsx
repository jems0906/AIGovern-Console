import { useEffect, useState } from 'react'
import { Activity, LayoutDashboard, ListChecks, Boxes, BookOpen, Share2, Database, Flag, SlidersHorizontal, GitPullRequest, Files, Archive, Search, ShieldAlert, RefreshCw, Download, Plus, Upload, Menu, X, KeyRound, LogOut, ChevronRight, ShieldCheck } from 'lucide-react'
import { api, allRecords, normalizeCredential } from './api/client'
import { loadAuthConfig, signInWithMicrosoft, signOutMicrosoft } from './api/entra'
import { platforms, resources, label } from './config'
import Table from './components/Table'
import Dialog from './components/Dialog'
import RecordForm from './components/RecordForm'
import Detail from './components/Detail'
import ImportDialog from './components/ImportDialog'
import ExportDialog from './components/ExportDialog'
import Overview from './pages/Overview'

const icons = { overview: LayoutDashboard, allowlist: ListChecks, inventory: Boxes, skills: BookOpen, sharing: Share2, datasources: Database, rollout: Flag, baseline: SlidersHorizontal, changes: GitPullRequest, evidence: Files, retention: Archive, audit_logs: Activity, aup_incidents: ShieldAlert }
const emptyData = Object.fromEntries(Object.keys(resources).map((key) => [key, []]))

export default function App() {
  const initialPage = window.location.hash.slice(1)
  const [page, setPage] = useState(resources[initialPage] ? initialPage : 'overview')
  const [platform, setPlatform] = useState('all')
  const [tenant, setTenant] = useState('demo')
  const [tenantInput, setTenantInput] = useState('demo')
  const [query, setQuery] = useState('')
  const [status, setStatus] = useState('all')
  const [data, setData] = useState(emptyData)
  const [session, setSession] = useState(null)
  const [authConfig, setAuthConfig] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [reload, setReload] = useState(0)
  const [modal, setModal] = useState(null)
  const [mobile, setMobile] = useState(false)
  const [token, setToken] = useState('')
  const [authError, setAuthError] = useState('')
  const [authBusy, setAuthBusy] = useState(false)
  const [auditDates, setAuditDates] = useState({ start: '', end: '', action: '' })
  const canWrite = session && session.role !== 'viewer'
  const current = resources[page]
  function go(next) { setPage(next); window.location.hash = next; setQuery(''); setStatus('all'); setMobile(false) }
  function openAuth() { setToken(''); setAuthError(''); setModal({ type: 'auth' }) }
  async function connect(event) {
    event.preventDefault()
    const credential = normalizeCredential(token)
    if (!credential) { setAuthError('Enter the ADMIN_API_KEY from Railway.'); return }
    setAuthBusy(true)
    setAuthError('')
    try {
      await api('/session', { credential })
      sessionStorage.setItem('aigovern-token', credential)
      setToken('')
      setModal(null)
      setReload((count) => count + 1)
    } catch (exception) {
      sessionStorage.removeItem('aigovern-token')
      setAuthError(exception.message)
      setReload((count) => count + 1)
    } finally { setAuthBusy(false) }
  }
  async function connectMicrosoft() {
    setAuthBusy(true)
    setAuthError('')
    try {
      await signInWithMicrosoft()
    } catch (exception) {
      setAuthError(exception.message)
    } finally { setAuthBusy(false) }
  }
  function signOut() {
    sessionStorage.removeItem('aigovern-token')
    signOutMicrosoft().catch(() => {})
    setToken('')
    setAuthError('')
    setModal(null)
    setReload((count) => count + 1)
  }
  useEffect(() => {
    const handler = () => { const next = window.location.hash.slice(1); if (resources[next] || next === 'overview') { setPage(next); setQuery(''); setStatus('all') } }
    window.addEventListener('hashchange', handler)
    return () => window.removeEventListener('hashchange', handler)
  }, [])
  useEffect(() => {
    let active = true
    loadAuthConfig().then((config) => { if (active) setAuthConfig(config) }).catch(() => {})
    return () => { active = false }
  }, [])
  useEffect(() => {
    let active = true
    setLoading(true)
    setError('')
    const filters = { tenant, ...(platform === 'all' ? {} : { platform }) }
    Promise.all([api('/session'), ...Object.keys(resources).map((key) => allRecords(key, filters))]).then(([user, ...rows]) => {
      if (active) { setSession(user); setData(Object.fromEntries(Object.keys(resources).map((key, index) => [key, rows[index]]))) }
    }).catch((exception) => { if (active) { setError(exception.message); setData(emptyData); setSession(null) } }).finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [platform, tenant, reload])
  useEffect(() => { if (!notice) return; const timer = setTimeout(() => setNotice(''), 5000); return () => clearTimeout(timer) }, [notice])
  function saved(message = 'Record saved') { setModal(null); setReload((count) => count + 1); setNotice(message) }
  let rows = (data[page] || []).filter((record) => (!query || JSON.stringify(record).toLowerCase().includes(query.toLowerCase())) && (status === 'all' || record.status === status))
  if (page === 'audit_logs') rows = rows.filter((record) => (!auditDates.start || record.timestamp.slice(0, 10) >= auditDates.start) && (!auditDates.end || record.timestamp.slice(0, 10) <= auditDates.end) && (!auditDates.action || record.action === auditDates.action))
  const statuses = [...new Set((data[page] || []).map((record) => record.status).filter(Boolean))]
  const needsAttention = data.allowlist.filter((record) => ['submitted', 'security_review', 'data_owner_approval'].includes(record.status)).length
  const NavIcon = icons[page]
  return <div className="app-shell">
    {mobile && <button className="nav-scrim" aria-label="Close navigation" onClick={() => setMobile(false)} />}
    <aside className={`sidebar ${mobile ? 'open' : ''}`}><a className="brand" href="#overview" onClick={() => go('overview')}><img src="/mark.svg" width="34" height="34" alt="" /><span>AIGovern<small>GOVERNANCE CONSOLE</small></span></a><button className="mobile-close icon-button" title="Close navigation" aria-label="Close navigation" onClick={() => setMobile(false)}><X size={20} /></button>
      <div className="workspace-label"><span className="workspace-avatar">AC</span><div><b>Acme Corporation</b><small>{tenant === 'demo' ? 'Synthetic tenant' : tenant}</small></div><span className="workspace-dot" /></div>
      <nav aria-label="Primary navigation"><button className={`nav-item ${page === 'overview' ? 'selected' : ''}`} onClick={() => go('overview')}><LayoutDashboard size={18} />Overview<span className="nav-shortcut">01</span></button>{['CAPABILITIES', 'CONTROLS', 'ASSURANCE'].map((section) => <div className="nav-group" key={section}><h2>{section}</h2>{Object.entries(resources).filter(([, value]) => value.section === section).map(([key, value]) => { const Icon = icons[key]; return <button className={`nav-item ${page === key ? 'selected' : ''}`} key={key} onClick={() => go(key)}><Icon size={17} /><span>{value.title}</span>{key === 'allowlist' && needsAttention > 0 && <span className="nav-count">{needsAttention}</span>}</button> })}</div>)}</nav>
      <div className="sidebar-bottom"><div className="assurance-label"><ShieldCheck size={17} /><span>Governed by design</span></div><button className="profile" onClick={openAuth}><span className="profile-avatar">{session?.role === 'viewer' ? 'GV' : 'GA'}</span><span><b>{session ? label(session.role) : 'Sign in'}</b><small>{session?.demo ? 'Local demo session' : 'Governance workspace'}</small></span><KeyRound size={15} /></button></div>
    </aside>
    <div className="main-shell"><header className="topbar"><div className="breadcrumb"><button className="icon-button mobile-menu" title="Open navigation" aria-label="Open navigation" onClick={() => setMobile(true)}><Menu size={21} /></button><span>Workspace</span><ChevronRight size={13} /><b>{current?.title || 'Overview'}</b></div><div className="topbar-right"><span className={`environment ${session?.demo ? 'demo' : ''}`}><i />{session?.demo ? 'LOCAL DEMO' : session?.environment?.toUpperCase() || 'DISCONNECTED'}</span><button className="icon-button" title="Credentials" aria-label="Credentials" onClick={openAuth}><KeyRound size={17} /></button></div></header>
      <main><div className="page-heading"><div><span className="eyebrow">AI PLATFORM GOVERNANCE</span><h1>{page === 'overview' ? 'Governance overview' : current.title}</h1><p>{page === 'overview' ? 'Your AI estate. Accountable, reviewed, under control.' : `${rows.length} records · ${platform === 'all' ? 'All platforms' : platforms[platform]} · ${tenant}`}</p></div><div className="heading-actions"><button className={`icon-button refresh ${loading ? 'spinning' : ''}`} title="Refresh records" aria-label="Refresh records" onClick={() => setReload((count) => count + 1)} disabled={loading}><RefreshCw size={17} /></button><button className="button" onClick={() => setModal({ type: 'export' })} disabled={!session}><Download size={16} />Audit package</button>{page !== 'overview' && canWrite && (current.import ? <button className="button primary" onClick={() => setModal({ type: 'import' })}><Upload size={16} />Import</button> : <button className="button primary" onClick={() => setModal({ type: 'form', resource: page })}><Plus size={17} />New {current.singular.toLowerCase()}</button>)}</div></div>
      <div className="scope-bar"><div className="platform-tabs" role="tablist" aria-label="Platform scope">{[['all', 'All platforms'], ...Object.entries(platforms)].map(([key, value]) => <button key={key} role="tab" aria-selected={platform === key} className={platform === key ? 'active' : ''} onClick={() => setPlatform(key)}>{key !== 'all' && <i className={`platform-dot ${key}`} />}{value}</button>)}</div><form className="tenant-picker" onSubmit={(event) => { event.preventDefault(); if (tenantInput.trim()) setTenant(tenantInput.trim()) }}><label htmlFor="tenant">Tenant</label><input id="tenant" value={tenantInput} onChange={(event) => setTenantInput(event.target.value)} /><button type="submit" className="icon-button" title="Apply tenant" aria-label="Apply tenant"><ChevronRight size={16} /></button></form></div>
      {error && <div className="error-banner" role="alert"><ShieldAlert size={19} /><span>{error}</span><button className="button" onClick={openAuth}>Credentials</button></div>}
      {loading ? <div className="loading-state" role="status"><RefreshCw size={24} className="spinning" /><span>Loading governance records</span></div> : page === 'overview' ? <Overview data={data} platform={platform} go={go} onSelect={(resource, record) => setModal({ type: 'detail', resource, record })} /> : <section className="register-section"><div className="register-tools"><div className="register-title"><NavIcon size={18} /><h2>{current.singular} register</h2><span className="subtle-tag">{rows.length}</span></div><div className="table-filters"><label className="search-box"><Search size={16} /><input aria-label="Search records" placeholder="Search records…" value={query} onChange={(event) => setQuery(event.target.value)} /></label>{statuses.length > 0 && <select aria-label="Filter by status" value={status} onChange={(event) => setStatus(event.target.value)}><option value="all">All statuses</option>{statuses.map((value) => <option key={value} value={value}>{label(value)}</option>)}</select>}</div></div>{page === 'audit_logs' && <div className="audit-filters"><label>From (UTC)<input type="date" value={auditDates.start} onChange={(event) => setAuditDates({ ...auditDates, start: event.target.value })} /></label><label>Through (UTC)<input type="date" value={auditDates.end} onChange={(event) => setAuditDates({ ...auditDates, end: event.target.value })} /></label><label>Action<select value={auditDates.action} onChange={(event) => setAuditDates({ ...auditDates, action: event.target.value })}><option value="">All actions</option>{[...new Set(data.audit_logs.map((record) => record.action))].map((action) => <option key={action}>{action}</option>)}</select></label></div>}<Table key={`${page}-${platform}-${tenant}-${status}-${query}`} rows={rows} fields={current.columns} onSelect={(record) => setModal({ type: 'detail', resource: page, record })} /></section>}
      <div className="page-footer"><span>AIGovern Console</span><span>Claude · ChatGPT Enterprise · Microsoft 365 Copilot</span><span className="footer-status"><i />{session ? 'Connected to governance API' : 'API unavailable'}</span></div>
      </main></div>
    {notice && <div className="toast" role="status"><ShieldCheck size={18} />{notice}<button className="icon-button" aria-label="Dismiss notification" onClick={() => setNotice('')}><X size={15} /></button></div>}
    {modal?.type === 'form' && <RecordForm resource={modal.resource} record={modal.record} platform={platform} tenant={tenant} baselines={data.baseline} onClose={() => setModal(null)} onSaved={() => saved()} />}
    {modal?.type === 'detail' && <Detail resource={modal.resource} record={modal.record} canWrite={canWrite} onClose={() => setModal(null)} onEdit={() => setModal({ ...modal, type: 'form' })} />}
    {modal?.type === 'import' && <ImportDialog resource={page} platform={platform} tenant={tenant} onClose={() => setModal(null)} onSaved={saved} />}
    {modal?.type === 'export' && <ExportDialog platform={platform} tenant={tenant} onClose={() => setModal(null)} />}
    {modal?.type === 'auth' && <Dialog title="Workspace Sign In" onClose={() => setModal(null)}>{authConfig?.mode === 'entra' ? <div><div className="dialog-body"><p>Sign in with your organization account. Access is based on your assigned AIGovern application role.</p>{authError && <div className="form-error" role="alert">{authError}</div>}</div><footer><button type="button" className="button" onClick={signOut}><LogOut size={16} />Sign out</button><button type="button" className="button primary" disabled={authBusy} onClick={connectMicrosoft}><KeyRound size={16} />{authBusy ? 'Signing in…' : 'Sign in with Microsoft'}</button></footer></div> : <form onSubmit={connect}><div className="dialog-body"><label>Railway API key<input autoFocus autoComplete="off" placeholder="Paste ADMIN_API_KEY; Bearer prefix optional" type="password" value={token} onChange={(event) => setToken(event.target.value)} /></label><p className="muted">Retrieve ADMIN_API_KEY from the Railway backend Variables. The key is kept only for this browser tab.</p>{authError && <div className="form-error" role="alert">{authError}</div>}{session && <p className="muted">Session: {session.actor}</p>}</div><footer><button type="button" className="button" onClick={signOut}><LogOut size={16} />Sign out</button><button type="submit" className="button primary" disabled={authBusy}><KeyRound size={16} />{authBusy ? 'Checking…' : 'Connect'}</button></footer></form>}</Dialog>}
  </div>
}