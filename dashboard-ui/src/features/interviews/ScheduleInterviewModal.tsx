import { useEffect, useMemo, useState } from 'react'
import { FiX, FiTrash2, FiCalendar, FiAlertTriangle } from 'react-icons/fi'
import {
  useCreateInterview,
  useDeleteInterview,
  useInterviews,
  useUpdateInterview,
} from '@/hooks/useInterviews'
import type { Job } from '@/lib/types'
import type { Interview } from '@/lib/types.interviews'
import { useUndoStore } from '@/lib/undo'
import { cn, companyColor } from '@/lib/utils'

// Stage → typical duration (mins). Mirrors TimeGridView so behaviour is consistent.
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

export const STAGES: { value: string; label: string }[] = [
  { value: 'phone', label: 'Phone screen' },
  { value: 'recruiter', label: 'Recruiter call' },
  { value: 'tech', label: 'Technical' },
  { value: 'system_design', label: 'System design' },
  { value: 'behavioral', label: 'Behavioral' },
  { value: 'onsite', label: 'Onsite' },
  { value: 'final', label: 'Final' },
  { value: 'offer', label: 'Offer call' },
]

export function stageLabel(stage: string) {
  return STAGES.find((s) => s.value === stage)?.label ?? stage
}

export const TIMEZONE_OPTIONS: { value: string; label: string }[] = [
  { value: '', label: 'Same as me' },
  { value: 'America/Los_Angeles', label: 'Pacific (Los Angeles)' },
  { value: 'America/Denver', label: 'Mountain (Denver)' },
  { value: 'America/Chicago', label: 'Central (Chicago)' },
  { value: 'America/New_York', label: 'Eastern (New York)' },
  { value: 'Europe/London', label: 'London (UK)' },
  { value: 'Europe/Berlin', label: 'Berlin (Germany)' },
  { value: 'Europe/Paris', label: 'Paris (France)' },
  { value: 'Asia/Kolkata', label: 'India (Kolkata)' },
  { value: 'Asia/Singapore', label: 'Singapore' },
  { value: 'Asia/Tokyo', label: 'Tokyo (Japan)' },
  { value: 'Australia/Sydney', label: 'Sydney (Australia)' },
]

function toDateTimeLocal(d: Date) {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function defaultDate() {
  const d = new Date()
  d.setDate(d.getDate() + 3)
  d.setHours(10, 0, 0, 0)
  return d
}

export interface ScheduleInterviewModalProps {
  open: boolean
  onClose: () => void
  jobId: string | null
  editing?: Interview | null
  initialStage?: string
  initialDate?: Date
  jobs?: Job[]
}

export function ScheduleInterviewModal(props: ScheduleInterviewModalProps) {
  const {
    open,
    onClose,
    jobId,
    editing,
    initialStage,
    initialDate,
    jobs = [],
  } = props

  const allowJobPicker = !editing && jobs.length > 0
  const [pickedJobId, setPickedJobId] = useState<string | null>(jobId)
  const effectiveJobId = editing?.job_id ?? pickedJobId

  const { data: existing = [] } = useInterviews(effectiveJobId || undefined)
  // All interviews across all jobs — used for cross-job conflict detection.
  const { data: allInterviews = [] } = useInterviews()

  const create = useCreateInterview()
  const update = useUpdateInterview()
  const del = useDeleteInterview()
  const pushUndo = useUndoStore((s) => s.push)

  const [stage, setStage] = useState(editing?.stage ?? initialStage ?? 'phone')
  const [when, setWhen] = useState(() =>
    toDateTimeLocal(editing ? new Date(editing.scheduled_at) : initialDate ?? defaultDate()),
  )
  const [location, setLocation] = useState(editing?.location ?? '')
  const [notes, setNotes] = useState(editing?.notes ?? '')
  const [interviewerTz, setInterviewerTz] = useState<string>(
    editing?.interviewer_tz ?? '',
  )

  useEffect(() => {
    if (!open) return
    setPickedJobId(jobId)
    setStage(editing?.stage ?? initialStage ?? 'phone')
    setWhen(
      toDateTimeLocal(editing ? new Date(editing.scheduled_at) : initialDate ?? defaultDate()),
    )
    setLocation(editing?.location ?? '')
    setNotes(editing?.notes ?? '')
    setInterviewerTz(editing?.interviewer_tz ?? '')
  }, [open, jobId, editing?.id, initialStage, initialDate?.toISOString()])

  const sortedExisting = useMemo(
    () =>
      [...existing].sort(
        (a, b) => new Date(a.scheduled_at).getTime() - new Date(b.scheduled_at).getTime(),
      ),
    [existing],
  )

  const roundNumber = useMemo(() => {
    if (!effectiveJobId) return 1
    if (editing) {
      const idx = sortedExisting.findIndex((e) => e.id === editing.id)
      return idx >= 0 ? idx + 1 : sortedExisting.length
    }
    const t = new Date(when).getTime()
    if (Number.isNaN(t)) return sortedExisting.length + 1
    let count = 1
    for (const e of sortedExisting) {
      if (new Date(e.scheduled_at).getTime() <= t) count++
    }
    return count
  }, [sortedExisting, when, editing, effectiveJobId])

  // Conflict detection: any other interview that overlaps the picked window.
  const conflicts = useMemo(() => {
    const t = new Date(when).getTime()
    if (Number.isNaN(t)) return [] as Interview[]
    const dur = durationFor(stage) * 60_000
    const start = t
    const end = t + dur
    return allInterviews.filter((e) => {
      if (editing && e.id === editing.id) return false
      const otherStart = new Date(e.scheduled_at).getTime()
      if (Number.isNaN(otherStart)) return false
      const otherEnd = otherStart + durationFor(e.stage) * 60_000
      return otherStart < end && otherEnd > start
    })
  }, [allInterviews, when, stage, editing?.id])

  if (!open) return null

  const job = jobs.find((j) => j.job_id === effectiveJobId)
  const otherRounds = editing
    ? sortedExisting.filter((e) => e.id !== editing.id)
    : sortedExisting

  const valid =
    !!effectiveJobId && !Number.isNaN(new Date(when).getTime()) && stage.trim().length > 0
  const isEdit = !!editing

  const submit = () => {
    if (!valid || !effectiveJobId) return
    const iso = new Date(when).toISOString()
    const tz = interviewerTz || null
    if (editing) {
      update.mutate(
        {
          id: editing.id,
          body: {
            stage,
            scheduled_at: iso,
            location: location || null,
            notes: notes || null,
            interviewer_tz: tz,
          },
        },
        { onSuccess: () => onClose() },
      )
    } else {
      create.mutate(
        {
          job_id: effectiveJobId,
          stage,
          scheduled_at: iso,
          location: location || undefined,
          notes: notes || undefined,
          interviewer_tz: tz ?? undefined,
        },
        { onSuccess: () => onClose() },
      )
    }
  }

  const remove = () => {
    if (!editing) return
    const snapshot = editing
    del.mutate(editing.id, {
      onSuccess: () => {
        pushUndo({
          label: `Deleted Round ${roundNumber} · ${stageLabel(snapshot.stage)}`,
          undo: () =>
            create.mutate({
              job_id: snapshot.job_id,
              stage: snapshot.stage,
              scheduled_at: snapshot.scheduled_at,
              location: snapshot.location ?? undefined,
              notes: snapshot.notes ?? undefined,
              interviewer_tz: snapshot.interviewer_tz ?? undefined,
            }),
        })
        onClose()
      },
    })
  }

  const isPending = create.isPending || update.isPending || del.isPending

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      onClick={onClose}
    >
      <div className="absolute inset-0 bg-black/50" />
      <div
        className="relative w-full max-w-md surface rounded-xl shadow-xl flex flex-col max-h-[calc(100vh-2rem)]"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="px-5 py-4 border-b border-zinc-200 dark:border-zinc-800 flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2">
              <FiCalendar className="h-4 w-4 text-zinc-500" />
              <h2 className="text-base font-semibold">
                {isEdit ? 'Edit interview' : 'Schedule interview'}
              </h2>
              <span className="chip text-[10px] bg-brand-50 text-brand-700 dark:bg-brand-700/20 dark:text-brand-100">
                Round {roundNumber}
              </span>
            </div>
            {job ? (
              <p className="mt-0.5 text-xs text-zinc-500 dark:text-zinc-400 truncate">
                {job.title}
                {job.company ? ` · ${job.company}` : ''}
              </p>
            ) : null}
          </div>
          <button className="btn-ghost" onClick={onClose} aria-label="Close">
            <FiX className="h-4 w-4" />
          </button>
        </header>

        <div className="px-5 py-4 space-y-4 overflow-auto">
          {allowJobPicker && !editing ? (
            <Field label="Job">
              <select
                className="input"
                value={pickedJobId ?? ''}
                onChange={(e) => setPickedJobId(e.target.value || null)}
              >
                <option value="">Select a job…</option>
                {jobs.map((j) => (
                  <option key={j.job_id} value={j.job_id}>
                    {j.title} · {j.company}
                  </option>
                ))}
              </select>
            </Field>
          ) : null}

          <Field label="Stage">
            <select className="input" value={stage} onChange={(e) => setStage(e.target.value)}>
              {STAGES.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>
          </Field>

          <Field label="Date & time">
            <input
              type="datetime-local"
              className="input"
              value={when}
              onChange={(e) => setWhen(e.target.value)}
            />
          </Field>

          <Field label="Interviewer timezone">
            <select
              className="input"
              value={interviewerTz}
              onChange={(e) => setInterviewerTz(e.target.value)}
            >
              {TIMEZONE_OPTIONS.map((tz) => (
                <option key={tz.value} value={tz.value}>
                  {tz.label}
                </option>
              ))}
            </select>
            <div className="mt-1 text-[11px] text-zinc-500 dark:text-zinc-400">
              Will display in your local time + the interviewer's time on calendar events.
            </div>
          </Field>

          <Field label="Location / link">
            <input
              className="input"
              placeholder="Zoom link, address, or phone number"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
            />
          </Field>

          <Field label="Notes">
            <textarea
              className="input min-h-[72px]"
              placeholder="Interviewer name, prep reminders…"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            />
          </Field>

          {conflicts.length > 0 ? (
            <div className="rounded-md border border-amber-300 dark:border-amber-700/60 bg-amber-50 dark:bg-amber-950/40 px-3 py-2">
              <div className="flex items-center gap-1.5 text-amber-900 dark:text-amber-200 text-xs font-medium mb-1">
                <FiAlertTriangle className="h-3.5 w-3.5" />
                {conflicts.length === 1 ? 'Conflicts with' : `Conflicts with ${conflicts.length} events`}
              </div>
              <ul className="space-y-1">
                {conflicts.map((e) => {
                  const otherJob = jobs.find((j) => j.job_id === e.job_id)
                  const c = companyColor(otherJob?.company)
                  return (
                    <li
                      key={e.id}
                      className="flex items-center gap-2 text-xs text-amber-900 dark:text-amber-100"
                    >
                      <span className={cn('h-2 w-2 rounded-full shrink-0', c.dot)} />
                      <span className="font-mono opacity-70 shrink-0">
                        {new Date(e.scheduled_at).toLocaleString(undefined, {
                          month: 'short',
                          day: 'numeric',
                          hour: 'numeric',
                          minute: '2-digit',
                        })}
                      </span>
                      <span className="capitalize">{e.stage}</span>
                      <span className="opacity-70 truncate">
                        · {otherJob?.company || 'Unknown'}
                      </span>
                    </li>
                  )
                })}
              </ul>
              <div className="mt-1.5 text-[11px] text-amber-800/80 dark:text-amber-200/70">
                You can still save — this is a heads-up.
              </div>
            </div>
          ) : null}

          {otherRounds.length > 0 ? (
            <div className="rounded-md border border-zinc-200 dark:border-zinc-800 px-3 py-2">
              <div className="text-[11px] uppercase tracking-wide text-zinc-500 dark:text-zinc-400 mb-1.5">
                Other rounds for this job
              </div>
              <ul className="space-y-1">
                {otherRounds.map((e, i) => (
                  <li
                    key={e.id}
                    className="flex items-center gap-2 text-xs text-zinc-700 dark:text-zinc-300"
                  >
                    <span className="font-mono text-zinc-500">R{i + 1}</span>
                    <span className="capitalize">{stageLabel(e.stage)}</span>
                    <span className="text-zinc-500">
                      ·{' '}
                      {new Date(e.scheduled_at).toLocaleString(undefined, {
                        month: 'short',
                        day: 'numeric',
                        hour: 'numeric',
                        minute: '2-digit',
                      })}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>

        <footer className={cn(
          'px-5 py-3 border-t border-zinc-200 dark:border-zinc-800 flex items-center justify-between gap-2',
        )}>
          <div>
            {isEdit ? (
              <button
                className="btn-ghost text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/40"
                onClick={remove}
                disabled={isPending}
              >
                <FiTrash2 className="h-4 w-4" /> Delete
              </button>
            ) : null}
          </div>
          <div className="flex items-center gap-2">
            <button className="btn-ghost" onClick={onClose} disabled={isPending}>
              Cancel
            </button>
            <button
              className="btn-primary"
              onClick={submit}
              disabled={!valid || isPending}
            >
              {isPending ? 'Saving…' : isEdit ? 'Save changes' : `Schedule round ${roundNumber}`}
            </button>
          </div>
        </footer>
      </div>
    </div>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <div className="text-xs uppercase tracking-wide text-zinc-500 dark:text-zinc-400 mb-1">
        {label}
      </div>
      {children}
    </label>
  )
}
