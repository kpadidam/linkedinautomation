import { useMemo, useState } from 'react'
import { DndContext, DragOverlay, PointerSensor, useDroppable, useDraggable, useSensor, useSensors, type DragEndEvent, type DragStartEvent } from '@dnd-kit/core'
import { FiExternalLink, FiAlertTriangle, FiArrowRight, FiCalendar } from 'react-icons/fi'
import { useJobs, useUpdateJob } from '@/hooks/useJobs'
import { useInterviews } from '@/hooks/useInterviews'
import { useSettings } from '@/hooks/useSettings'
import { PIPELINE_STAGES, type Job } from '@/lib/types'
import type { Interview } from '@/lib/types.interviews'
import { cn, daysSince, effectiveMatchScore, nextActionFor, scoreColor, statusColor } from '@/lib/utils'
import { JobDetailDrawer } from '@/features/jobs/JobDetailDrawer'
import { ScheduleInterviewModal } from '@/features/interviews/ScheduleInterviewModal'
import { useUndoStore } from '@/lib/undo'

const STAGE_IDS = PIPELINE_STAGES.map((s) => s.id)

const KANBAN_TO_INTERVIEW_STAGE: Record<string, string> = {
  recruiter_screen: 'phone',
  technical_interview: 'tech',
  final: 'onsite',
  offer: 'offer',
}

const INTERVIEW_STAGE_COLUMNS = new Set([
  'recruiter_screen',
  'technical_interview',
  'final',
])

interface ScheduleContext {
  jobId: string
  initialStage: string
}

export default function PipelineScreen() {
  const { data: jobs = [] } = useJobs({ limit: 500 })
  const { data: interviews = [] } = useInterviews()
  const update = useUpdateJob()
  const pushUndo = useUndoStore((s) => s.push)
  const [draggingId, setDraggingId] = useState<string | null>(null)
  const [openId, setOpenId] = useState<string | null>(null)
  const [scheduleCtx, setScheduleCtx] = useState<ScheduleContext | null>(null)
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 5 } }))

  const interviewsByJob = useMemo(() => {
    const m = new Map<string, Interview[]>()
    for (const e of interviews) {
      const arr = m.get(e.job_id) || []
      arr.push(e)
      m.set(e.job_id, arr)
    }
    for (const arr of m.values()) {
      arr.sort(
        (a, b) =>
          new Date(a.scheduled_at).getTime() - new Date(b.scheduled_at).getTime(),
      )
    }
    return m
  }, [interviews])

  const grouped = useMemo(() => {
    const g: Record<string, Job[]> = {}
    for (const s of PIPELINE_STAGES) g[s.id] = []
    // Migrate legacy 'interviewing' status into 'recruiter_screen' bucket
    for (const j of jobs) {
      const raw = (j.status as string) || 'new'
      const k = raw === 'interviewing' ? 'recruiter_screen' : raw
      if (g[k]) g[k].push(j)
    }
    return g
  }, [jobs])

  const totalInPipeline = useMemo(
    () => Object.values(grouped).reduce((acc, arr) => acc + arr.length, 0),
    [grouped]
  )

  const onDragStart = (e: DragStartEvent) => setDraggingId(String(e.active.id))
  const onDragEnd = (e: DragEndEvent) => {
    setDraggingId(null)
    const id = String(e.active.id)
    const target = e.over?.id ? String(e.over.id) : null
    if (!target || !STAGE_IDS.includes(target as never)) return
    const job = jobs.find((j) => j.job_id === id)
    if (!job || job.status === target) return
    const oldStatus = job.status
    const newLabel = PIPELINE_STAGES.find((s) => s.id === target)?.label ?? target
    update.mutate({ jobId: id, body: { status: target } })
    pushUndo({
      label: `Moved ${job.title} to ${newLabel}`,
      undo: () => update.mutate({ jobId: id, body: { status: oldStatus } }),
    })
  }

  const draggingJob = draggingId ? jobs.find((j) => j.job_id === draggingId) : null

  return (
    <div className="p-4 md:p-6 h-full flex flex-col">
      <div className="mb-4 flex items-end justify-between">
        <div>
          <h1 className="text-xl font-semibold">Pipeline</h1>
          <p className="text-sm text-zinc-500 dark:text-zinc-400">
            {totalInPipeline} active opportunities · drag between stages · new scraped jobs live in
            <a href="/review-queue" className="text-brand-600 hover:underline ml-1">Review Queue</a>
          </p>
        </div>
      </div>
      <DndContext sensors={sensors} onDragStart={onDragStart} onDragEnd={onDragEnd}>
        <div className="flex gap-3 overflow-x-auto pb-4 flex-1">
          {PIPELINE_STAGES.map((s) => (
            <Column
              key={s.id}
              id={s.id}
              label={s.label}
              jobs={grouped[s.id]}
              onOpen={setOpenId}
              interviewsByJob={interviewsByJob}
              onSchedule={(jobId) =>
                setScheduleCtx({
                  jobId,
                  initialStage: KANBAN_TO_INTERVIEW_STAGE[s.id] ?? 'phone',
                })
              }
            />
          ))}
        </div>
        <DragOverlay>{draggingJob ? <JobCard job={draggingJob} dragging /> : null}</DragOverlay>
      </DndContext>
      <JobDetailDrawer jobId={openId} onClose={() => setOpenId(null)} />
      <ScheduleInterviewModal
        open={scheduleCtx !== null}
        onClose={() => setScheduleCtx(null)}
        jobId={scheduleCtx?.jobId ?? null}
        initialStage={scheduleCtx?.initialStage}
      />
    </div>
  )
}

function Column({
  id,
  label,
  jobs,
  onOpen,
  interviewsByJob,
  onSchedule,
}: {
  id: string
  label: string
  jobs: Job[]
  onOpen: (jid: string) => void
  interviewsByJob: Map<string, Interview[]>
  onSchedule: (jobId: string) => void
}) {
  const { isOver, setNodeRef } = useDroppable({ id })
  const showSchedule = INTERVIEW_STAGE_COLUMNS.has(id) || id === 'offer'
  return (
    <div
      ref={setNodeRef}
      className={cn(
        'w-72 shrink-0 rounded-lg border flex flex-col',
        'border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900/50',
        isOver && 'ring-2 ring-brand-500'
      )}
    >
      <div className="px-3 py-2 flex items-center justify-between border-b border-zinc-200 dark:border-zinc-800">
        <div className="flex items-center gap-2">
          <span className={cn('chip', statusColor(id))}>{label}</span>
          <span className="text-xs text-zinc-500 tabular-nums">{jobs.length}</span>
        </div>
      </div>
      <div className="flex-1 overflow-auto p-2 space-y-2 min-h-[200px]">
        {jobs.length === 0 ? (
          <div className="text-xs text-zinc-400 text-center py-4">Drop here</div>
        ) : (
          jobs.map((j) => (
            <DraggableCard
              key={j.job_id}
              job={j}
              rounds={interviewsByJob.get(j.job_id) || []}
              showSchedule={showSchedule}
              onOpen={() => onOpen(j.job_id)}
              onSchedule={() => onSchedule(j.job_id)}
            />
          ))
        )}
      </div>
    </div>
  )
}

function DraggableCard({
  job,
  rounds,
  showSchedule,
  onOpen,
  onSchedule,
}: {
  job: Job
  rounds: Interview[]
  showSchedule: boolean
  onOpen: () => void
  onSchedule: () => void
}) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({ id: job.job_id })
  return (
    <div
      ref={setNodeRef}
      {...attributes}
      {...listeners}
      onClick={onOpen}
      className={cn(isDragging && 'opacity-30')}
    >
      <JobCard
        job={job}
        rounds={rounds}
        showSchedule={showSchedule}
        onSchedule={onSchedule}
      />
    </div>
  )
}

function JobCard({
  job,
  dragging,
  rounds = [],
  showSchedule,
  onSchedule,
}: {
  job: Job
  dragging?: boolean
  rounds?: Interview[]
  showSchedule?: boolean
  onSchedule?: () => void
}) {
  const { data: settings } = useSettings()
  const matchingEnabled = settings?.enable_resume_matching ?? true
  const age = daysSince(job.last_updated || job.scraped_at)
  const isStale = age != null && age >= 7 && job.status !== 'rejected' && job.status !== 'offer'
  const matchPct = effectiveMatchScore(job)
  const isHighMatchUnapplied =
    matchingEnabled && job.status === 'saved' && (matchPct ?? 0) >= 85
  const nextRound = rounds.find((r) => new Date(r.scheduled_at).getTime() >= Date.now())
  const lastRound = rounds[rounds.length - 1]
  const upcomingRound = nextRound || lastRound
  const nextRoundNumber = rounds.length + 1
  return (
    <div
      className={cn(
        'surface rounded-md p-3 cursor-grab active:cursor-grabbing select-none',
        dragging && 'shadow-xl ring-1 ring-brand-500',
        isStale && 'ring-1 ring-amber-400/60'
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="text-sm font-medium leading-tight line-clamp-2">{job.title}</div>
          <div className="mt-1 text-xs text-zinc-500 dark:text-zinc-400 truncate">
            {job.company}{job.location ? ` · ${job.location}` : ''}
          </div>
        </div>
        {job.url ? (
          <a
            href={job.url}
            target="_blank"
            rel="noreferrer"
            onPointerDown={(e) => e.stopPropagation()}
            onClick={(e) => e.stopPropagation()}
            className="p-1 rounded hover:bg-zinc-100 dark:hover:bg-zinc-800 shrink-0"
            title="Open on LinkedIn"
          >
            <FiExternalLink className="h-3.5 w-3.5 text-zinc-500" />
          </a>
        ) : null}
      </div>
      <div className="mt-2 flex items-center justify-between gap-2">
        {matchingEnabled && matchPct != null ? (
          <span className={cn('chip text-[10px]', scoreColor(matchPct))}>
            {matchPct}%
          </span>
        ) : <span />}
        {age != null ? (
          <span className="text-[10px] text-zinc-500 dark:text-zinc-400">
            {age === 0 ? 'today' : `${age}d`}
          </span>
        ) : null}
      </div>
      <div className="mt-2 flex items-center gap-1 text-[11px] text-zinc-600 dark:text-zinc-300">
        <FiArrowRight className="h-3 w-3 text-brand-500" />
        {nextActionFor(job.status)}
      </div>
      {showSchedule && onSchedule ? (
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation()
            onSchedule()
          }}
          onPointerDown={(e) => e.stopPropagation()}
          className={cn(
            'mt-2 w-full inline-flex items-center justify-center gap-1.5 rounded border px-2 py-1 text-[10px] transition-colors',
            upcomingRound
              ? 'border-brand-200 dark:border-brand-700/60 text-brand-700 dark:text-brand-200 bg-brand-50 dark:bg-brand-700/10 hover:bg-brand-100 dark:hover:bg-brand-700/20'
              : 'border-dashed border-zinc-300 dark:border-zinc-700 text-zinc-600 dark:text-zinc-400 hover:border-brand-500 hover:text-brand-700 dark:hover:text-brand-300'
          )}
          title={
            upcomingRound
              ? `Round ${rounds.indexOf(upcomingRound) + 1} scheduled — click to add the next`
              : `Schedule round ${nextRoundNumber}`
          }
        >
          <FiCalendar className="h-3 w-3" />
          {upcomingRound
            ? `R${rounds.indexOf(upcomingRound) + 1} · ${new Date(
                upcomingRound.scheduled_at,
              ).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}${
                rounds.length > 0 ? ` · + round ${nextRoundNumber}` : ''
              }`
            : `Schedule round ${nextRoundNumber}`}
        </button>
      ) : null}
      {(isStale || isHighMatchUnapplied) ? (
        <div className="mt-2 flex flex-wrap gap-1">
          {isStale ? (
            <span className="chip text-[10px] bg-amber-50 text-amber-700 dark:bg-amber-950 dark:text-amber-300">
              <FiAlertTriangle className="h-2.5 w-2.5" /> Stale {age}d
            </span>
          ) : null}
          {isHighMatchUnapplied ? (
            <span className="chip text-[10px] bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300">
              High match · apply
            </span>
          ) : null}
        </div>
      ) : null}
    </div>
  )
}
