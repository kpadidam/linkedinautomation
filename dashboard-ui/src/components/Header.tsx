import { useEffect, useState } from 'react'
import {
  FiSun,
  FiMoon,
  FiPlay,
  FiPause,
  FiSquare,
  FiAlertTriangle,
  FiRefreshCw,
  FiSkipForward,
  FiClock,
  FiZap,
  FiSettings,
  FiCalendar,
} from 'react-icons/fi'
import { Link, NavLink } from 'react-router-dom'
import { useTheme } from '@/hooks/useTheme'
import {
  useSessionStatus,
  useStartSession,
  useStopSession,
  useResetSession,
  usePauseSession,
  useResumePausedSession,
} from '@/hooks/useSession'
import { useSetupStatus } from '@/hooks/useSetup'
import { useSettingsDirty } from '@/lib/settingsDirty'
import { cn } from '@/lib/utils'

/** Format seconds → "Xh Ym Zs" with sensible truncation. */
function fmtElapsed(totalSec: number): string {
  if (totalSec < 0 || !Number.isFinite(totalSec)) return '0s'
  const h = Math.floor(totalSec / 3600)
  const m = Math.floor((totalSec % 3600) / 60)
  const s = Math.floor(totalSec % 60)
  if (h > 0) return `${h}h ${m}m ${s}s`
  if (m > 0) return `${m}m ${s}s`
  return `${s}s`
}

/** Format ISO datetime → "14:03" (24h, local). */
function fmtClock(iso: string | null | undefined): string {
  if (!iso) return ''
  try {
    return new Date(iso).toLocaleTimeString(undefined, {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    })
  } catch {
    return ''
  }
}

export function Header() {
  const { theme, toggle } = useTheme()
  const { data: status } = useSessionStatus()
  const { data: setup } = useSetupStatus()
  const start = useStartSession()
  const stop = useStopSession()
  const reset = useResetSession()
  const pause = usePauseSession()
  const resumePaused = useResumePausedSession()
  const dirty = useSettingsDirty((s) => s.dirty)

  const running = !!status?.running
  const paused = !!status?.paused
  const pending = status?.pending_progress ?? null
  const canResumeFromCheckpoint = !running && !!pending
  const setupBlocked = !!setup && !setup.complete

  // Live ticker — drives both the running stopwatch and the idle
  // "next trigger in Xh Ym" countdown, so we tick whenever there's
  // something time-sensitive on screen.
  const hasNextTrigger = !!status?.next_trigger
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    if (!running && !hasNextTrigger) return
    const id = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(id)
  }, [running, hasNextTrigger])

  const startedAtMs = status?.started_at ? new Date(status.started_at).getTime() : null
  const pausedAtMs = status?.paused_at ? new Date(status.paused_at).getTime() : null
  const accumulatedPause = (status?.pause_duration_seconds || 0) * 1000
  // Active runtime = wall time since start — cumulative pause windows
  // — current pause window (if currently paused).
  const activeMs = startedAtMs
    ? now - startedAtMs - accumulatedPause - (paused && pausedAtMs ? now - pausedAtMs : 0)
    : 0
  const activeSec = Math.max(0, Math.floor(activeMs / 1000))

  const missingLabels = setup
    ? setup.items.filter((i) => !i.complete && !i.optional).map((i) => i.label)
    : []

  const startLabel = canResumeFromCheckpoint
    ? `Resume · ${pending!.completed_index + 1}/${pending!.total_categories}`
    : 'Start session'
  const startTitle = setupBlocked
    ? `Setup incomplete: ${missingLabels.join(' · ')}`
    : canResumeFromCheckpoint
      ? `Resume from category ${pending!.completed_index + 2} of ${pending!.total_categories} (started ${new Date(pending!.started_at).toLocaleString()})`
      : 'Start a fresh scraping session'

  const handleReset = () => {
    if (!confirm('Discard saved progress and start the next run from scratch?')) return
    reset.mutate()
  }

  // Status pill content varies by state. Color also conveys state at a glance:
  // green pulse = running, orange pulse = paused, amber = resumable (idle+ckpt),
  // gray = idle.
  let dotClass = 'bg-zinc-400'
  if (running && paused) dotClass = 'bg-orange-500 animate-pulse'
  else if (running) dotClass = 'bg-emerald-500 animate-pulse'
  else if (canResumeFromCheckpoint) dotClass = 'bg-amber-500'

  // Idle copy is trigger-aware: when auto-search is on we show a live
  // "next trigger in Xh Ym" countdown (re-derived each tick from now() vs
  // the server's `next_at` ISO so it stays accurate without polling).
  const trigger = status?.next_trigger ?? null
  let statusLine: React.ReactNode = 'Idle'
  if (running && paused) {
    statusLine = (
      <>
        Paused · started {fmtClock(status?.started_at)} ·{' '}
        <span className="font-mono tabular-nums">{fmtElapsed(activeSec)}</span> active
      </>
    )
  } else if (running) {
    statusLine = (
      <>
        Running · started {fmtClock(status?.started_at)} ·{' '}
        <span className="font-mono tabular-nums">{fmtElapsed(activeSec)}</span>
      </>
    )
  } else if (canResumeFromCheckpoint) {
    statusLine = (
      <>
        Resumable · {pending!.completed_index + 1}/{pending!.total_categories} done ·
        started {fmtClock(pending!.started_at)}
      </>
    )
  } else if (trigger) {
    const secsUntil = Math.max(
      0,
      Math.floor((new Date(trigger.next_at).getTime() - now) / 1000),
    )
    // Render the cadence in the most readable unit: <60m as "Nm",
    // hour-multiples as "Nh", anything else as "Xh Ym".
    const m = trigger.frequency_minutes
    let cadence: string
    if (m < 60) cadence = `${m}m`
    else if (m % 60 === 0) cadence = `${m / 60}h`
    else cadence = `${Math.floor(m / 60)}h ${m % 60}m`
    statusLine = (
      <>
        <FiZap className="h-3.5 w-3.5 opacity-70 shrink-0" />
        Trigger every {cadence} · next in{' '}
        <span className="font-mono tabular-nums">{fmtElapsed(secsUntil)}</span>
      </>
    )
  } else {
    statusLine = 'Trigger: manual only'
  }

  return (
    <header className="h-14 shrink-0 px-4 md:px-6 flex items-center justify-between border-b border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900">
      <Link to="/session" className="flex items-center gap-2 hover:opacity-80 min-w-0">
        <span className={cn('h-2 w-2 rounded-full shrink-0', dotClass)} />
        <span className="text-sm text-zinc-600 dark:text-zinc-400 truncate flex items-center gap-1">
          {running ? <FiClock className="h-3.5 w-3.5 opacity-60 shrink-0" /> : null}
          {statusLine}
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
          <>
            {paused ? (
              <button
                className="btn-primary"
                onClick={() => resumePaused.mutate()}
                disabled={resumePaused.isPending}
                title="Resume the paused scraper subprocess"
              >
                <FiPlay className="h-4 w-4" /> Resume
              </button>
            ) : (
              <button
                className="btn-ghost"
                onClick={() => pause.mutate()}
                disabled={pause.isPending}
                title="Freeze the scraper in place (SIGSTOP). Best for short interruptions; long pauses risk LinkedIn cookie expiry."
              >
                <FiPause className="h-4 w-4" /> Pause
              </button>
            )}
            <button
              className="btn-danger"
              onClick={() => stop.mutate()}
              disabled={stop.isPending}
              title="Stop the run. Completed categories are preserved as a checkpoint."
            >
              <FiSquare className="h-4 w-4" /> Stop
            </button>
          </>
        ) : (
          <>
            {setupBlocked ? (
              <Link
                to="/setup"
                className="inline-flex items-center gap-1.5 rounded-full border border-amber-400/60 bg-amber-50 px-3 py-1.5 text-sm font-medium text-amber-900 hover:bg-amber-100 dark:border-amber-500/40 dark:bg-amber-950/40 dark:text-amber-200 dark:hover:bg-amber-900/40"
                title={startTitle}
              >
                <FiAlertTriangle className="h-4 w-4" />
                Finish setup
              </Link>
            ) : null}
            <button
              className="btn-primary"
              onClick={() => start.mutate()}
              disabled={start.isPending || setupBlocked}
              title={startTitle}
            >
              {canResumeFromCheckpoint ? (
                <FiSkipForward className="h-4 w-4" />
              ) : (
                <FiPlay className="h-4 w-4" />
              )}
              {startLabel}
            </button>
            {canResumeFromCheckpoint ? (
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
        <span className="w-px h-6 bg-zinc-200 dark:bg-zinc-800 mx-1" aria-hidden />
        <NavLink
          to="/calendar"
          className={({ isActive }) =>
            cn(
              'inline-flex items-center justify-center h-8 w-8 rounded-md transition-colors',
              isActive
                ? 'bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900'
                : 'text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800 hover:text-zinc-900 dark:hover:text-zinc-50',
            )
          }
          aria-label="Calendar"
          title="Calendar"
        >
          <FiCalendar className="h-4 w-4" />
        </NavLink>
        <NavLink
          to="/settings"
          className={({ isActive }) =>
            cn(
              'inline-flex items-center justify-center h-8 w-8 rounded-md transition-colors',
              isActive
                ? 'bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900'
                : 'text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800 hover:text-zinc-900 dark:hover:text-zinc-50',
            )
          }
          aria-label="Settings"
          title="Settings"
        >
          <FiSettings className="h-4 w-4" />
        </NavLink>
        <button
          className="btn-ghost !p-1.5"
          onClick={toggle}
          aria-label="Toggle theme"
          title="Toggle theme"
        >
          {theme === 'dark' ? <FiSun className="h-4 w-4" /> : <FiMoon className="h-4 w-4" />}
        </button>
      </div>
    </header>
  )
}
