import { useState } from 'react'
import {
  FiSend,
  FiCheck,
  FiX,
  FiExternalLink,
  FiMapPin,
} from 'react-icons/fi'
import { EmptyState } from '@/components/EmptyState'
import {
  useApplyQueue,
  useApproveJob,
  useSkipJob,
} from '@/hooks/useApplyQueue'
import { cn, companyColor, effectiveMatchScore, scoreColor } from '@/lib/utils'
import type { Job } from '@/lib/types'

/**
 * Operator review surface for the auto-apply pipeline (slice 2).
 *
 * Lists jobs the matcher gated as ``eligible`` and asks the operator to
 * approve or skip each one. Approve flips ``apply_status`` to
 * ``approved`` — slice 3's ``_apply_loop`` will pick those up. Skip
 * flips to ``skipped_by_operator`` (sticky; matcher won't re-promote on
 * the next run).
 *
 * Card layout deliberately — this is a "look, decide, click" surface,
 * not a browsing table. Bulk operations are intentionally absent until
 * the gate is calibrated and we trust the matcher.
 */
export default function ApplyQueueScreen() {
  const { data: jobs = [], isLoading } = useApplyQueue(50)
  const approve = useApproveJob()
  const skip = useSkipJob()

  return (
    <div className="p-4 md:p-6 space-y-4">
      <div>
        <h1 className="text-xl font-semibold flex items-center gap-2">
          <FiSend className="h-5 w-5" /> Apply Queue
        </h1>
        <p className="text-sm text-zinc-500 dark:text-zinc-400">
          Top-matched jobs awaiting your approval · {jobs.length} eligible
        </p>
      </div>

      {isLoading ? (
        <div className="text-sm text-zinc-500 dark:text-zinc-400">Loading…</div>
      ) : jobs.length === 0 ? (
        <EmptyState
          icon={FiSend}
          title="No eligible jobs yet"
          description="Run the matcher (POST /api/match/run) or wait for the next scheduled match loop. Eligible jobs appear here above the configured percentile threshold."
        />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          {jobs.map((job) => (
            <ApplyCard
              key={job.job_id}
              job={job}
              busy={
                approve.isPending && approve.variables === job.job_id ||
                skip.isPending && skip.variables === job.job_id
              }
              onApprove={() => approve.mutate(job.job_id)}
              onSkip={() => skip.mutate(job.job_id)}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function ApplyCard({
  job,
  busy,
  onApprove,
  onSkip,
}: {
  job: Job
  busy: boolean
  onApprove: () => void
  onSkip: () => void
}) {
  const score = effectiveMatchScore(job)
  const pct = job.match_score_percentile
  const color = companyColor(job.company)
  const reasons = Array.isArray(job.match_reasons) ? job.match_reasons : []
  // Heuristic: pull the matched/missing chip strings out of the
  // semicolon-free reason lines the matcher writes (see app/main.py).
  const matchedLine = reasons.find((r) => typeof r === 'string' && r.startsWith('matched: ')) as string | undefined
  const missingLine = reasons.find((r) => typeof r === 'string' && r.startsWith('missing: ')) as string | undefined
  const breakdownLine = reasons.find(
    (r) => typeof r === 'string' && r.startsWith('semantic '),
  ) as string | undefined
  const matchedSkills = matchedLine ? matchedLine.replace('matched: ', '').split(', ') : []
  const missingSkills = missingLine ? missingLine.replace('missing: ', '').split(', ') : []
  const [expanded, setExpanded] = useState(false)
  const description = job.description || ''
  const truncated = description.length > 240 && !expanded
  const shown = truncated ? description.slice(0, 240).trimEnd() + '…' : description

  return (
    <div className={cn('surface rounded-lg p-4 border-l-4', color.border)}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold leading-tight">{job.title}</h3>
            {job.url ? (
              <a
                href={job.url}
                target="_blank"
                rel="noreferrer"
                className="p-1 rounded hover:bg-zinc-100 dark:hover:bg-zinc-800 shrink-0"
                title="Open on LinkedIn"
              >
                <FiExternalLink className="h-3.5 w-3.5 text-zinc-500" />
              </a>
            ) : null}
          </div>
          <div className="mt-0.5 text-xs text-zinc-600 dark:text-zinc-400">
            {job.company || 'Unknown'}
            {job.location ? (
              <span className="inline-flex items-center gap-1 ml-2">
                <FiMapPin className="h-3 w-3" />
                {job.location}
              </span>
            ) : null}
          </div>
        </div>
        <div className="text-right shrink-0">
          {score != null ? (
            <span className={cn('chip text-xs font-semibold', scoreColor(score))}>
              {score}%
            </span>
          ) : null}
          {pct != null ? (
            <div className="mt-1 text-[10px] text-zinc-500 dark:text-zinc-400 tabular-nums">
              p{Math.round(pct)}
            </div>
          ) : null}
        </div>
      </div>

      {matchedSkills.length > 0 ? (
        <div className="mt-2 flex flex-wrap gap-1">
          {matchedSkills.map((s) => (
            <span
              key={`m-${s}`}
              className="chip text-[10px] bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300"
            >
              {s}
            </span>
          ))}
        </div>
      ) : null}

      {missingSkills.length > 0 ? (
        <div className="mt-1 flex flex-wrap gap-1">
          {missingSkills.map((s) => (
            <span
              key={`x-${s}`}
              className="chip text-[10px] bg-zinc-100 text-zinc-500 line-through dark:bg-zinc-800 dark:text-zinc-500"
            >
              {s}
            </span>
          ))}
        </div>
      ) : null}

      {breakdownLine ? (
        <div className="mt-1 text-[11px] text-zinc-500 dark:text-zinc-400 font-mono">
          {breakdownLine}
        </div>
      ) : null}

      {description ? (
        <div className="mt-2 text-xs text-zinc-600 dark:text-zinc-400 whitespace-pre-wrap">
          {shown}
          {description.length > 240 ? (
            <button
              type="button"
              onClick={() => setExpanded((v) => !v)}
              className="ml-1 text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100 underline-offset-2 hover:underline"
            >
              {expanded ? 'show less' : 'show more'}
            </button>
          ) : null}
        </div>
      ) : null}

      <div className="mt-3 flex items-center gap-2">
        <button
          type="button"
          onClick={onApprove}
          disabled={busy}
          className="btn-primary !py-1 !px-3 text-xs"
          title="Mark approved — slice 3 apply loop will pick it up"
        >
          <FiCheck className="h-3.5 w-3.5" /> Approve
        </button>
        <button
          type="button"
          onClick={onSkip}
          disabled={busy}
          className="btn-ghost !py-1 !px-3 text-xs"
          title="Skip — sticky, matcher won't re-promote"
        >
          <FiX className="h-3.5 w-3.5" /> Skip
        </button>
      </div>
    </div>
  )
}
