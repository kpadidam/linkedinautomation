import { useEffect, useMemo, useRef, useState } from 'react'
import { cn, companyColor } from '@/lib/utils'
import { stageLabel } from '@/features/interviews/ScheduleInterviewModal'
import type { Interview } from '@/lib/types.interviews'
import type { Job } from '@/lib/types'

const HOUR_HEIGHT = 56
const START_HOUR = 0
const END_HOUR = 24

const DURATION_BY_STAGE: Record<string, number> = {
  phone: 30,
  recruiter: 30,
  tech: 60,
  system_design: 60,
  behavioral: 45,
  onsite: 90,
  final: 60,
  offer: 30,
}
const DEFAULT_DURATION = 60

function durationFor(stage: string) {
  return DURATION_BY_STAGE[stage] ?? DEFAULT_DURATION
}

function ymd(d: Date) {
  return d.toISOString().slice(0, 10)
}
function fmtTime(d: Date) {
  return d.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })
}
function hourLabel(h: number) {
  if (h === 0) return '12 AM'
  if (h === 12) return '12 PM'
  if (h < 12) return `${h} AM`
  return `${h - 12} PM`
}

export interface TimeGridViewProps {
  days: Date[]
  interviews: Interview[]
  jobMap: Map<string, Job>
  roundFor: (e: Interview) => number
  onCreate: (date: Date) => void
  onEdit: (e: Interview) => void
}

export function TimeGridView({
  days,
  interviews,
  jobMap,
  roundFor,
  onCreate,
  onEdit,
}: TimeGridViewProps) {
  const [now, setNow] = useState(() => new Date())
  const scrollRef = useRef<HTMLDivElement | null>(null)
  const todayKey = ymd(new Date())

  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 60_000)
    return () => clearInterval(id)
  }, [])

  // Scroll to ~7am on mount so the working day is in view by default.
  useEffect(() => {
    if (!scrollRef.current) return
    scrollRef.current.scrollTop = 7 * HOUR_HEIGHT - 8
  }, [])

  const eventsByDay = useMemo(() => {
    const m = new Map<string, Interview[]>()
    for (const e of interviews) {
      const k = ymd(new Date(e.scheduled_at))
      const arr = m.get(k) || []
      arr.push(e)
      m.set(k, arr)
    }
    for (const [, arr] of m) {
      arr.sort(
        (a, b) =>
          new Date(a.scheduled_at).getTime() - new Date(b.scheduled_at).getTime(),
      )
    }
    return m
  }, [interviews])

  const totalHeight = (END_HOUR - START_HOUR) * HOUR_HEIGHT
  const nowMinutes = now.getHours() * 60 + now.getMinutes()
  const nowOffset = ((nowMinutes - START_HOUR * 60) / 60) * HOUR_HEIGHT

  const isWeek = days.length > 1

  return (
    <div className="surface rounded-lg overflow-hidden flex-1 flex flex-col min-h-0">
      {/* Day headers row */}
      <div className="flex border-b border-zinc-200 dark:border-zinc-800 bg-zinc-50/60 dark:bg-zinc-900/60">
        <div className="w-14 shrink-0 border-r border-zinc-200 dark:border-zinc-800" />
        {days.map((d) => {
          const isToday = ymd(d) === todayKey
          return (
            <div
              key={d.toISOString()}
              className={cn(
                'flex-1 px-2 py-2 text-center border-r border-zinc-200 dark:border-zinc-800 last:border-r-0',
                isToday && 'bg-brand-50/70 dark:bg-brand-700/15',
              )}
            >
              <div
                className={cn(
                  'text-[11px] uppercase tracking-wide',
                  isToday
                    ? 'text-brand-700 dark:text-brand-300 font-medium'
                    : 'text-zinc-500 dark:text-zinc-400',
                )}
              >
                {d.toLocaleDateString(undefined, { weekday: 'short' })}
              </div>
              <div
                className={cn(
                  'mt-0.5 inline-flex items-center justify-center w-7 h-7 rounded-full text-sm font-semibold tabular-nums',
                  isToday
                    ? 'bg-brand-600 text-white'
                    : 'text-zinc-800 dark:text-zinc-200',
                )}
              >
                {d.getDate()}
              </div>
            </div>
          )
        })}
      </div>

      {/* Scrollable hour grid */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto">
        <div className="relative flex" style={{ height: totalHeight }}>
          {/* Hour-label gutter */}
          <div className="w-14 shrink-0 border-r border-zinc-200 dark:border-zinc-800 relative">
            {Array.from({ length: END_HOUR - START_HOUR }, (_, i) => {
              const h = START_HOUR + i
              return (
                <div
                  key={h}
                  className="absolute right-2 -translate-y-1/2 text-[10px] text-zinc-500 dark:text-zinc-400 tabular-nums"
                  style={{ top: i * HOUR_HEIGHT }}
                >
                  {i === 0 ? '' : hourLabel(h)}
                </div>
              )
            })}
          </div>

          {/* Day columns */}
          <div className="flex flex-1">
            {days.map((d) => {
              const isToday = ymd(d) === todayKey
              const dayEvents = eventsByDay.get(ymd(d)) || []
              return (
                <DayColumn
                  key={d.toISOString()}
                  date={d}
                  events={dayEvents}
                  jobMap={jobMap}
                  roundFor={roundFor}
                  isToday={isToday}
                  nowOffset={nowOffset}
                  onCreate={onCreate}
                  onEdit={onEdit}
                  isWeek={isWeek}
                />
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}

function DayColumn({
  date,
  events,
  jobMap,
  roundFor,
  isToday,
  nowOffset,
  onCreate,
  onEdit,
  isWeek,
}: {
  date: Date
  events: Interview[]
  jobMap: Map<string, Job>
  roundFor: (e: Interview) => number
  isToday: boolean
  nowOffset: number
  onCreate: (date: Date) => void
  onEdit: (e: Interview) => void
  isWeek: boolean
}) {
  const handleSlotClick = (hour: number, half: 0 | 1) => {
    const target = new Date(date)
    target.setHours(hour, half * 30, 0, 0)
    onCreate(target)
  }

  return (
    <div
      className={cn(
        'flex-1 relative border-r border-zinc-200 dark:border-zinc-800 last:border-r-0',
        isToday && 'bg-brand-50/40 dark:bg-brand-700/5',
      )}
    >
      {/* Hour grid lines + half-hour click targets */}
      {Array.from({ length: END_HOUR - START_HOUR }, (_, i) => (
        <div
          key={i}
          className="absolute inset-x-0 border-t border-zinc-100 dark:border-zinc-800/60"
          style={{ top: i * HOUR_HEIGHT, height: HOUR_HEIGHT }}
        >
          <button
            type="button"
            onClick={() => handleSlotClick(START_HOUR + i, 0)}
            className="absolute inset-x-0 top-0 h-1/2 hover:bg-brand-500/5 dark:hover:bg-brand-500/10 transition-colors"
            aria-label={`Add interview at ${hourLabel(START_HOUR + i)}`}
          />
          <button
            type="button"
            onClick={() => handleSlotClick(START_HOUR + i, 1)}
            className="absolute inset-x-0 bottom-0 h-1/2 hover:bg-brand-500/5 dark:hover:bg-brand-500/10 transition-colors border-t border-dashed border-transparent hover:border-brand-300/30"
            aria-label={`Add interview at ${hourLabel(START_HOUR + i)} 30`}
          />
        </div>
      ))}

      {/* Events */}
      {layoutEvents(events).map(({ event, lane, lanes }) => {
        const start = new Date(event.scheduled_at)
        const startMin = start.getHours() * 60 + start.getMinutes()
        const dur = durationFor(event.stage)
        const top = ((startMin - START_HOUR * 60) / 60) * HOUR_HEIGHT
        const height = (dur / 60) * HOUR_HEIGHT - 2
        const job = jobMap.get(event.job_id)
        const c = companyColor(job?.company)
        const round = roundFor(event)
        const widthPct = 100 / lanes
        const leftPct = lane * widthPct
        const isPast = start.getTime() + dur * 60_000 < Date.now()

        return (
          <button
            key={event.id}
            onClick={(ev) => {
              ev.stopPropagation()
              onEdit(event)
            }}
            className={cn(
              'absolute rounded-md border-l-[3px] px-2 py-1 text-left overflow-hidden hover:shadow-md transition-shadow',
              c.bg,
              c.border,
              c.text,
              isPast && 'opacity-60',
            )}
            style={{
              top: top + 1,
              height: Math.max(height, 22),
              left: `calc(${leftPct}% + 2px)`,
              width: `calc(${widthPct}% - 4px)`,
            }}
            title={`Round ${round} · ${stageLabel(event.stage)} · ${
              job?.company || 'Unknown company'
            }`}
          >
            <div className="flex items-center gap-1 text-[11px] leading-tight">
              <span className="font-mono text-[10px] opacity-70 shrink-0">R{round}</span>
              <span className="font-semibold tabular-nums shrink-0">{fmtTime(start)}</span>
              {height > 38 || !isWeek ? (
                <span className="truncate">{stageLabel(event.stage)}</span>
              ) : null}
            </div>
            {height > 26 ? (
              <div className="truncate text-[11px] font-medium leading-tight mt-0.5">
                {job?.company || 'Unknown company'}
              </div>
            ) : null}
          </button>
        )
      })}

      {/* Now line */}
      {isToday ? (
        <div
          className="absolute inset-x-0 z-10 pointer-events-none"
          style={{ top: nowOffset }}
        >
          <div className="absolute -left-1 -translate-y-1/2 h-2.5 w-2.5 rounded-full bg-rose-500 shadow-sm" />
          <div className="h-px bg-rose-500" />
        </div>
      ) : null}
    </div>
  )
}

interface LaidOutEvent {
  event: Interview
  lane: number
  lanes: number
}

// Greedy lane assignment: events that overlap in time get placed in side-by-side columns.
function layoutEvents(events: Interview[]): LaidOutEvent[] {
  const sorted = [...events].sort(
    (a, b) =>
      new Date(a.scheduled_at).getTime() - new Date(b.scheduled_at).getTime(),
  )
  const result: LaidOutEvent[] = []
  let cluster: LaidOutEvent[] = []
  let clusterEnd = 0

  const flush = () => {
    if (cluster.length === 0) return
    const lanes = Math.max(...cluster.map((c) => c.lane)) + 1
    for (const c of cluster) c.lanes = lanes
    cluster = []
  }

  for (const event of sorted) {
    const start = new Date(event.scheduled_at).getTime()
    const end = start + durationFor(event.stage) * 60_000

    if (cluster.length === 0 || start >= clusterEnd) {
      flush()
      cluster.push({ event, lane: 0, lanes: 1 })
      clusterEnd = end
    } else {
      const usedLanes = new Set(cluster.map((c) => c.lane))
      let lane = 0
      while (usedLanes.has(lane)) lane++
      cluster.push({ event, lane, lanes: 1 })
      clusterEnd = Math.max(clusterEnd, end)
    }
    result.push(cluster[cluster.length - 1])
  }
  flush()
  return result
}
