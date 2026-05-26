import type { Job, JobUpdate, JobsQuery, SearchRun, Statistics } from './types'

async function http<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
  })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json() as Promise<T>
}

export const api = {
  jobs: (q: JobsQuery = {}) => {
    const params = new URLSearchParams()
    if (q.limit) params.set('limit', String(q.limit))
    if (q.offset) params.set('offset', String(q.offset))
    if (q.status) params.set('status', q.status)
    if (q.min_score != null) params.set('min_score', String(q.min_score))
    const qs = params.toString()
    return http<Job[]>(`/api/jobs${qs ? `?${qs}` : ''}`)
  },
  job: (jobId: string) => http<Job>(`/api/jobs/${encodeURIComponent(jobId)}`),
  updateJob: (jobId: string, body: JobUpdate) =>
    http<{ status: string; job: Job }>(`/api/jobs/${encodeURIComponent(jobId)}`, {
      method: 'PUT',
      body: JSON.stringify(body),
    }),
  statistics: () => http<Statistics>(`/api/statistics`),
  searches: (limit = 10) => http<SearchRun[]>(`/api/searches?limit=${limit}`),
}
