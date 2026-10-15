const base = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '')

export async function api(path, options = {}) {
  const headers = new Headers(options.headers)
  const token = sessionStorage.getItem('aigovern-token')
  if (token) headers.set('Authorization', `Bearer ${token}`)
  if (options.body && !(options.body instanceof FormData)) headers.set('Content-Type', 'application/json')
  const response = await fetch(`${base}/api${path}`, { ...options, headers })
  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new Error(typeof error.detail === 'string' ? error.detail : JSON.stringify(error.detail || `Request failed (${response.status})`))
  }
  return options.blob ? response.blob() : response.json()
}

export async function allRecords(resource, filters = {}) {
  let items = []
  let total = Infinity
  while (items.length < total) {
    const params = new URLSearchParams({ ...filters, limit: '1000', offset: String(items.length) })
    const page = await api(`/${resource}?${params}`)
    items = [...items, ...page.items]
    total = page.total
    if (!page.items.length) break
  }
  return items
}

export function download(blob, filename) {
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}