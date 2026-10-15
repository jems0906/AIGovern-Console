import { useState } from 'react'
import { flexRender, getCoreRowModel, getSortedRowModel, getPaginationRowModel, useReactTable } from '@tanstack/react-table'
import { ArrowDown, ArrowUp, ArrowUpDown, ChevronLeft, ChevronRight, Inbox } from 'lucide-react'
import { label, platforms } from '../config'

export function Badge({ value }) {
  const text = typeof value === 'boolean' ? (value ? 'Yes' : 'No') : value
  return <span className={`badge state-${String(text).toLowerCase()}`}>{label(text || 'Not set')}</span>
}

export function Cell({ field, value }) {
  if (['status', 'risk_level', 'severity', 'activation_status', 'outcome'].includes(field)) return <Badge value={value} />
  if (field === 'drift') return <span className={`signal ${value ? 'danger' : 'success'}`}><i />{value ? 'Drift detected' : 'Aligned'}</span>
  if (field === 'overdue') return <span className={`signal ${value ? 'danger' : 'success'}`}><i />{value ? 'Overdue' : 'On schedule'}</span>
  if (field === 'platform') return <span className={`platform-name ${value}`}><i />{platforms[value]}</span>
  if (typeof value === 'boolean') return value ? 'Yes' : 'No'
  if (field.includes('_at') || field.includes('_due') || field === 'timestamp' || field === 'scheduled_start') return value ? new Date(value).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC' }) : <span className="muted">Not set</span>
  return value ? label(['kind', 'phase', 'artifact_type', 'category'].includes(field) ? value : '') || String(value) : <span className="muted">Not set</span>
}

export default function Table({ rows, fields, onSelect }) {
  const [sorting, setSorting] = useState([])
  const columns = fields.map((field) => ({ accessorKey: field, header: label(field), cell: ({ getValue }) => <Cell field={field} value={getValue()} /> }))
  const table = useReactTable({ data: rows, columns, state: { sorting }, onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(), getSortedRowModel: getSortedRowModel(), getPaginationRowModel: getPaginationRowModel(), initialState: { pagination: { pageSize: 10 } } })
  return <div className="table-shell">
    <div className="table-scroll"><table>
      <thead>{table.getHeaderGroups().map((group) => <tr key={group.id}>{group.headers.map((header) => <th key={header.id}><button onClick={header.column.getToggleSortingHandler()}>{flexRender(header.column.columnDef.header, header.getContext())}{header.column.getIsSorted() === 'asc' ? <ArrowUp size={12} /> : header.column.getIsSorted() === 'desc' ? <ArrowDown size={12} /> : <ArrowUpDown size={12} />}</button></th>)}</tr>)}</thead>
      <tbody>{table.getRowModel().rows.map((row) => <tr key={row.id} onClick={() => onSelect(row.original)}>{row.getVisibleCells().map((cell, index) => <td key={cell.id}>{index === 0 ? <button className="row-link" onClick={(event) => { event.stopPropagation(); onSelect(row.original) }}>{flexRender(cell.column.columnDef.cell, cell.getContext())}</button> : flexRender(cell.column.columnDef.cell, cell.getContext())}</td>)}</tr>)}</tbody>
    </table>{!rows.length && <div className="empty"><Inbox size={30} /><h3>No records found</h3><span className="muted">{rows.length} records</span></div>}</div>
    <div className="table-footer"><span>{rows.length ? table.getState().pagination.pageIndex * 10 + 1 : 0}–{Math.min((table.getState().pagination.pageIndex + 1) * 10, rows.length)} of {rows.length} records</span><div><button className="icon-button" aria-label="Previous page" title="Previous page" disabled={!table.getCanPreviousPage()} onClick={() => table.previousPage()}><ChevronLeft size={16} /></button><span>Page {table.getState().pagination.pageIndex + 1} of {Math.max(table.getPageCount(), 1)}</span><button className="icon-button" aria-label="Next page" title="Next page" disabled={!table.getCanNextPage()} onClick={() => table.nextPage()}><ChevronRight size={16} /></button></div></div>
  </div>
}