import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { LIVE_POLL_MS } from '@/lib/poll'

/** History of dry-run apply attempts, newest first. Auto-refreshes. */
export function useApplyRuns(limit = 50) {
  return useQuery({
    queryKey: ['apply-runs', limit],
    queryFn: () => api.applyRuns(limit),
    refetchInterval: LIVE_POLL_MS,
  })
}

/**
 * Read the circuit-breaker state. The Apply Runs screen renders a banner
 * when this returns ``tripped: true``; the operator clears it via
 * ``useResetCircuit()``.
 */
export function useCircuitStatus() {
  return useQuery({
    queryKey: ['circuit-status'],
    queryFn: () => api.circuitStatus(),
    refetchInterval: LIVE_POLL_MS,
  })
}

/** Operator-driven reset after they've resolved whatever tripped it. */
export function useResetCircuit() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => api.resetCircuit(),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['circuit-status'] })
      qc.invalidateQueries({ queryKey: ['apply-runs'] })
    },
  })
}
