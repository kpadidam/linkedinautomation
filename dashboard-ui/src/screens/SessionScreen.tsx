import { useEffect, useRef, useState } from 'react'
import { FiPlay, FiSquare, FiTrash2, FiPause, FiActivity } from 'react-icons/fi'
import { cn } from '@/lib/utils'
import { useLogStream, useSessionStatus, useStartSession, useStopSession } from '@/hooks/useSession'

export default function SessionScreen() {
  const { data: status } = useSessionStatus()
  const start = useStartSession()
  const stop = useStopSession()
  const [autoscroll, setAutoscroll] = useState(true)
  const { lines, clear } = useLogStream(true)
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (autoscroll) endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [lines.length, autoscroll])

  const running = !!status?.running

  return (
    <div className="p-4 md:p-6 space-y-4 h-full flex flex-col">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold flex items-center gap-2">
            <FiActivity className="h-5 w-5" /> Session
          </h1>
          <p className="text-sm text-zinc-500 dark:text-zinc-400">
            {running
              ? `Running · pid ${status?.pid} · started ${status?.started_at?.slice(11, 19)}`
              : status?.exit_code != null
                ? `Idle · last exit ${status.exit_code}`
                : 'Idle'}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {running ? (
            <button className="btn-danger" onClick={() => stop.mutate()} disabled={stop.isPending}>
              <FiSquare className="h-4 w-4" /> Stop session
            </button>
          ) : (
            <button className="btn-primary" onClick={() => start.mutate()} disabled={start.isPending}>
              <FiPlay className="h-4 w-4" /> Start session
            </button>
          )}
        </div>
      </div>

      <div className="surface rounded-lg flex-1 flex flex-col overflow-hidden">
        <div className="px-3 py-2 border-b border-zinc-200 dark:border-zinc-800 flex items-center justify-between text-xs">
          <div className="flex items-center gap-2">
            <span className={cn('h-2 w-2 rounded-full', running ? 'bg-emerald-500 animate-pulse' : 'bg-zinc-400')} />
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
