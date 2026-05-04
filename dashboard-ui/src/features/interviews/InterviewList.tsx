import { useMemo, useState } from 'react'
import { FiPlus, FiTrash2, FiCalendar, FiEdit2 } from 'react-icons/fi'
import { useDeleteInterview, useInterviews } from '@/hooks/useInterviews'
import { cn, statusColor } from '@/lib/utils'
import {
  ScheduleInterviewModal,
  STAGES,
  stageLabel,
} from './ScheduleInterviewModal'
import type { Interview } from '@/lib/types.interviews'

export function InterviewList({ jobId }: { jobId: string }) {
  const { data: items = [] } = useInterviews(jobId)
  const del = useDeleteInterview()
  const [modal, setModal] = useState<
    { kind: 'closed' } | { kind: 'create' } | { kind: 'edit'; interview: Interview }
  >({ kind: 'closed' })

  const sorted = useMemo(
    () =>
      [...items].sort(
        (a, b) =>
          new Date(a.scheduled_at).getTime() - new Date(b.scheduled_at).getTime(),
      ),
    [items],
  )

  const nextStage = useMemo(() => {
    if (sorted.length === 0) return 'phone'
    const lastStage = sorted[sorted.length - 1].stage
    const idx = STAGES.findIndex((s) => s.value === lastStage)
    if (idx < 0) return 'tech'
    const next = STAGES[Math.min(idx + 1, STAGES.length - 1)]
    return next.value
  }, [sorted])

  return (
    <div className="space-y-2">
      {sorted.length === 0 ? (
        <div className="text-xs text-zinc-500">No interviews scheduled.</div>
      ) : (
        <ul className="space-y-1.5">
          {sorted.map((e, i) => (
            <li key={e.id} className="flex items-center gap-2 text-sm">
              <span className="font-mono text-[11px] text-zinc-500 w-6 shrink-0">
                R{i + 1}
              </span>
              <FiCalendar className="h-3.5 w-3.5 text-zinc-400 shrink-0" />
              <span className={cn('chip capitalize', statusColor(e.stage))}>
                {stageLabel(e.stage)}
              </span>
              <span className="text-xs text-zinc-500 dark:text-zinc-400 shrink-0">
                {new Date(e.scheduled_at).toLocaleString(undefined, {
                  month: 'short',
                  day: 'numeric',
                  hour: 'numeric',
                  minute: '2-digit',
                })}
              </span>
              <span className="flex-1 truncate text-xs">{e.location || ''}</span>
              <button
                className="btn-ghost !p-1"
                onClick={() => setModal({ kind: 'edit', interview: e })}
                aria-label="Edit interview"
              >
                <FiEdit2 className="h-3.5 w-3.5" />
              </button>
              <button
                className="btn-ghost !p-1"
                onClick={() => del.mutate(e.id)}
                aria-label="Delete interview"
              >
                <FiTrash2 className="h-3.5 w-3.5" />
              </button>
            </li>
          ))}
        </ul>
      )}
      <button className="btn-ghost" onClick={() => setModal({ kind: 'create' })}>
        <FiPlus className="h-3.5 w-3.5" />
        {sorted.length === 0
          ? 'Schedule first round'
          : `Schedule round ${sorted.length + 1}`}
      </button>

      <ScheduleInterviewModal
        open={modal.kind !== 'closed'}
        onClose={() => setModal({ kind: 'closed' })}
        jobId={jobId}
        editing={modal.kind === 'edit' ? modal.interview : null}
        initialStage={modal.kind === 'create' ? nextStage : undefined}
      />
    </div>
  )
}
