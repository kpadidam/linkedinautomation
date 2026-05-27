import { useMemo, useState } from 'react'
import {
  FiActivity,
  FiAlertOctagon,
  FiChevronDown,
  FiChevronRight,
  FiExternalLink,
  FiImage,
  FiRefreshCw,
} from 'react-icons/fi'
import { EmptyState } from '@/components/EmptyState'
import { api } from '@/lib/api'
import {
  useApplyRuns,
  useCircuitStatus,
  useResetCircuit,
} from '@/hooks/useApplyRuns'
import { useJobs } from '@/hooks/useJobs'
import { applyRunStateColor, cn, formatRelative } from '@/lib/utils'
import type { ApplicationRun, Job } from '@/lib/types'

/**
 * History of every dry-run apply attempt the loop has made. Lets the
 * operator watch the bot's behavior before any real submits ship in
 * slice 4-5.
 *
 * Row click expands a panel with screenshot thumbnails + error details.
 * Banner at top surfaces a tripped circuit breaker with a Reset button.
 */
export default function ApplyRunsScreen() {
  const { data: runs = [], isLoading } = useApplyRuns(100)
  const { data: circuit } = useCircuitStatus()
  const reset = useResetCircuit()
  // We need job titles for runs — the API only returns job_id. Pull a
  // reasonable slice of jobs and join in-memory. For thousands of runs
  // this'd want server-side enrichment; for the slice-3 volume it's fine.
  const { data: jobs = [] } = useJobs({ limit: 500 })
  const jobsById = useMemo(() => {
    const m = new Map<string, Job>()
    for (const j of jobs) m.set(j.job_id, j)
    return m
  }, [jobs])

  const [expandedId, setExpandedId] = useState<number | null>(null)

  return (
    <div className="p-4 md:p-6 space-y-4">
      <div>
        <h1 className="text-xl font-semibold flex items-center gap-2">
          <FiActivity className="h-5 w-5" /> Apply Runs
        </h1>
        <p className="text-sm text-zinc-500 dark:text-zinc-400">
          Dry-run attempts by the apply loop · {runs.length} recent
        </p>
      </div>

      {circuit?.tripped ? (
        <CircuitBanner
          reason={circuit.reason}
          trippedAt={circuit.tripped_at}
          consecutiveFailures={circuit.consecutive_failures}
          onReset={() => reset.mutate()}
          resetting={reset.isPending}
        />
      ) : null}

      {isLoading ? (
        <div className="text-sm text-zinc-500 dark:text-zinc-400">Loading…</div>
      ) : runs.length === 0 ? (
        <EmptyState
          icon={FiActivity}
          title="No apply runs yet"
          description="The apply loop fires every ~5 min (pacing-gated) on approved jobs. Approve one in the Apply Queue, enable auto_apply in Settings, and runs will show up here."
        />
      ) : (
        <div className="surface rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead className="text-xs uppercase tracking-wide text-zinc-500 dark:text-zinc-400 bg-zinc-50 dark:bg-zinc-900">
              <tr>
                <th className="px-3 py-2 w-8" />
                <th className="px-3 py-2 text-left">State</th>
                <th className="px-3 py-2 text-left">Job</th>
                <th className="px-3 py-2 text-left">When</th>
                <th className="px-3 py-2 text-left">Duration</th>
                <th className="px-3 py-2 text-left">Reason</th>
                <th className="px-3 py-2 text-left w-16">Shots</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-200 dark:divide-zinc-800">
              {runs.map((run) => (
                <RunRow
                  key={run.id}
                  run={run}
                  job={jobsById.get(run.job_id)}
                  expanded={expandedId === run.id}
                  onToggle={() =>
                    setExpandedId((id) => (id === run.id ? null : run.id))
                  }
                />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function CircuitBanner({
  reason,
  trippedAt,
  consecutiveFailures,
  onReset,
  resetting,
}: {
  reason: string | null
  trippedAt: string | null
  consecutiveFailures: number
  onReset: () => void
  resetting: boolean
}) {
  return (
    <div className="surface rounded-lg p-3 border-l-4 border-orange-500 flex items-center gap-3">
      <FiAlertOctagon className="h-5 w-5 text-orange-500 shrink-0" />
      <div className="flex-1 min-w-0">
        <div className="text-sm font-medium">
          Circuit breaker tripped — apply loop halted
        </div>
        <div className="text-xs text-zinc-600 dark:text-zinc-400">
          Reason: <span className="font-mono">{reason ?? 'unknown'}</span>
          {trippedAt ? <> · {formatRelative(trippedAt)}</> : null}
          {consecutiveFailures > 0 ? (
            <> · {consecutiveFailures} consecutive failures</>
          ) : null}
        </div>
      </div>
      <button
        type="button"
        onClick={onReset}
        disabled={resetting}
        className="btn-primary !py-1 !px-3 text-xs"
      >
        <FiRefreshCw className={cn('h-3.5 w-3.5', resetting && 'animate-spin')} />
        Reset
      </button>
    </div>
  )
}

function RunRow({
  run,
  job,
  expanded,
  onToggle,
}: {
  run: ApplicationRun
  job: Job | undefined
  expanded: boolean
  onToggle: () => void
}) {
  const durationMs =
    run.started_at && run.ended_at
      ? new Date(run.ended_at).getTime() - new Date(run.started_at).getTime()
      : null
  const durationLabel =
    durationMs == null
      ? '—'
      : durationMs < 1000
        ? `${durationMs}ms`
        : `${(durationMs / 1000).toFixed(1)}s`
  const shots = run.screenshot_paths?.length ?? 0

  return (
    <>
      <tr
        className="cursor-pointer hover:bg-zinc-50 dark:hover:bg-zinc-900/60"
        onClick={onToggle}
      >
        <td className="px-3 py-2 align-middle">
          {expanded ? (
            <FiChevronDown className="h-4 w-4 text-zinc-400" />
          ) : (
            <FiChevronRight className="h-4 w-4 text-zinc-400" />
          )}
        </td>
        <td className="px-3 py-2 align-middle">
          <span className={cn('chip text-[11px]', applyRunStateColor(run.state))}>
            {run.state}
          </span>
        </td>
        <td className="px-3 py-2 align-middle">
          <div className="text-sm font-medium truncate max-w-md">
            {job?.title ?? <span className="text-zinc-400">{run.job_id}</span>}
          </div>
          <div className="text-xs text-zinc-500 dark:text-zinc-400 truncate">
            {job?.company ?? ''}
          </div>
        </td>
        <td className="px-3 py-2 align-middle text-xs text-zinc-500 dark:text-zinc-400">
          {run.started_at ? formatRelative(run.started_at) : '—'}
        </td>
        <td className="px-3 py-2 align-middle text-xs text-zinc-500 dark:text-zinc-400 tabular-nums">
          {durationLabel}
        </td>
        <td className="px-3 py-2 align-middle text-xs">
          <span className="font-mono text-zinc-600 dark:text-zinc-400">
            {run.exit_reason ?? '—'}
          </span>
        </td>
        <td className="px-3 py-2 align-middle text-xs">
          {shots > 0 ? (
            <span className="inline-flex items-center gap-1 text-zinc-500 dark:text-zinc-400">
              <FiImage className="h-3.5 w-3.5" /> {shots}
            </span>
          ) : (
            <span className="text-zinc-400">—</span>
          )}
        </td>
      </tr>
      {expanded ? (
        <tr className="bg-zinc-50 dark:bg-zinc-900/40">
          <td colSpan={7} className="px-4 py-3">
            <RunDetail run={run} job={job} />
          </td>
        </tr>
      ) : null}
    </>
  )
}

function RunDetail({ run, job }: { run: ApplicationRun; job: Job | undefined }) {
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
        <Field label="run id" value={String(run.id)} />
        <Field label="ats" value={run.ats} />
        <Field label="job id" value={run.job_id} />
        <Field
          label="job url"
          value={
            job?.url ? (
              <a
                href={job.url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 text-brand-600 hover:underline"
              >
                open <FiExternalLink className="h-3 w-3" />
              </a>
            ) : (
              '—'
            )
          }
        />
        <Field label="started" value={run.started_at ?? '—'} mono />
        <Field label="ended" value={run.ended_at ?? '—'} mono />
        <Field
          label="dedup key"
          value={run.dedup_key ?? '—'}
          mono
          className="col-span-2 md:col-span-2"
        />
      </div>

      {run.error_message ? (
        <div className="text-xs text-rose-700 dark:text-rose-300 font-mono whitespace-pre-wrap">
          {run.error_message}
        </div>
      ) : null}

      {run.screenshot_paths.length > 0 ? (
        <div className="flex flex-wrap gap-3">
          {run.screenshot_paths.map((_path, i) => (
            <a
              key={i}
              href={api.applyRunScreenshotUrl(run.id, i)}
              target="_blank"
              rel="noreferrer"
              className="block rounded border border-zinc-200 dark:border-zinc-800 overflow-hidden hover:ring-2 hover:ring-brand-500"
              title={`screenshot ${i + 1} — open full size`}
            >
              <img
                src={api.applyRunScreenshotUrl(run.id, i)}
                alt={`run ${run.id} screenshot ${i}`}
                className="block max-h-48"
              />
            </a>
          ))}
        </div>
      ) : (
        <div className="text-xs text-zinc-500 dark:text-zinc-400">
          No screenshots captured for this run.
        </div>
      )}
    </div>
  )
}

function Field({
  label,
  value,
  mono,
  className,
}: {
  label: string
  value: React.ReactNode
  mono?: boolean
  className?: string
}) {
  return (
    <div className={className}>
      <div className="text-[10px] uppercase tracking-wide text-zinc-400">
        {label}
      </div>
      <div className={cn('text-zinc-700 dark:text-zinc-300 break-all', mono && 'font-mono')}>
        {value}
      </div>
    </div>
  )
}
