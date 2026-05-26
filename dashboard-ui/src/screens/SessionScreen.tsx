import { useEffect, useRef, useState } from 'react'
import { FiTrash2, FiPause, FiActivity } from 'react-icons/fi'
import { cn } from '@/lib/utils'
import { useLogStream, useSessionStatus } from '@/hooks/useSession'

export default function SessionScreen() {
  const { data: status } = useSessionStatus()
  const [autoscroll, setAutoscroll] = useState(true)
  // Tie the log buffer's identity to the active session so a new scrape
  // starts with an empty pane instead of inheriting the last run's tail.
  const { lines, clear } = useLogStream(true, status?.started_at ?? null)
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (autoscroll) endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [lines.length, autoscroll])

  const running = !!status?.running
  const paused = !!status?.paused
  // Backend emits explicit-UTC ISO strings (_utc_iso); render in the
  // operator's local tz. Previously sliced (11, 19) which displayed UTC
  // hours as if they were local — Header.tsx got it right, this screen
  // didn't. Same data, two answers — the visible inconsistency.
  const startedAtLocal = status?.started_at
    ? new Date(status.started_at).toLocaleTimeString(undefined, {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false,
      })
    : null

  return (
    <div className="p-4 md:p-6 space-y-4 h-full flex flex-col">
      <div>
        <h1 className="text-xl font-semibold flex items-center gap-2">
          <FiActivity className="h-5 w-5" /> Session
        </h1>
        <p className="text-sm text-zinc-500 dark:text-zinc-400">
          {running
            ? `${paused ? 'Paused' : 'Running'} · pid ${status?.pid} · started ${startedAtLocal ?? '—'}`
            : status?.exit_code != null
              ? `Idle · last exit ${status.exit_code}`
              : 'Idle'}
          <span className="ml-2 text-xs text-zinc-400">· controls in header</span>
        </p>
      </div>

      <div className="surface rounded-lg flex-1 flex flex-col overflow-hidden">
        <div className="px-3 py-2 border-b border-zinc-200 dark:border-zinc-800 flex items-center justify-between text-xs">
          <div className="flex items-center gap-2">
            <span
              className={cn(
                'h-2 w-2 rounded-full',
                paused
                  ? 'bg-orange-500 animate-pulse'
                  : running
                    ? 'bg-emerald-500 animate-pulse'
                    : 'bg-zinc-400',
              )}
            />
            <span className="text-zinc-500 dark:text-zinc-400">{lines.length} lines</span>
          </div>
          <div className="flex items-center gap-1">
            <button
              className="btn-ghost !py-1 !px-2"
              onClick={() => setAutoscroll((v) => !v)}
              title={autoscroll ? 'Pause auto-scroll' : 'Resume auto-scroll'}
            >
              <FiPause className="h-3.5 w-3.5" />
              {autoscroll ? 'Auto' : 'Paused'}
            </button>
            <button className="btn-ghost !py-1 !px-2" onClick={clear} title="Clear view">
              <FiTrash2 className="h-3.5 w-3.5" /> Clear
            </button>
          </div>
        </div>
        <div className="flex-1 overflow-auto bg-zinc-950 text-zinc-100 font-mono text-xs leading-relaxed p-3">
          {lines.length === 0 ? (
            <div className="text-zinc-500">Waiting for log output…</div>
          ) : (
            lines.map((l, i) => <div key={i} className="whitespace-pre-wrap">{l}</div>)
          )}
          <div ref={endRef} />
        </div>
      </div>
    </div>
  )
}
