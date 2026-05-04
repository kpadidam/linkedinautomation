import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  FiInbox,
  FiBookmark,
  FiSend,
  FiCalendar,
  FiPercent,
  FiArrowRight,
  FiActivity,
  FiCheckCircle,
  FiAlertCircle,
  FiPlay,
  FiFileText,
} from 'react-icons/fi'
import { useJobs, useStatistics, useSearches } from '@/hooks/useJobs'
import { useFollowups } from '@/hooks/useInterviews'
import { useSettings } from '@/hooks/useSettings'
import { useSetupStatus } from '@/hooks/useSetup'
import { StatCard } from '@/components/StatCard'
import { SetupBanner } from '@/components/SetupBanner'
import { JobDetailDrawer } from '@/features/jobs/JobDetailDrawer'
import { PIPELINE_STAGES } from '@/lib/types'
import { cn, formatRelative, nextActionFor, scoreColor, statusColor, statusLabel } from '@/lib/utils'

const NEW_THRESHOLD_HOURS = 24
const HIGH_MATCH = 80

export default function DashboardScreen() {
  const navigate = useNavigate()
  const { data: stats } = useStatistics()
  const { data: searches = [] } = useSearches(3)
  const { data: jobs = [] } = useJobs({ limit: 500 })
  const { data: followups = [] } = useFollowups()
  const { data: settings } = useSettings()
  const { data: setup } = useSetupStatus()
  const matchingEnabled = settings?.enable_resume_matching ?? true
  const [openId, setOpenId] = useState<string | null>(null)

  // First-run auto-redirect: when ALL required setup items are missing
  // (fresh clone), bounce to /setup. Use sessionStorage so we only redirect
  // once per browser session — user can still navigate back to / manually.
  useEffect(() => {
    if (!setup) return
    const required = setup.items.filter((i) => !i.optional)
    const allEmpty = required.every((i) => !i.complete)
    if (!allEmpty) return
    if (typeof window === 'undefined') return
    if (sessionStorage.getItem('setup-redirect-done') === '1') return
    sessionStorage.setItem('setup-redirect-done', '1')
    navigate('/setup', { replace: true })
  }, [setup, navigate])

  const counts = useMemo(() => {
    const c: Record<string, number> = { new: 0, saved: 0, tailoring_resume: 0, applied: 0, recruiter_screen: 0, technical_interview: 0, final: 0, offer: 0, rejected: 0 }
    for (const j of jobs) {
      const raw = (j.status as string) || 'new'
      const k = raw === 'interviewing' ? 'recruiter_screen' : raw
      if (k in c) c[k]++
    }
    return c
  }, [jobs])

  const newRecent = useMemo(() => {
    const cutoff = Date.now() - NEW_THRESHOLD_HOURS * 3600_000
    return jobs.filter((j) => {
      const t = new Date(j.scraped_at || 0).getTime()
      const status = (j.status as string) || 'new'
      return status === 'new' && t >= cutoff
    }).length
  }, [jobs])

  const bestNewMatches = useMemo(
    () =>
      jobs
        .filter((j) => ((j.status as string) || 'new') === 'new')
        .sort((a, b) => (b.resume_match_score ?? 0) - (a.resume_match_score ?? 0))
        .slice(0, 5),
    [jobs]
  )

  const upcomingFollowups = useMemo(() => {
    const now = Date.now()
    return followups
      .filter((f) => !f.done)
      .map((f) => ({ ...f, due: new Date(f.due_at).getTime() }))
      .sort((a, b) => a.due - b.due)
      .slice(0, 5)
      .map((f) => ({ ...f, overdue: f.due < now }))
  }, [followups])

  const todaysPlan = useMemo(() => {
    const items: { icon: any; label: string; to: string; tone: string }[] = []
    if (newRecent > 0) {
      items.push({
        icon: FiInbox,
        label: `Review ${newRecent} new ${newRecent === 1 ? 'job' : 'jobs'}`,
        to: '/review-queue',
        tone: 'text-brand-600',
      })
    }
    if (counts.tailoring_resume > 0) {
      items.push({
        icon: FiFileText,
        label: `Tailor resume for ${counts.tailoring_resume} role${counts.tailoring_resume === 1 ? '' : 's'}`,
        to: '/pipeline',
        tone: 'text-cyan-600',
      })
    }
    const overdue = upcomingFollowups.filter((f) => f.overdue).length
    if (overdue > 0) {
      items.push({
        icon: FiAlertCircle,
        label: `Catch up on ${overdue} overdue follow-up${overdue === 1 ? '' : 's'}`,
        to: '/calendar',
        tone: 'text-rose-600',
      })
    }
    const interviews = counts.recruiter_screen + counts.technical_interview + counts.final
    if (interviews > 0) {
      items.push({
        icon: FiCalendar,
        label: `Prep for ${interviews} active interview${interviews === 1 ? '' : 's'}`,
        to: '/calendar',
        tone: 'text-violet-600',
      })
    }
    if (items.length === 0) {
      items.push({
        icon: FiPlay,
        label: 'Run a session to discover new jobs',
        to: '/session',
        tone: 'text-emerald-600',
      })
    }
    return items
  }, [counts, newRecent, upcomingFollowups])

  const activePipeline =
    counts.saved + counts.tailoring_resume + counts.applied + counts.recruiter_screen + counts.technical_interview + counts.final + counts.offer

  const lastSearch = searches[0]
  const sessionHealthy = !!lastSearch && (lastSearch.status === 'completed' || lastSearch.status === 'success')

  return (
    <div className="p-4 md:p-6 space-y-6">
      <SetupBanner />
      <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">Job Search Command Center</h1>
          <p className="text-sm text-zinc-500 dark:text-zinc-400">
            {newRecent > 0
              ? `${newRecent} new high-potential roles waiting for review.`
              : 'No new jobs in the last 24h — start a session to discover more.'}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link to="/session" className="btn-primary">
            <FiPlay className="h-4 w-4" /> Start Session
          </Link>
          <Link to="/review-queue" className="btn-ghost">
            <FiInbox className="h-4 w-4" /> Review Queue
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        <StatCard label="New jobs" value={newRecent} icon={FiInbox} hint="last 24h" />
        {matchingEnabled ? (
          <StatCard label="High matches" value={stats?.high_match_jobs ?? 0} icon={FiActivity} hint={`≥ ${HIGH_MATCH}%`} />
        ) : null}
        <StatCard label="Saved" value={counts.saved} icon={FiBookmark} />
        <StatCard label="Applied" value={counts.applied} icon={FiSend} />
        <StatCard
          label="Interviews"
          value={counts.recruiter_screen + counts.technical_interview + counts.final}
          icon={FiCalendar}
        />
        {matchingEnabled ? (
          <StatCard
            label="Avg match"
            value={stats?.average_match_score != null ? `${Math.round(stats.average_match_score)}%` : '—'}
            icon={FiPercent}
          />
        ) : null}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <section className="surface rounded-lg p-4 lg:col-span-1">
          <h2 className="text-sm font-medium mb-3">Today's Action Plan</h2>
          <ul className="space-y-2">
            {todaysPlan.map((item, i) => {
              const Icon = item.icon
              return (
                <li key={i}>
                  <Link
                    to={item.to}
                    className="group flex items-center justify-between gap-2 rounded-md border border-zinc-200 dark:border-zinc-800 px-3 py-2 hover:bg-zinc-50 dark:hover:bg-zinc-800/40"
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      <Icon className={cn('h-4 w-4 shrink-0', item.tone)} />
                      <span className="text-sm truncate">{item.label}</span>
                    </div>
                    <FiArrowRight className="h-4 w-4 text-zinc-400 group-hover:text-zinc-600 dark:group-hover:text-zinc-200" />
                  </Link>
                </li>
              )
            })}
          </ul>
        </section>

        <section className="surface rounded-lg p-4 lg:col-span-2">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-medium">Best New Matches</h2>
            <Link to="/review-queue" className="text-xs text-brand-600 hover:underline">
              See all →
            </Link>
          </div>
          {!matchingEnabled ? (
            <div className="text-sm text-zinc-500 py-6 text-center">
              Enable matching in{' '}
              <Link to="/settings/system" className="text-brand-600 hover:underline">
                Settings → System
              </Link>{' '}
              to see matches.
            </div>
          ) : bestNewMatches.length === 0 ? (
            <div className="text-sm text-zinc-500 py-6 text-center">No new jobs to review.</div>
          ) : (
            <ul className="divide-y divide-zinc-100 dark:divide-zinc-800">
              {bestNewMatches.map((j) => (
                <li key={j.job_id}>
                  <button
                    onClick={() => setOpenId(j.job_id)}
                    className="w-full flex items-center justify-between gap-3 py-2 text-left hover:bg-zinc-50 dark:hover:bg-zinc-800/40 rounded-md px-2 -mx-2"
                  >
                    <div className="min-w-0">
                      <div className="text-sm font-medium truncate">{j.title}</div>
                      <div className="text-xs text-zinc-500 dark:text-zinc-400 truncate">
                        {j.company}
                        {j.location ? ` · ${j.location}` : ''}
                      </div>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      {matchingEnabled && j.resume_match_score != null ? (
                        <span className={cn('chip text-xs', scoreColor(j.resume_match_score))}>
                          {Math.round(j.resume_match_score)}%
                        </span>
                      ) : null}
                      <span className="hidden md:inline text-[11px] text-zinc-500 dark:text-zinc-400">
                        {nextActionFor(j.status)}
                      </span>
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <section className="surface rounded-lg p-4 lg:col-span-2">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-medium">Pipeline Funnel</h2>
            <Link to="/pipeline" className="text-xs text-brand-600 hover:underline">
              Open pipeline →
            </Link>
          </div>
          {activePipeline === 0 ? (
            <div className="text-sm text-zinc-500 py-6 text-center">
              No active opportunities yet — save jobs from the Review Queue.
            </div>
          ) : (
            <div className="space-y-2">
              {PIPELINE_STAGES.map((s) => {
                const n = counts[s.id] || 0
                const pct = activePipeline > 0 ? (n / activePipeline) * 100 : 0
                return (
                  <div key={s.id} className="flex items-center gap-3 text-sm">
                    <div className="w-36 shrink-0">
                      <span className={cn('chip text-[11px]', statusColor(s.id))}>{s.label}</span>
                    </div>
                    <div className="flex-1 h-2 rounded bg-zinc-100 dark:bg-zinc-800 overflow-hidden">
                      <div
                        className="h-full bg-brand-500"
                        style={{ width: `${Math.max(pct, n > 0 ? 4 : 0)}%` }}
                      />
                    </div>
                    <div className="w-10 text-right text-xs tabular-nums text-zinc-600 dark:text-zinc-400">
                      {n}
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </section>

        <section className="surface rounded-lg p-4 lg:col-span-1">
          <h2 className="text-sm font-medium mb-3">Session Health</h2>
          {!lastSearch ? (
            <div className="text-sm text-zinc-500">No sessions yet.</div>
          ) : (
            <div className="space-y-3 text-sm">
              <div className="flex items-center gap-2">
                {sessionHealthy ? (
                  <FiCheckCircle className="h-4 w-4 text-emerald-500" />
                ) : (
                  <FiAlertCircle className="h-4 w-4 text-amber-500" />
                )}
                <span className="capitalize">{lastSearch.status || 'unknown'}</span>
              </div>
              <Row k="Last run" v={formatRelative(lastSearch.started_at)} />
              <Row k="Keywords" v={lastSearch.keywords || '—'} />
              <Row k="Location" v={lastSearch.location || '—'} />
              <Row k="Scraped" v={String(lastSearch.jobs_scraped ?? 0)} />
              <Row k="Matched" v={String(lastSearch.jobs_matched ?? 0)} />
              <Link to="/session" className="btn-ghost mt-2 w-full justify-center">
                <FiActivity className="h-4 w-4" /> Session log
              </Link>
            </div>
          )}
        </section>
      </div>

      <section className="surface rounded-lg p-4">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-medium">Upcoming Follow-ups</h2>
          <Link to="/calendar" className="text-xs text-brand-600 hover:underline">
            Open calendar →
          </Link>
        </div>
        {upcomingFollowups.length === 0 ? (
          <div className="text-sm text-zinc-500 py-4 text-center">
            No follow-ups scheduled. Add one from a job's detail panel.
          </div>
        ) : (
          <ul className="divide-y divide-zinc-100 dark:divide-zinc-800">
            {upcomingFollowups.map((f) => {
              const job = jobs.find((j) => j.job_id === f.job_id)
              return (
                <li key={f.id}>
                  <button
                    onClick={() => setOpenId(f.job_id)}
                    className="w-full flex items-center justify-between gap-3 py-2 text-left hover:bg-zinc-50 dark:hover:bg-zinc-800/40 rounded-md px-2 -mx-2"
                  >
                    <div className="min-w-0">
                      <div className="text-sm font-medium truncate">
                        {job ? `${job.title} · ${job.company}` : f.job_id}
                      </div>
                      <div className="text-xs text-zinc-500 dark:text-zinc-400 truncate">
                        {f.note || 'Follow up'}
                      </div>
                    </div>
                    <div className="text-right shrink-0">
                      <div
                        className={cn(
                          'text-xs font-medium',
                          f.overdue ? 'text-rose-600' : 'text-zinc-700 dark:text-zinc-300'
                        )}
                      >
                        {new Date(f.due_at).toLocaleString(undefined, {
                          month: 'short',
                          day: 'numeric',
                          hour: 'numeric',
                          minute: '2-digit',
                        })}
                      </div>
                      <div className="text-[10px] text-zinc-500 dark:text-zinc-400">
                        {f.overdue ? 'overdue' : formatRelative(f.due_at)}
                        {job?.status ? ` · ${statusLabel(job.status)}` : ''}
                      </div>
                    </div>
                  </button>
                </li>
              )
            })}
          </ul>
        )}
      </section>

      <JobDetailDrawer jobId={openId} onClose={() => setOpenId(null)} />
    </div>
  )
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="text-xs text-zinc-500 dark:text-zinc-400">{k}</span>
      <span className="text-xs text-zinc-700 dark:text-zinc-300 truncate max-w-[160px]">{v}</span>
    </div>
  )
}
