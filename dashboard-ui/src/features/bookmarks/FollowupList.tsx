import { useState } from 'react'
import { FiPlus, FiCheck, FiTrash2, FiClock } from 'react-icons/fi'
import { useCreateFollowup, useDeleteFollowup, useFollowups, useUpdateFollowup } from '@/hooks/useInterviews'
import { cn, formatRelative } from '@/lib/utils'
import { useUndoStore } from '@/lib/undo'

export function FollowupList({ jobId }: { jobId: string }) {
  const { data: items = [] } = useFollowups(jobId)
  const create = useCreateFollowup()
  const update = useUpdateFollowup()
  const del = useDeleteFollowup()
  const pushUndo = useUndoStore((s) => s.push)
  const [adding, setAdding] = useState(false)
  const [due, setDue] = useState<string>(() => {
    const d = new Date(); d.setDate(d.getDate() + 3); d.setMinutes(0); d.setSeconds(0)
    const pad = (n: number) => String(n).padStart(2, '0')
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
  })
  const [note, setNote] = useState('')

  return (
    <div className="space-y-2">
      {items.length === 0 ? (
        <div className="text-xs text-zinc-500">No follow-ups yet.</div>
      ) : (
        <ul className="space-y-1.5">
          {items.map((f) => (
            <li key={f.id} className="flex items-center gap-2 text-sm">
              <button
                className={cn(
                  'h-5 w-5 rounded border flex items-center justify-center',
                  f.done ? 'bg-emerald-600 border-emerald-600 text-white' : 'border-zinc-300 dark:border-zinc-700'
                )}
                onClick={() => update.mutate({ id: f.id, body: { done: !f.done } })}
              >
                {f.done ? <FiCheck className="h-3 w-3" /> : null}
              </button>
              <FiClock className="h-3 w-3 text-zinc-400" />
              <span className="text-xs text-zinc-500 dark:text-zinc-400 w-32">
                {new Date(f.due_at).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })}
              </span>
              <span className={cn('flex-1 truncate', f.done && 'line-through text-zinc-400')}>{f.note || '—'}</span>
              <span className="text-[10px] text-zinc-400">{formatRelative(f.due_at)}</span>
              <button
                className="btn-ghost !p-1"
                onClick={() => {
                  const snapshot = { job_id: f.job_id, due_at: f.due_at, note: f.note ?? undefined }
                  del.mutate(f.id)
                  pushUndo({
                    label: 'Deleted follow-up',
                    undo: () => create.mutate(snapshot),
                  })
                }}
              >
                <FiTrash2 className="h-3.5 w-3.5" />
              </button>
            </li>
          ))}
        </ul>
      )}
      {adding ? (
        <div className="space-y-1.5">
          <input type="datetime-local" className="input" value={due} onChange={(e) => setDue(e.target.value)} />
          <input className="input" placeholder="Note (e.g. Email recruiter)" value={note} onChange={(e) => setNote(e.target.value)} />
          <div className="flex gap-1.5">
            <button
              className="btn-primary"
              onClick={() => {
                create.mutate({ job_id: jobId, due_at: new Date(due).toISOString(), note: note || undefined })
                setAdding(false); setNote('')
              }}
            >Add</button>
            <button className="btn-ghost" onClick={() => setAdding(false)}>Cancel</button>
          </div>
        </div>
      ) : (
        <button className="btn-ghost" onClick={() => setAdding(true)}>
          <FiPlus className="h-3.5 w-3.5" /> Add follow-up
        </button>
      )}
    </div>
  )
}
