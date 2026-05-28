import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { LIVE_POLL_MS } from '@/lib/poll'

/**
 * Eligible jobs awaiting operator approval, score-sorted descending.
 * Powers the Apply Queue screen. Refreshes on the same cadence as the
 * rest of the live surfaces (LIVE_POLL_MS).
 */
export function useApplyQueue(limit = 50) {
  return useQuery({
    queryKey: ['apply-queue', limit],
    queryFn: () => api.applyQueue(limit),
    refetchInterval: LIVE_POLL_MS,
  })
}

/**
 * Approve a single job: backend flips ``apply_status`` to ``approved``.
 * Slice 3's apply loop will pick it up; this slice just records intent.
 * Invalidates the queue + jobs list so the approved row drops out
 * immediately.
 */
export function useApproveJob() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (jobId: string) => api.applyApprove(jobId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['apply-queue'] })
      qc.invalidateQueries({ queryKey: ['jobs'] })
      qc.invalidateQueries({ queryKey: ['statistics'] })
    },
  })
}

/**
 * Operator-initiated immediate apply on a single job. Bypasses the
 * 5-minute apply-loop tick and the pacing gates — the bot fires
 * Playwright synchronously. Still respects the circuit breaker.
 *
 * Returns the resulting ``ApplicationRun`` summary so the UI can
 * navigate the operator straight to /apply-runs to watch it.
 */
export function useApplyNow() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (jobId: string) => api.applyNow(jobId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['apply-runs'] })
      qc.invalidateQueries({ queryKey: ['apply-queue'] })
      qc.invalidateQueries({ queryKey: ['jobs'] })
    },
  })
}

/**
 * Skip a single job: backend flips ``apply_status`` to
 * ``skipped_by_operator``. Sticky — the matcher will not re-promote it
 * to ``eligible`` on a future rerun.
 */
export function useSkipJob() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (jobId: string) => api.applySkip(jobId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['apply-queue'] })
      qc.invalidateQueries({ queryKey: ['jobs'] })
    },
  })
}
