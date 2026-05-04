import { useState } from 'react'
import { FiX, FiTrash2 } from 'react-icons/fi'
import { useCreateInterview, useDeleteInterview } from '@/hooks/useInterviews'
import type { Interview } from '@/lib/types.interviews'
import { useUndoStore } from '@/lib/undo'

const STAGES = ['phone', 'tech', 'onsite', 'offer', 'rejected']

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

interface Props {
  jobId: string
  existing?: Interview | null
  roundNumber?: number
  onClose: () => void
}

export function ScheduleInterviewModal({ jobId, existing, roundNumber, onClose }: Props) {
  const create = useCreateInterview()
  const del = useDeleteInterview()
  const pushUndo = useUndoStore((s) => s.push)

  const [stage, setStage] = useState(existing?.stage ?? 'phone')
  const [when, setWhen] = useState<string>(() => {
    if (existing?.scheduled_at) {
      const d = new Date(existing.scheduled_at)
      const off = d.getTimezoneOffset() * 60000
      return new Date(d.getTime() - off).toISOString().slice(0, 16)
    }
    const d = new Date()
    d.setDate(d.getDate() + 7)
    d.setMinutes(0, 0, 0)
    const off = d.getTimezoneOffset() * 60000
    return new Date(d.getTime() - off).toISOString().slice(0, 16)
  })
  const [location, setLocation] = useState(existing?.location ?? '')
  const [notes, setNotes] = useState(existing?.notes ?? '')
  const [interviewerTz, setInterviewerTz] = useState<string>(existing?.interviewer_tz ?? '')

  const submit = () => {
    const payload = {
      job_id: jobId,
      stage,
      scheduled_at: new Date(when).toISOString(),
      location: location || undefined,
      notes: notes || undefined,
      interviewer_tz: interviewerTz || null,
    }
    create.mutate(payload as Omit<Interview, 'id' | 'created_at'>)
    onClose()
  }

  const onDelete = () => {
    if (!existing) return
    // capture state before mutation, then push an undo that recreates the interview
    const snapshot = {
      job_id: existing.job_id,
      stage: existing.stage,
      scheduled_at: existing.scheduled_at,
      location: existing.location ?? undefined,
      notes: existing.notes ?? undefined,
      interviewer_tz: existing.interviewer_tz ?? null,
    }
    const label = `Deleted Round ${roundNumber ?? '?'} · ${existing.stage}`
    del.mutate(existing.id)
    pushUndo({
      label,
      undo: () => {
        create.mutate(snapshot as Omit<Interview, 'id' | 'created_at'>)
      },
    })
    onClose()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" role="dialog" aria-modal="true">
      <div className="w-full max-w-md surface rounded-lg shadow-xl">
        <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-200 dark:border-zinc-800">
          <h3 className="text-sm font-semibold">{existing ? 'Edit interview' : 'Schedule interview'}</h3>
          <button className="btn-ghost !p-1" onClick={onClose} aria-label="Close"><FiX /></button>
        </div>
        <div className="p-4 space-y-3">
          <label className="block text-xs">
            <div className="text-zinc-500 dark:text-zinc-400 mb-1">Stage</div>
            <select className="input" value={stage} onChange={(e) => setStage(e.target.value)}>
              {STAGES.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </label>

          <label className="block text-xs">
            <div className="text-zinc-500 dark:text-zinc-400 mb-1">Date &amp; time</div>
            <input type="datetime-local" className="input" value={when} onChange={(e) => setWhen(e.target.value)} />
          </label>

          <label className="block text-xs">
            <div className="text-zinc-500 dark:text-zinc-400 mb-1">Timezone</div>
            <select
              className="input"
              value={interviewerTz}
              onChange={(e) => setInterviewerTz(e.target.value)}
            >
              {TIMEZONE_OPTIONS.map((o) => (
                <option key={o.value || 'local'} value={o.value}>{o.label}</option>
              ))}
            </select>
            <div className="mt-1 text-[11px] text-zinc-500 dark:text-zinc-400">
              Will display in your local time + the interviewer's time
            </div>
          </label>

          <label className="block text-xs">
            <div className="text-zinc-500 dark:text-zinc-400 mb-1">Location / link</div>
            <input className="input" value={location} onChange={(e) => setLocation(e.target.value)} placeholder="Zoom link, office, …" />
          </label>

          <label className="block text-xs">
            <div className="text-zinc-500 dark:text-zinc-400 mb-1">Notes</div>
            <textarea className="input min-h-[80px]" value={notes} onChange={(e) => setNotes(e.target.value)} />
          </label>
        </div>
        <div className="flex items-center justify-between px-4 py-3 border-t border-zinc-200 dark:border-zinc-800">
          {existing ? (
            <button className="btn-ghost text-rose-600" onClick={onDelete}>
              <FiTrash2 className="h-3.5 w-3.5" /> Delete
            </button>
          ) : <span />}
          <div className="flex gap-2">
            <button className="btn-ghost" onClick={onClose}>Cancel</button>
            <button className="btn-primary" onClick={submit}>{existing ? 'Save' : 'Schedule'}</button>
          </div>
        </div>
      </div>
    </div>
  )
}
