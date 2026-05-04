import { useEffect, useMemo, useState } from 'react'
import {
  FiChevronLeft,
  FiChevronRight,
  FiCalendar,
  FiBriefcase,
  FiPlus,
  FiEdit2,
} from 'react-icons/fi'
import { useInterviews } from '@/hooks/useInterviews'
import { useJobs } from '@/hooks/useJobs'
import { cn, companyColor } from '@/lib/utils'
import {
  ScheduleInterviewModal,
  stageLabel,
} from '@/features/interviews/ScheduleInterviewModal'
import type { Interview } from '@/lib/types.interviews'
import { TimeGridView } from './calendar/TimeGridView'

type CalendarView = 'day' | 'week' | 'month'

const VIEW_STORAGE_KEY = 'calendar.view'

function readStoredView(): CalendarView {
  if (typeof window === 'undefined') return 'month'
  const v = window.localStorage.getItem(VIEW_STORAGE_KEY)
  return v === 'day' || v === 'week' || v === 'month' ? v : 'month'
}

function startOfMonth(d: Date) {
  return new Date(d.getFullYear(), d.getMonth(), 1)
}
function startOfWeek(d: Date) {
  const x = new Date(d)
  const dow = (x.getDay() + 6) % 7 // Mon=0
  x.setDate(x.getDate() - dow)
  x.setHours(0, 0, 0, 0)
  return x
}
function addDays(d: Date, n: number) {
  const x = new Date(d)
  x.setDate(x.getDate() + n)
  return x
}
function ymd(d: Date) {
  return d.toISOString().slice(0, 10)
}
function fmtTime(d: Date) {
  return d.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })
}

type ModalState =
  | { kind: 'closed' }
  | { kind: 'create'; date?: Date }
  | { kind: 'edit'; interview: Interview }

export default function CalendarScreen() {
  const [view, setViewState] = useState<CalendarView>(readStoredView)
  const [cursor, setCursor] = useState(() => new Date())
  const [modal, setModal] = useState<ModalState>({ kind: 'closed' })
  const [now, setNow] = useState(() => new Date())
  const { data: interviews = [] } = useInterviews()
  const { data: jobs = [] } = useJobs({ limit: 500 })

  const setView = (v: CalendarView) => {
    setViewState(v)
    try {
      window.localStorage.setItem(VIEW_STORAGE_KEY, v)
    } catch {
      // storage may be unavailable; non-fatal
    }
  }

  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 60_000)
    return () => clearInterval(id)
  }, [])

  const jobMap = useMemo(() => new Map(jobs.map((j) => [j.job_id, j])), [jobs])

  const sortedByJob = useMemo(() => {
    const m = new Map<string, Interview[]>()
    for (const e of interviews) {
      const arr = m.get(e.job_id) || []
      arr.push(e)
      m.set(e.job_id, arr)
    }
    for (const [, arr] of m) {
      arr.sort(
        (a, b) =>
          new Date(a.scheduled_at).getTime() - new Date(b.scheduled_at).getTime(),
      )
    }
    return m
  }, [interviews])

  const roundFor = (e: Interview): number => {
    const arr = sortedByJob.get(e.job_id) || []
    const idx = arr.findIndex((x) => x.id === e.id)
    return idx >= 0 ? idx + 1 : 1
  }

  const eventsByDay = useMemo(() => {
    const map = new Map<string, Interview[]>()
    for (const e of interviews) {
      const k = ymd(new Date(e.scheduled_at))
      const arr = map.get(k) || []
      arr.push(e)
      map.set(k, arr)
    }
    for (const [, arr] of map) {
      arr.sort(
        (a, b) =>
          new Date(a.scheduled_at).getTime() - new Date(b.scheduled_at).getTime(),
      )
    }
    return map
  }, [interviews])

  // Days visible in the current view
  const visibleDays = useMemo(() => {
    if (view === 'day') return [new Date(cursor)]
    if (view === 'week') {
      const ws = startOfWeek(cursor)
      return Array.from({ length: 7 }, (_, i) => addDays(ws, i))
    }
    // month → 6 weeks starting Mon, anchored to month
    const monthStart = startOfMonth(cursor)
    const gridStart = addDays(monthStart, -((monthStart.getDay() + 6) % 7))
    return Array.from({ length: 42 }, (_, i) => addDays(gridStart, i))
  }, [view, cursor])

  // Header label
  const periodLabel = useMemo(() => {
    if (view === 'day') {
      return cursor.toLocaleDateString(undefined, {
        weekday: 'short',
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      })
    }
    if (view === 'week') {
      const ws = startOfWeek(cursor)
      const we = addDays(ws, 6)
      const sameMonth = ws.getMonth() === we.getMonth()
      const sameYear = ws.getFullYear() === we.getFullYear()
      const monthFmt: Intl.DateTimeFormatOptions = { month: 'short' }
      const dayFmt: Intl.DateTimeFormatOptions = { day: 'numeric' }
      const yearFmt: Intl.DateTimeFormatOptions = { year: 'numeric' }
      if (sameMonth) {
        return `${ws.toLocaleDateString(undefined, monthFmt)} ${ws.getDate()} — ${we.getDate()}, ${ws.toLocaleDateString(undefined, yearFmt)}`
      }
      if (sameYear) {
        return `${ws.toLocaleDateString(undefined, { ...monthFmt, ...dayFmt })} — ${we.toLocaleDateString(undefined, { ...monthFmt, ...dayFmt })}, ${ws.toLocaleDateString(undefined, yearFmt)}`
      }
      return `${ws.toLocaleDateString(undefined, { ...monthFmt, ...dayFmt, ...yearFmt })} — ${we.toLocaleDateString(undefined, { ...monthFmt, ...dayFmt, ...yearFmt })}`
    }
    return cursor.toLocaleDateString(undefined, { month: 'long', year: 'numeric' })
  }, [view, cursor])

  const stepCursor = (dir: -1 | 1) => {
    if (view === 'day') {
      setCursor((c) => addDays(c, dir))
    } else if (view === 'week') {
      setCursor((c) => addDays(c, dir * 7))
    } else {
      setCursor((c) => new Date(c.getFullYear(), c.getMonth() + dir, 1))
    }
  }

  const today = ymd(new Date())

  const upcoming = useMemo(
    () =>
      [...interviews]
        .filter((e) => new Date(e.scheduled_at).getTime() >= Date.now() - 86400_000)
        .sort(
          (a, b) =>
            new Date(a.scheduled_at).getTime() - new Date(b.scheduled_at).getTime(),
        )
        .slice(0, 8),
    [interviews],
  )

  const companies = useMemo(() => {
    const seen = new Map<string, number>()
    for (const e of interviews) {
      const company = jobMap.get(e.job_id)?.company
      if (!company) continue
      seen.set(company, (seen.get(company) || 0) + 1)
    }
    return [...seen.entries()].sort((a, b) => b[1] - a[1])
  }, [interviews, jobMap])

  const openCreate = (date?: Date) => setModal({ kind: 'create', date })
  const openEdit = (interview: Interview) => setModal({ kind: 'edit', interview })

  return (
    <div className="p-4 md:p-6 space-y-4 h-full flex flex-col min-h-0">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h1 className="text-xl font-semibold flex items-center gap-2">
            <FiCalendar /> Calendar
          </h1>
          <p className="text-sm text-zinc-500 dark:text-zinc-400">
            {interviews.length} interviews scheduled · click any{' '}
            {view === 'month' ? 'day' : 'slot'} to add a round
          </p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <ViewSwitcher view={view} onChange={setView} />
          <div className="flex items-center gap-1">
            <button
              className="btn-ghost"
              onClick={() => stepCursor(-1)}
              aria-label={`Previous ${view}`}
            >
              <FiChevronLeft />
            </button>
            <div className="text-sm font-medium min-w-[180px] text-center px-2">
              {periodLabel}
            </div>
            <button
              className="btn-ghost"
              onClick={() => stepCursor(1)}
              aria-label={`Next ${view}`}
            >
              <FiChevronRight />
            </button>
          </div>
          <button className="btn-ghost" onClick={() => setCursor(new Date())}>
            Today
          </button>
          <button className="btn-primary" onClick={() => openCreate()}>
            <FiPlus className="h-4 w-4" /> Add interview
          </button>
        </div>
      </div>

      {companies.length > 0 ? (
        <div className="surface rounded-lg px-4 py-2 flex items-center gap-3 flex-wrap">
          <span className="text-[11px] uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
            Companies
          </span>
          {companies.map(([company, count]) => {
            const c = companyColor(company)
            return (
              <span
                key={company}
                className="inline-flex items-center gap-1.5 text-xs"
                title={`${count} interview${count === 1 ? '' : 's'}`}
              >
                <span className={cn('h-2.5 w-2.5 rounded-full', c.dot)} />
                <span className="text-zinc-700 dark:text-zinc-300">{company}</span>
                <span className="text-zinc-500 tabular-nums">{count}</span>
              </span>
            )
          })}
        </div>
      ) : null}

      {view === 'month' ? (
        <MonthGrid
          days={visibleDays}
          cursor={cursor}
          today={today}
          eventsByDay={eventsByDay}
          jobMap={jobMap}
          roundFor={roundFor}
          now={now}
          onCreate={openCreate}
          onEdit={openEdit}
        />
      ) : (
        <TimeGridView
          days={visibleDays}
          interviews={interviews}
          jobMap={jobMap}
          roundFor={roundFor}
          onCreate={openCreate}
          onEdit={openEdit}
        />
      )}

      <div className="surface rounded-lg">
        <div className="px-4 py-3 border-b border-zinc-200 dark:border-zinc-800 flex items-center justify-between">
          <h2 className="text-sm font-medium">Upcoming</h2>
          <button className="btn-ghost text-xs" onClick={() => openCreate()}>
            <FiPlus className="h-3 w-3" /> Add
          </button>
        </div>
        {upcoming.length === 0 ? (
          <div className="p-6 text-sm text-zinc-500">
            No upcoming interviews. Click a {view === 'month' ? 'day' : 'time slot'}{' '}
            above or hit "Add interview" to schedule one.
          </div>
        ) : (
          <ul className="divide-y divide-zinc-100 dark:divide-zinc-800">
            {upcoming.map((e) => {
              const job = jobMap.get(e.job_id)
              const round = roundFor(e)
              const c = companyColor(job?.company)
              return (
                <li
                  key={e.id}
                  className="px-4 py-2 flex items-center gap-3 hover:bg-zinc-50 dark:hover:bg-zinc-800/40 cursor-pointer"
                  onClick={() => openEdit(e)}
                >
                  <span className={cn('h-7 w-1 rounded-full shrink-0', c.bgSolid)} />
                  <span className="font-mono text-xs text-zinc-500 w-6 shrink-0">
                    R{round}
                  </span>
                  <div className="text-xs text-zinc-500 tabular-nums w-32 shrink-0">
                    {new Date(e.scheduled_at).toLocaleString(undefined, {
                      month: 'short',
                      day: 'numeric',
                      hour: 'numeric',
                      minute: '2-digit',
                    })}
                  </div>
                  <span
                    className={cn(
                      'inline-flex items-center rounded-md px-2 py-0.5 text-[11px] font-medium border-l-2',
                      c.bg,
                      c.border,
                      c.text,
                    )}
                  >
                    {stageLabel(e.stage)}
                  </span>
                  <button
                    className="flex-1 text-left text-sm hover:underline truncate"
                    onClick={(ev) => {
                      ev.stopPropagation()
                      openEdit(e)
                    }}
                  >
                    <FiBriefcase className="inline h-3 w-3 mr-1 text-zinc-400" />
                    {job?.title || e.job_id}{' '}
                    <span className="text-zinc-500">· {job?.company || ''}</span>
                  </button>
                  <button
                    className="btn-ghost !p-1"
                    onClick={(ev) => {
                      ev.stopPropagation()
                      openEdit(e)
                    }}
                    aria-label="Edit"
                  >
                    <FiEdit2 className="h-3.5 w-3.5" />
                  </button>
                </li>
              )
            })}
          </ul>
        )}
      </div>

      <ScheduleInterviewModal
        open={modal.kind !== 'closed'}
        onClose={() => setModal({ kind: 'closed' })}
        jobId={modal.kind === 'edit' ? modal.interview.job_id : null}
        editing={modal.kind === 'edit' ? modal.interview : null}
        initialDate={modal.kind === 'create' ? modal.date : undefined}
        jobs={jobs}
      />
    </div>
  )
}

function ViewSwitcher({
  view,
  onChange,
}: {
  view: CalendarView
  onChange: (v: CalendarView) => void
}) {
  const opts: CalendarView[] = ['day', 'week', 'month']
  return (
    <div className="inline-flex rounded-md border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900 p-0.5 text-sm">
      {opts.map((o) => (
        <button
          key={o}
          type="button"
          onClick={() => onChange(o)}
          className={cn(
            'px-3 py-1 rounded capitalize transition-colors',
            view === o
              ? 'bg-white dark:bg-zinc-800 text-zinc-900 dark:text-zinc-50 shadow-sm'
              : 'text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-200',
          )}
        >
          {o}
        </button>
      ))}
    </div>
  )
}

interface MonthGridProps {
  days: Date[]
  cursor: Date
  today: string
  eventsByDay: Map<string, Interview[]>
  jobMap: Map<string, import('@/lib/types').Job>
  roundFor: (e: Interview) => number
  now: Date
  onCreate: (date: Date) => void
  onEdit: (e: Interview) => void
}

function MonthGrid({
  days,
  cursor,
  today,
  eventsByDay,
  jobMap,
  roundFor,
  now,
  onCreate,
  onEdit,
}: MonthGridProps) {
  return (
    <div className="surface rounded-lg overflow-hidden flex-1 flex flex-col">
      <div className="grid grid-cols-7 text-xs uppercase tracking-wide text-zinc-500 dark:text-zinc-400 bg-zinc-50 dark:bg-zinc-900/60 border-b border-zinc-200 dark:border-zinc-800">
        {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map((d) => (
          <div key={d} className="px-2 py-2 text-center">
            {d}
          </div>
        ))}
      </div>
      <div className="grid grid-cols-7 flex-1 auto-rows-fr">
        {days.map((d, i) => {
          const inMonth = d.getMonth() === cursor.getMonth()
          const k = ymd(d)
          const events = eventsByDay.get(k) || []
          const isToday = k === today
          const isWeekend = d.getDay() === 0 || d.getDay() === 6
          return (
            <div
              key={i}
              className={cn(
                'group relative border-r border-b border-zinc-200 dark:border-zinc-800 p-1.5 min-h-[110px] flex flex-col gap-1.5 cursor-pointer transition-colors',
                inMonth
                  ? 'bg-white dark:bg-zinc-900'
                  : 'bg-zinc-50/80 dark:bg-zinc-950/60 text-zinc-400',
                !isToday && 'hover:bg-zinc-50 dark:hover:bg-zinc-900/60',
                isWeekend && inMonth && !isToday && 'bg-zinc-50/60 dark:bg-zinc-900/80',
                isToday &&
                  'bg-brand-50/70 dark:bg-brand-700/10 ring-1 ring-inset ring-brand-500/30',
                (i + 1) % 7 === 0 && 'border-r-0',
              )}
              onClick={() => {
                const date = new Date(d)
                date.setHours(10, 0, 0, 0)
                onCreate(date)
              }}
            >
              <div className="flex items-center justify-between">
                <div
                  className={cn(
                    'text-xs tabular-nums w-6 h-6 flex items-center justify-center rounded-full font-medium',
                    isToday
                      ? 'bg-brand-600 text-white shadow-sm'
                      : inMonth
                        ? 'text-zinc-700 dark:text-zinc-300'
                        : 'text-zinc-400 dark:text-zinc-600',
                  )}
                >
                  {d.getDate()}
                </div>
                {isToday ? (
                  <span className="inline-flex items-center gap-1 text-[10px] font-medium text-brand-700 dark:text-brand-300">
                    <span className="h-1.5 w-1.5 rounded-full bg-brand-500 animate-pulse" />
                    now {fmtTime(now)}
                  </span>
                ) : (
                  <FiPlus className="h-3 w-3 text-zinc-400 opacity-0 group-hover:opacity-100 transition-opacity" />
                )}
              </div>
              <div className="space-y-1 overflow-hidden">
                {events.slice(0, 3).map((e) => {
                  const job = jobMap.get(e.job_id)
                  const round = roundFor(e)
                  const c = companyColor(job?.company)
                  const eventDate = new Date(e.scheduled_at)
                  const isPast = eventDate.getTime() < Date.now() - 60_000
                  return (
                    <button
                      key={e.id}
                      onClick={(ev) => {
                        ev.stopPropagation()
                        onEdit(e)
                      }}
                      className={cn(
                        'w-full text-left rounded-md border-l-[3px] pl-2 pr-1.5 py-1 text-[11px] hover:shadow-sm transition-shadow',
                        c.bg,
                        c.border,
                        c.text,
                        isPast && 'opacity-60',
                      )}
                      title={`Round ${round} · ${stageLabel(e.stage)} · ${
                        job?.company || 'Unknown company'
                      }`}
                    >
                      <div className="flex items-center gap-1 leading-tight">
                        <span className="font-mono text-[10px] opacity-70 shrink-0">
                          R{round}
                        </span>
                        <span className="font-semibold tabular-nums shrink-0">
                          {fmtTime(eventDate)}
                        </span>
                        <span className="truncate">{stageLabel(e.stage)}</span>
                      </div>
                      <div className="truncate text-[11px] font-medium leading-tight mt-0.5">
                        {job?.company || 'Unknown company'}
                      </div>
                    </button>
                  )
                })}
                {events.length > 3 ? (
                  <div className="text-[10px] text-zinc-500 px-1">
                    +{events.length - 3} more
                  </div>
                ) : null}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
