import { useMemo, useState } from 'react'
import { FiBriefcase } from 'react-icons/fi'
import { useJobs } from '@/hooks/useJobs'
import { JobTable } from '@/features/jobs/JobTable'
import { JobFilters, type JobFiltersValue } from '@/features/jobs/JobFilters'
import { JobDetailDrawer } from '@/features/jobs/JobDetailDrawer'
import { EmptyState } from '@/components/EmptyState'

export default function ReviewQueueScreen() {
  const [filters, setFilters] = useState<JobFiltersValue>({ q: '', status: '', minScore: 0 })
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null)

  const { data: jobs = [], isLoading } = useJobs({
    limit: 200,
    status: filters.status || undefined,
    min_score: filters.minScore || undefined,
  })

  const filtered = useMemo(() => {
    if (!filters.q) return jobs
    const q = filters.q.toLowerCase()
    return jobs.filter(
      (j) =>
        j.title?.toLowerCase().includes(q) ||
        j.company?.toLowerCase().includes(q) ||
        j.location?.toLowerCase().includes(q)
    )
  }, [jobs, filters.q])

  return (
    <div className="p-4 md:p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Review Queue</h1>
          <p className="text-sm text-zinc-500 dark:text-zinc-400">
            Triage newly discovered jobs · {filtered.length} of {jobs.length} · live updates every 5s
          </p>
        </div>
      </div>

      <JobFilters value={filters} onChange={setFilters} />

      {isLoading ? (
        <div className="surface rounded-lg p-8 text-sm text-zinc-500">Loading jobs…</div>
      ) : filtered.length === 0 ? (
        <div className="surface rounded-lg">
          <EmptyState
            icon={FiBriefcase}
            title="No jobs to review"
            description="Adjust your filters or run a scraping session to pull new jobs from LinkedIn."
          />
        </div>
      ) : (
        <JobTable jobs={filtered} onRowClick={setSelectedJobId} />
      )}

      <JobDetailDrawer jobId={selectedJobId} onClose={() => setSelectedJobId(null)} />
    </div>
  )
}
