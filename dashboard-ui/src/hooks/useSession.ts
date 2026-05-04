import { useEffect, useRef, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { clearSettingsDirty } from '@/lib/settingsDirty'

export interface SessionStatus {
  running: boolean
  pid: number | null
  started_at: string | null
  exit_code: number | null
  log_count: number
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
      return r.json()
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['session-status'] }),
  })
}

export function useLogStream(active: boolean) {
  const [lines, setLines] = useState<string[]>([])
  const esRef = useRef<EventSource | null>(null)

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
  }, [active])

  const clear = () => setLines([])
  return { lines, clear }
}
