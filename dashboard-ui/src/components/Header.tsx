import { FiSun, FiMoon, FiPlay, FiSquare, FiAlertTriangle, FiRefreshCw, FiSkipForward } from 'react-icons/fi'
import { Link } from 'react-router-dom'
import { useTheme } from '@/hooks/useTheme'
import { useSessionStatus, useStartSession, useStopSession, useResetSession } from '@/hooks/useSession'
import { useSettingsDirty } from '@/lib/settingsDirty'
import { cn } from '@/lib/utils'

export function Header() {
  const { theme, toggle } = useTheme()
  const { data: status } = useSessionStatus()
  const start = useStartSession()
  const stop = useStopSession()
  const reset = useResetSession()
  const dirty = useSettingsDirty((s) => s.dirty)
  const running = !!status?.running
  const pending = status?.pending_progress ?? null
  const canResume = !running && !!pending

  const startLabel = canResume
    ? `Resume · ${pending!.completed_index + 1}/${pending!.total_categories}`
    : 'Start session'
  const startTitle = canResume
    ? `Resume from category ${pending!.completed_index + 2} of ${pending!.total_categories} (started ${new Date(pending!.started_at).toLocaleString()})`
    : 'Start a fresh scraping session'

  const handleReset = () => {
    if (!confirm('Discard saved progress and start the next run from scratch?')) return
    reset.mutate()
  }

  return (
    <header className="h-14 shrink-0 px-4 md:px-6 flex items-center justify-between border-b border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900">
      <Link to="/session" className="flex items-center gap-2 hover:opacity-80">
        <span
          className={cn(
            'h-2 w-2 rounded-full',
            running ? 'bg-emerald-500 animate-pulse' : canResume ? 'bg-amber-500' : 'bg-zinc-400'
          )}
        />
        <span className="text-sm text-zinc-600 dark:text-zinc-400">
          {running
            ? `Running · pid ${status?.pid}`
            : canResume
              ? `Paused · ${pending!.completed_index + 1}/${pending!.total_categories} done`
              : 'Idle'}
        </span>
      </Link>
      <div className="flex items-center gap-2">
        {dirty && running ? (
          <Link
            to="/session"
            className="inline-flex items-center gap-1.5 rounded-full border border-amber-400/60 bg-amber-50 px-3 py-1 text-xs font-medium text-amber-800 hover:bg-amber-100 dark:border-amber-500/40 dark:bg-amber-950/40 dark:text-amber-200 dark:hover:bg-amber-900/40"
            title="Settings changed since this session started. Restart to apply."
          >
            <FiAlertTriangle className="h-3.5 w-3.5" />
            Restart Session to apply settings
          </Link>
        ) : null}
        {running ? (
          <button className="btn-danger" onClick={() => stop.mutate()} disabled={stop.isPending}>
            <FiSquare className="h-4 w-4" /> Stop
          </button>
        ) : (
          <>
            <button
              className="btn-primary"
              onClick={() => start.mutate()}
              disabled={start.isPending}
              title={startTitle}
            >
              {canResume ? <FiSkipForward className="h-4 w-4" /> : <FiPlay className="h-4 w-4" />}
              {startLabel}
            </button>
            {canResume ? (
              <button
                className="btn-ghost"
                onClick={handleReset}
                disabled={reset.isPending}
                title="Discard saved progress and start fresh"
              >
                <FiRefreshCw className="h-4 w-4" />
                Reset
              </button>
            ) : null}
          </>
        )}
        <button className="btn-ghost" onClick={toggle} aria-label="Toggle theme">
          {theme === 'dark' ? <FiSun className="h-4 w-4" /> : <FiMoon className="h-4 w-4" />}
        </button>
      </div>
    </header>
  )
}
