import { FiTag, FiX } from 'react-icons/fi'
import { useState } from 'react'
import { useUpdateJob } from '@/hooks/useJobs'

const PRESETS = ['Hot', 'Maybe', 'Followup', 'Dream', 'Remote', 'Onsite']

export function JobLabels({ jobId, labels }: { jobId: string; labels: string[] }) {
  const [adding, setAdding] = useState(false)
  const [draft, setDraft] = useState('')
  const update = useUpdateJob()

  const setLabels = (next: string[]) =>
    update.mutate({ jobId, body: { labels: Array.from(new Set(next)) } })

  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {labels.map((l) => (
        <span key={l} className="chip bg-brand-50 text-brand-700 dark:bg-brand-700/20 dark:text-brand-100">
          <FiTag className="h-3 w-3" />
          {l}
          <button
            className="ml-0.5 opacity-60 hover:opacity-100"
            onClick={() => setLabels(labels.filter((x) => x !== l))}
            aria-label={`Remove ${l}`}
          >
            <FiX className="h-3 w-3" />
          </button>
        </span>
      ))}
      {adding ? (
        <div className="flex items-center gap-1">
          <input
            autoFocus
            className="input !py-0.5 !text-xs w-24"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && draft.trim()) {
                setLabels([...labels, draft.trim()])
                setDraft('')
                setAdding(false)
              } else if (e.key === 'Escape') {
                setAdding(false)
                setDraft('')
              }
            }}
            onBlur={() => {
              if (draft.trim()) setLabels([...labels, draft.trim()])
              setDraft('')
              setAdding(false)
            }}
            placeholder="Label…"
          />
        </div>
      ) : (
        <button
          className="chip bg-zinc-100 text-zinc-600 hover:bg-zinc-200 dark:bg-zinc-800 dark:text-zinc-300 dark:hover:bg-zinc-700"
          onClick={() => setAdding(true)}
        >
          + Add
        </button>
      )}
      {PRESETS.filter((p) => !labels.includes(p)).slice(0, 3).map((p) => (
        <button
          key={p}
          className="chip border border-dashed border-zinc-300 dark:border-zinc-700 text-zinc-500 hover:border-brand-500 hover:text-brand-600"
          onClick={() => setLabels([...labels, p])}
        >
          {p}
        </button>
      ))}
    </div>
  )
}
