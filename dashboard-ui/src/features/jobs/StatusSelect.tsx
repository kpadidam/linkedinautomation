import { cn, statusColor, statusLabel } from '@/lib/utils'
import { useUpdateJob } from '@/hooks/useJobs'

const STATUSES = [
  'new',
  'saved',
  'tailoring_resume',
  'applied',
  'recruiter_screen',
  'technical_interview',
  'final',
  'offer',
  'rejected',
]

export function StatusSelect({ jobId, status }: { jobId: string; status?: string | null }) {
  const update = useUpdateJob()
  const current = status || 'new'
  return (
    <select
      value={current}
      onClick={(e) => e.stopPropagation()}
      onChange={(e) => {
        e.stopPropagation()
        update.mutate({ jobId, body: { status: e.target.value } })
      }}
      className={cn(
        'chip capitalize border-0 cursor-pointer pr-6 appearance-none bg-no-repeat bg-right',
        statusColor(current)
      )}
      style={{
        backgroundImage:
          "url(\"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2'><polyline points='6 9 12 15 18 9'/></svg>\")",
        backgroundPosition: 'right 4px center',
      }}
    >
      {STATUSES.map((s) => (
        <option key={s} value={s}>
          {statusLabel(s)}
        </option>
      ))}
    </select>
  )
}
