import { useState } from 'react'
import { FiPlus, FiTrash2, FiCalendar } from 'react-icons/fi'
import { useCreateInterview, useDeleteInterview, useInterviews } from '@/hooks/useInterviews'
import { cn, statusColor } from '@/lib/utils'

const STAGES = ['phone', 'tech', 'onsite', 'offer', 'rejected']

export function InterviewList({ jobId }: { jobId: string }) {
  const { data: items = [] } = useInterviews(jobId)
  const create = useCreateInterview()
  const del = useDeleteInterview()
  const [adding, setAdding] = useState(false)
  const [stage, setStage] = useState('phone')
  const [when, setWhen] = useState<string>(() => {
    const d = new Date(); d.setDate(d.getDate() + 7); d.setMinutes(0); d.setSeconds(0)
    return d.toISOString().slice(0, 16)
  })
  const [location, setLocation] = useState('')

  return (
    <div className="space-y-2">
      {items.length === 0 ? (
        <div className="text-xs text-zinc-500">No interviews scheduled.</div>
      ) : (
        <ul className="space-y-1.5">
          {items.map((e) => (
            <li key={e.id} className="flex items-center gap-2 text-sm">
              <FiCalendar className="h-3.5 w-3.5 text-zinc-400" />
              <span className={cn('chip capitalize', statusColor(e.stage))}>{e.stage}</span>
              <span className="text-xs text-zinc-500 dark:text-zinc-400">
                {new Date(e.scheduled_at).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })}
              </span>
              <span className="flex-1 truncate text-xs">{e.location || ''}</span>
              <button className="btn-ghost !p-1" onClick={() => del.mutate(e.id)}>
                <FiTrash2 className="h-3.5 w-3.5" />
              </button>
            </li>
          ))}
        </ul>
      )}
      {adding ? (
        <div className="space-y-1.5">
          <select className="input" value={stage} onChange={(e) => setStage(e.target.value)}>
            {STAGES.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
          <input type="datetime-local" className="input" value={when} onChange={(e) => setWhen(e.target.value)} />
          <input className="input" placeholder="Location / link" value={location} onChange={(e) => setLocation(e.target.value)} />
          <div className="flex gap-1.5">
            <button
              className="btn-primary"
              onClick={() => {
                create.mutate({ job_id: jobId, stage, scheduled_at: new Date(when).toISOString(), location: location || undefined })
                setAdding(false); setLocation('')
              }}
            >Schedule</button>
            <button className="btn-ghost" onClick={() => setAdding(false)}>Cancel</button>
          </div>
        </div>
      ) : (
        <button className="btn-ghost" onClick={() => setAdding(true)}>
          <FiPlus className="h-3.5 w-3.5" /> Schedule interview
        </button>
      )}
    </div>
  )
}
