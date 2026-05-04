import { FiSun, FiMoon, FiPlay, FiSquare, FiAlertTriangle } from 'react-icons/fi'
import { Link } from 'react-router-dom'
import { useTheme } from '@/hooks/useTheme'
import { useSessionStatus, useStartSession, useStopSession } from '@/hooks/useSession'
import { useSettingsDirty } from '@/lib/settingsDirty'
import { cn } from '@/lib/utils'

export function Header() {
  const { theme, toggle } = useTheme()
  const { data: status } = useSessionStatus()
  const start = useStartSession()
  const stop = useStopSession()
  const dirty = useSettingsDirty((s) => s.dirty)
  const running = !!status?.running

  return (
    <header className="h-14 shrink-0 px-4 md:px-6 flex items-center justify-between border-b border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900">
      <Link to="/session" className="flex items-center gap-2 hover:opacity-80">
        <span
          className={cn(
            'h-2 w-2 rounded-full',
            running ? 'bg-emerald-500 animate-pulse' : 'bg-zinc-400'
          )}
        />
        <span className="text-sm text-zinc-600 dark:text-zinc-400">
          {running ? `Running · pid ${status?.pid}` : 'Idle'}
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
          <button className="btn-primary" onClick={() => start.mutate()} disabled={start.isPending}>
            <FiPlay className="h-4 w-4" /> Start session
          </button>
        )}
        <button className="btn-ghost" onClick={toggle} aria-label="Toggle theme">
          {theme === 'dark' ? <FiSun className="h-4 w-4" /> : <FiMoon className="h-4 w-4" />}
        </button>
      </div>
    </header>
  )
}
