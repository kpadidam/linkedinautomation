import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type { Interview, Followup } from '@/lib/types.interviews'

async function http<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
  })
  if (!res.ok) throw new Error(`${res.status}`)
  return res.json() as Promise<T>
}

export function useInterviews(jobId?: string) {
  return useQuery({
    queryKey: ['interviews', jobId || 'all'],
    queryFn: () => http<Interview[]>(`/api/interviews${jobId ? `?job_id=${encodeURIComponent(jobId)}` : ''}`),
    refetchInterval: 10_000,
  })
}

export function useCreateInterview() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: Omit<Interview, 'id' | 'created_at'>) =>
      http<Interview>('/api/interviews', { method: 'POST', body: JSON.stringify(body) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['interviews'] }),
  })
}

export function useUpdateInterview() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, body }: { id: number; body: Partial<Omit<Interview, 'id' | 'job_id' | 'created_at'>> }) =>
      http<Interview>(`/api/interviews/${id}`, { method: 'PUT', body: JSON.stringify(body) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['interviews'] }),
  })
}

export function useDeleteInterview() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => http(`/api/interviews/${id}`, { method: 'DELETE' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['interviews'] }),
  })
}

export function useFollowups(jobId?: string) {
  return useQuery({
    queryKey: ['followups', jobId || 'all'],
    queryFn: () => http<Followup[]>(`/api/followups${jobId ? `?job_id=${encodeURIComponent(jobId)}` : ''}`),
    refetchInterval: 10_000,
  })
}

export function useCreateFollowup() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: { job_id: string; due_at: string; note?: string }) =>
      http<Followup>('/api/followups', { method: 'POST', body: JSON.stringify(body) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['followups'] }),
  })
}

export function useUpdateFollowup() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, body }: { id: number; body: Partial<Followup> }) =>
      http<Followup>(`/api/followups/${id}`, { method: 'PUT', body: JSON.stringify(body) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['followups'] }),
  })
}

export function useDeleteFollowup() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => http(`/api/followups/${id}`, { method: 'DELETE' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['followups'] }),
  })
}
