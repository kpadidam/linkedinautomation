import { useEffect, useRef, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { clearSettingsDirty } from '@/lib/settingsDirty'

export interface PendingProgress {
  completed_index: number    // index of last fully-completed category (0-based)
  total_categories: number
  started_at: string         // ISO datetime when run originally started
  age_hours: number
}

export interface NextTrigger {
  next_at: string            // ISO datetime
  frequency_hours: number    // legacy/back-compat (rounded)
  frequency_minutes: number  // canonical, sub-hour-aware
  seconds_until: number      // negative if overdue
  last_run_at: string | null
}

export interface SessionStatus {
  running: boolean
  paused: boolean
  paused_at: string | null
  pause_duration_seconds: number
  pid: number | null
  started_at: string | null
  exit_code: number | null
  log_count: number
  pending_progress: PendingProgress | null
  next_trigger: NextTrigger | null
}

export function useSessionStatus() {
  return useQuery({
    queryKey: ['session-status'],
    queryFn: async () => {
      const r = await fetch('/api/sessions/status')
      return (await r.json()) as SessionStatus
    },
    refetchInterval: 2000,
  })
}

export function useStartSession() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async () => {
      const r = await fetch('/api/sessions/start', { method: 'POST' })
      if (!r.ok) {
        const err = await r.json().catch(() => ({}))
        throw new Error(err.detail || `${r.status} ${r.statusText}`)
      }
      return r.json()
    },
    onSuccess: () => {
      clearSettingsDirty()
      qc.invalidateQueries({ queryKey: ['session-status'] })
    },
  })
}

export function useStopSession() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async () => {
      const r = await fetch('/api/sessions/stop', { method: 'POST' })
      if (!r.ok) {
        const err = await r.json().catch(() => ({}))
        throw new Error(err.detail || `${r.status} ${r.statusText}`)
      }
      return r.json()
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['session-status'] }),
  })
}

export function useResetSession() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async () => {
      const r = await fetch('/api/sessions/reset', { method: 'POST' })
      if (!r.ok) {
        const err = await r.json().catch(() => ({}))
        throw new Error(err.detail || `${r.status} ${r.statusText}`)
      }
      return r.json()
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['session-status'] }),
  })
}

export function usePauseSession() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async () => {
      const r = await fetch('/api/sessions/pause', { method: 'POST' })
      if (!r.ok) {
        const err = await r.json().catch(() => ({}))
        throw new Error(err.detail || `${r.status} ${r.statusText}`)
      }
      return r.json()
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['session-status'] }),
  })
}

export function useResumePausedSession() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async () => {
      const r = await fetch('/api/sessions/resume', { method: 'POST' })
      if (!r.ok) {
        const err = await r.json().catch(() => ({}))
        throw new Error(err.detail || `${r.status} ${r.statusText}`)
      }
      return r.json()
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['session-status'] }),
  })
}

/**
 * SSE log stream consumer for the active scraper session.
 *
 * `resetKey` exists so callers can wipe the buffer when a new session
 * starts — pass `status?.started_at`. Without it, a fresh run shows the
 * previous run's tail until new lines push them out of the 1500-line
 * window. The reconnect happens on every `resetKey` change so the backend's
 * own in-memory deque doesn't replay stale lines either.
 */
export function useLogStream(active: boolean, resetKey?: string | null) {
  const [lines, setLines] = useState<string[]>([])
  const esRef = useRef<EventSource | null>(null)

  useEffect(() => {
    setLines([])
  }, [resetKey])

  useEffect(() => {
    if (!active) return
    const es = new EventSource('/api/sessions/logs/stream')
    esRef.current = es
    es.onmessage = (ev) => {
      setLines((prev) => {
        const next = [...prev, ev.data]
        return next.length > 1500 ? next.slice(next.length - 1500) : next
      })
    }
    es.onerror = () => { /* keep buffer; browser will retry */ }
    return () => { es.close(); esRef.current = null }
  }, [active, resetKey])

  const clear = () => setLines([])
  return { lines, clear }
}
