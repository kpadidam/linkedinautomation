import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { JobUpdate, JobsQuery } from '@/lib/types'

export function useJobs(q: JobsQuery = {}) {
  return useQuery({
    queryKey: ['jobs', q],
    queryFn: () => api.jobs(q),
    refetchInterval: 5000,
  })
}

export function useJob(jobId: string | null) {
  return useQuery({
    queryKey: ['job', jobId],
    queryFn: () => api.job(jobId as string),
    enabled: jobId != null,
  })
}

export function useUpdateJob() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ jobId, body }: { jobId: string; body: JobUpdate }) => api.updateJob(jobId, body),
    onSuccess: (_, { jobId }) => {
      qc.invalidateQueries({ queryKey: ['jobs'] })
      qc.invalidateQueries({ queryKey: ['job', jobId] })
      qc.invalidateQueries({ queryKey: ['statistics'] })
    },
  })
}

export function useStatistics() {
  return useQuery({
    queryKey: ['statistics'],
    queryFn: () => api.statistics(),
    refetchInterval: 10000,
  })
}

export function useSearches(limit = 10) {
  return useQuery({
    queryKey: ['searches', limit],
    queryFn: () => api.searches(limit),
    refetchInterval: 10000,
  })
}
