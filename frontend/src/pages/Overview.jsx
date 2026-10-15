import { ArrowRight, ShieldCheck, AlertTriangle, Clock3, FileCheck2, ArrowUpRight, CircleCheck } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { platforms, label } from '../config'
import { Badge, Cell } from '../components/Table'

export function summarize(data) {
  const approved = data.allowlist.filter((item) => ['approved', 'enabled'].includes(item.status))
  const pending = data.allowlist.filter((item) => ['submitted', 'security_review', 'data_owner_approval'].includes(item.status))
  const drift = [...data.sharing, ...data.baseline].filter((item) => item.drift)
  const latest = new Map()
  for (const item of [...data.inventory].sort((first, second) => second.created_at.localeCompare(first.created_at))) {
    const key = `${item.platform}:${item.tenant}`
    if (!latest.has(key)) latest.set(key, item)
  }
  const shadow = [...latest.values()].flatMap((snapshot) => snapshot.items.filter((item) => !approved.some((request) => request.platform === snapshot.platform && request.tenant === snapshot.tenant && request.kind === item.kind && request.external_id === item.external_id)).map((item) => ({ ...item, platform: snapshot.platform })))
  const overdue = [...latest.values()].filter((item) => item.overdue || !item.reviewed_at)
  return { approved, pending, drift, shadow, overdue }
}

export default function Overview({ data, go, onSelect, platform }) {
  const { approved, pending, drift, shadow, overdue } = summarize(data)
  const activePlatforms = Object.keys(platforms).filter((key) => platform === 'all' || key === platform)
  const chart = activePlatforms.map((key) => ({ name: key === 'chatgpt' ? 'ChatGPT' : label(key), approved: approved.filter((item) => item.platform === key).length, review: pending.filter((item) => item.platform === key).length, shadow: shadow.filter((item) => item.platform === key).length }))
  const actions = [
    { title: 'Security reviews', detail: 'Requests awaiting approval', value: pending.length, page: 'allowlist', icon: ShieldCheck },
    { title: 'Shadow capabilities', detail: 'Inventory without approved requests', value: shadow.length, page: 'inventory', icon: AlertTriangle },
    { title: 'Configuration drift', detail: 'Settings outside approved baseline', value: drift.length, page: 'baseline', icon: FileCheck2 },
    { title: 'Inventory reviews', detail: 'Overdue or unsigned snapshots', value: overdue.length, page: 'inventory', icon: Clock3 },
  ]
  const recent = [...data.allowlist].sort((first, second) => second.updated_at.localeCompare(first.updated_at)).slice(0, 5)
  return <>
    <section className="metric-grid" aria-label="Governance summary">
      {[{ label: 'Approved capabilities', value: approved.length, note: `${data.allowlist.filter((item) => item.status === 'enabled').length} currently enabled`, icon: ShieldCheck, tone: 'green' }, { label: 'Pending decisions', value: pending.length, note: 'Security & data owner review', icon: Clock3, tone: 'amber' }, { label: 'Control exceptions', value: drift.length + shadow.length, note: `${drift.length} drift · ${shadow.length} unapproved`, icon: AlertTriangle, tone: 'coral' }, { label: 'Evidence artifacts', value: data.evidence.length, note: `${data.evidence.filter((item) => item.expired).length} expired artifacts`, icon: FileCheck2, tone: 'blue' }].map((metric) => <article className={`metric ${metric.tone}`} key={metric.label}><div><span>{metric.label}</span><metric.icon size={19} /></div><strong>{metric.value.toString().padStart(2, '0')}</strong><small>{metric.note}</small></article>)}
    </section>
    <div className="overview-grid">
      <section className="posture-section"><div className="section-heading"><div><span className="eyebrow">PLATFORM COVERAGE</span><h2>Capability posture</h2></div><span className="subtle-tag">Live register</span></div><div className="chart-legend"><span><i className="legend-green" />Approved</span><span><i className="legend-amber" />In review</span><span><i className="legend-coral" />Unapproved</span></div><div className="posture-chart" aria-label="Capability counts by platform"><ResponsiveContainer width="100%" height="100%"><BarChart data={chart} barSize={28} margin={{ top: 15, right: 16, left: -24, bottom: 4 }}><CartesianGrid strokeDasharray="3 5" vertical={false} stroke="#dfe7e2" /><XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: '#65736c', fontSize: 12 }} dy={10} /><YAxis allowDecimals={false} axisLine={false} tickLine={false} tick={{ fill: '#65736c', fontSize: 11 }} /><Tooltip cursor={{ fill: '#edf3ef' }} contentStyle={{ borderRadius: 4, border: '1px solid #dce5df', fontSize: 12 }} /><Bar isAnimationActive={false} dataKey="approved" name="Approved" stackId="posture" fill="#23715b" /><Bar isAnimationActive={false} dataKey="review" name="In review" stackId="posture" fill="#e4b65a" /><Bar isAnimationActive={false} dataKey="shadow" name="Unapproved" stackId="posture" fill="#cf705c" radius={[3, 3, 0, 0]} /></BarChart></ResponsiveContainer></div><div className="platform-strip">{activePlatforms.map((key) => <div key={key}><span className={`platform-dot ${key}`} /><span>{platforms[key]}</span><b>{data.allowlist.filter((item) => item.platform === key).length}</b></div>)}</div></section>
      <section className="attention-section"><div className="section-heading"><div><span className="eyebrow">REVIEW QUEUE</span><h2>Needs attention</h2></div><span className="count-bubble">{actions.reduce((sum, action) => sum + action.value, 0)}</span></div><div className="attention-list">{actions.map((action) => <button key={action.title} onClick={() => go(action.page)}><span className={`attention-icon ${action.value ? 'warn' : ''}`}><action.icon size={18} /></span><span className="attention-copy"><b>{action.title}</b><small>{action.detail}</small></span><strong>{action.value}</strong><ArrowUpRight size={16} /></button>)}</div><div className="queue-note"><CircleCheck size={16} /><span>{data.audit_logs.length} normalized audit events in scope</span></div></section>
    </div>
    <section className="recent-section"><div className="section-heading"><div><span className="eyebrow">CHANGE & ACCESS</span><h2>Recent capability requests</h2></div><button className="text-button" onClick={() => go('allowlist')}>View all requests<ArrowRight size={16} /></button></div><div className="table-scroll"><table><thead><tr>{['Capability', 'Platform', 'Owner', 'Workflow', 'Activation', ''].map((title) => <th key={title}>{title}</th>)}</tr></thead><tbody>{recent.map((record) => <tr key={record.id} onClick={() => onSelect('allowlist', record)}><td><button className="row-link" onClick={(event) => { event.stopPropagation(); onSelect('allowlist', record) }}>{record.name}<small>{label(record.kind)}</small></button></td><td><Cell field="platform" value={record.platform} /></td><td>{record.owner}</td><td><Badge value={record.status} /></td><td><span className={`signal ${record.activation_status === 'enabled' ? 'success' : 'neutral'}`}><i />{label(record.activation_status)}</span></td><td><ArrowUpRight size={16} /></td></tr>)}</tbody></table>{!recent.length && <div className="empty"><ShieldCheck size={28} /><h3>No requests in this scope</h3></div>}</div></section>
    <section className="rollout-strip"><div><span className="eyebrow">CONTROLLED EXPANSION</span><h2>Rollout readiness</h2></div><div className="phase-track">{['core', 'intelligence', 'integrations', 'automation_agents'].map((phase, index) => {
      const rows = data.rollout.filter((item) => item.phase === phase)
      const complete = rows.length > 0 && rows.every((item) => item.status === 'completed')
      const active = rows.some((item) => item.status === 'active')
      return <button key={phase} className={complete ? 'complete' : active ? 'active' : ''} onClick={() => go('rollout')}><span>{complete ? <CircleCheck size={18} /> : String(index + 1).padStart(2, '0')}</span><b>{label(phase)}</b><small>{complete ? 'Completed' : active ? 'In progress' : 'Planned'}</small></button>
    })}</div></section>
  </>
}