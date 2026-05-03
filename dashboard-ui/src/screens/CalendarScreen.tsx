import { useMemo, useState } from 'react'
import { FiChevronLeft, FiChevronRight, FiCalendar, FiBriefcase, FiTrash2 } from 'react-icons/fi'
import { useInterviews, useDeleteInterview } from '@/hooks/useInterviews'
import { useJobs } from '@/hooks/useJobs'
import { cn, statusColor } from '@/lib/utils'
import { JobDetailDrawer } from '@/features/jobs/JobDetailDrawer'

function startOfMonth(d: Date) { return new Date(d.getFullYear(), d.getMonth(), 1) }
function endOfMonth(d: Date) { return new Date(d.getFullYear(), d.getMonth() + 1, 0) }
function addDays(d: Date, n: number) { const x = new Date(d); x.setDate(x.getDate() + n); return x }
function ymd(d: Date) { return d.toISOString().slice(0, 10) }

export default function CalendarScreen() {
  const [cursor, setCursor] = useState(() => new Date())
  const [openId, setOpenId] = useState<string | null>(null)
  const { data: interviews = [] } = useInterviews()
  const { data: jobs = [] } = useJobs({ limit: 500 })
  const del = useDeleteInterview()

  const jobMap = useMemo(() => new Map(jobs.map((j) => [j.job_id, j])), [jobs])

  const monthStart = startOfMonth(cursor)
  const gridStart = addDays(monthStart, -((monthStart.getDay() + 6) % 7))
  const days = useMemo(() => Array.from({ length: 42 }, (_, i) => addDays(gridStart, i)), [gridStart])

  const eventsByDay = useMemo(() => {
    const map = new Map<string, typeof interviews>()
    for (const e of interviews) {
      const k = ymd(new Date(e.scheduled_at))
      const arr = map.get(k) || []
      arr.push(e)
      map.set(k, arr)
    }
    return map
  }, [interviews])

  const monthLabel = cursor.toLocaleDateString(undefined, { month: 'long', year: 'numeric' })
  const today = ymd(new Date())

  return (
    <div className="p-4 md:p-6 space-y-4 h-full flex flex-col">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold flex items-center gap-2"><FiCalendar /> Calendar</h1>
          <p className="text-sm text-zinc-500 dark:text-zinc-400">{interviews.length} interviews scheduled</p>
        </div>
        <div className="flex items-center gap-2">
          <button className="btn-ghost" onClick={() => setCursor(new Date(cursor.getFullYear(), cursor.getMonth() - 1, 1))}>
            <FiChevronLeft />
          </button>
          <div className="text-sm font-medium w-36 text-center">{monthLabel}</div>
          <button className="btn-ghost" onClick={() => setCursor(new Date(cursor.getFullYear(), cursor.getMonth() + 1, 1))}>
            <FiChevronRight />
          </button>
          <button className="btn-ghost" onClick={() => setCursor(new Date())}>Today</button>
        </div>
      </div>

      <div className="surface rounded-lg overflow-hidden flex-1 flex flex-col">
        <div className="grid grid-cols-7 text-xs uppercase tracking-wide text-zinc-500 dark:text-zinc-400 bg-zinc-50 dark:bg-zinc-900/60 border-b border-zinc-200 dark:border-zinc-800">
          {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map((d) => (
            <div key={d} className="px-2 py-2 text-center">{d}</div>
          ))}
        </div>
        <div className="grid grid-cols-7 flex-1 auto-rows-fr">
          {days.map((d, i) => {
            const inMonth = d.getMonth() === cursor.getMonth()
            const k = ymd(d)
            const events = eventsByDay.get(k) || []
            const isToday = k === today
            return (
              <div
                key={i}
                className={cn(
                  'border-r border-b border-zinc-200 dark:border-zinc-800 p-1.5 min-h-[96px] flex flex-col gap-1',
                  !inMonth && 'bg-zinc-50/60 dark:bg-zinc-900/30',
                  (i + 1) % 7 === 0 && 'border-r-0'
                )}
              >
                <div className={cn(
                  'text-xs tabular-nums w-6 h-6 flex items-center justify-center rounded-full',
                  isToday ? 'bg-brand-600 text-white' : 'text-zinc-500 dark:text-zinc-400'
                )}>
                  {d.getDate()}
                </div>
                <div className="space-y-0.5 overflow-hidden">
                  {events.slice(0, 3).map((e) => {
                    const job = jobMap.get(e.job_id)
                    return (
                      <button
                        key={e.id}
                        onClick={() => setOpenId(e.job_id)}
                        className={cn(
                          'w-full text-left px-1.5 py-0.5 rounded text-[10px] truncate hover:opacity-80',
                          statusColor(e.stage)
                        )}
                        title={`${e.stage} · ${job?.title || e.job_id}`}
                      >
                        {new Date(e.scheduled_at).toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })}{' '}
                        <span className="font-medium">{e.stage}</span>{' '}
                        <span className="opacity-80">{job?.company || '—'}</span>
                      </button>
                    )
                  })}
                  {events.length > 3 ? (
                    <div className="text-[10px] text-zinc-500">+{events.length - 3} more</div>
                  ) : null}
                </div>
              </div>
            )
          })}
        </div>
      </div>

      <div className="surface rounded-lg">
        <div className="px-4 py-3 border-b border-zinc-200 dark:border-zinc-800">
          <h2 className="text-sm font-medium">Upcoming</h2>
        </div>
        {interviews.length === 0 ? (
          <div className="p-6 text-sm text-zinc-500">No interviews scheduled. Schedule one from a job's detail panel.</div>
        ) : (
          <ul className="divide-y divide-zinc-100 dark:divide-zinc-800">
            {interviews.slice(0, 8).map((e) => {
              const job = jobMap.get(e.job_id)
              return (
                <li key={e.id} className="px-4 py-2 flex items-center gap-3 hover:bg-zinc-50 dark:hover:bg-zinc-800/40">
                  <div className="text-xs text-zinc-500 tabular-nums w-32">
                    {new Date(e.scheduled_at).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })}
                  </div>
                  <span className={cn('chip capitalize', statusColor(e.stage))}>{e.stage}</span>
                  <button onClick={() => setOpenId(e.job_id)} className="flex-1 text-left text-sm hover:underline truncate">
                    <FiBriefcase className="inline h-3 w-3 mr-1 text-zinc-400" />
                    {job?.title || e.job_id} <span className="text-zinc-500">· {job?.company || ''}</span>
                  </button>
                  <button className="btn-ghost !p-1" onClick={() => del.mutate(e.id)}>
                    <FiTrash2 className="h-3.5 w-3.5" />
                  </button>
                </li>
              )
            })}
          </ul>
        )}
      </div>
      <JobDetailDrawer jobId={openId} onClose={() => setOpenId(null)} />
    </div>
  )
}
