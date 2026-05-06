import { useMemo, useState } from 'react'
import {
  FiBriefcase,
  FiBookmark,
  FiSend,
  FiSlash,
  FiTag,
  FiX,
} from 'react-icons/fi'
import { useQueryClient } from '@tanstack/react-query'
import { useJobs } from '@/hooks/useJobs'
import { JobTable } from '@/features/jobs/JobTable'
import { JobFilters, type JobFiltersValue } from '@/features/jobs/JobFilters'
import { JobDetailDrawer } from '@/features/jobs/JobDetailDrawer'
import {
  SavedViews,
  useInitialFiltersFromSavedView,
} from '@/features/jobs/SavedViews'
import { EmptyState } from '@/components/EmptyState'
import { api } from '@/lib/api'
import { cn } from '@/lib/utils'

export default function ReviewQueueScreen() {
  const initialFilters = useInitialFiltersFromSavedView({
    q: '',
    status: '',
    minScore: 0,
  })
  const [filters, setFilters] = useState<JobFiltersValue>(initialFilters)
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null)
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [bulkBusy, setBulkBusy] = useState(false)
  const [tagDraft, setTagDraft] = useState('')
  const qc = useQueryClient()

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
        j.location?.toLowerCase().includes(q),
    )
  }, [jobs, filters.q])

  const visibleIds = useMemo(() => filtered.map((j) => j.job_id), [filtered])
  const allVisibleSelected =
    visibleIds.length > 0 && visibleIds.every((id) => selectedIds.has(id))

  const toggleOne = (id: string) =>
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })

  const toggleAll = () =>
    setSelectedIds((prev) => {
      if (allVisibleSelected) {
        // Deselect just the visible ones; keep any cross-filter selections.
        const next = new Set(prev)
        for (const id of visibleIds) next.delete(id)
        return next
      }
      const next = new Set(prev)
      for (const id of visibleIds) next.add(id)
      return next
    })

  const clearSelection = () => setSelectedIds(new Set())

  const bulkUpdate = async (
    body: { status?: string; labels?: string[] },
    label: string,
  ) => {
    if (selectedIds.size === 0) return
    setBulkBusy(true)
    try {
      const ids = [...selectedIds]
      await Promise.all(ids.map((id) => api.updateJob(id, body)))
      qc.invalidateQueries({ queryKey: ['jobs'] })
      qc.invalidateQueries({ queryKey: ['statistics'] })
      // Toast-style note (browser-native for now)
      console.info(`Bulk ${label}: ${ids.length} jobs updated`)
      clearSelection()
    } catch (err) {
      console.error('Bulk update failed', err)
      alert('Some updates failed — check console')
    } finally {
      setBulkBusy(false)
    }
  }

  const bulkAddTag = async () => {
    const tag = tagDraft.trim()
    if (!tag || selectedIds.size === 0) return
    setBulkBusy(true)
    try {
      const ids = [...selectedIds]
      await Promise.all(
        ids.map(async (id) => {
          const job = jobs.find((j) => j.job_id === id)
          const existing = job?.tags || []
          if (existing.includes(tag)) return
          return api.updateJob(id, { labels: [...existing, tag] })
        }),
      )
      qc.invalidateQueries({ queryKey: ['jobs'] })
      setTagDraft('')
      clearSelection()
    } catch (err) {
      console.error('Bulk tag failed', err)
    } finally {
      setBulkBusy(false)
    }
  }

  return (
    <div className="p-4 md:p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Review Queue</h1>
          <p className="text-sm text-zinc-500 dark:text-zinc-400">
            Triage newly discovered jobs · {filtered.length} of {jobs.length} · live
            updates every 5s
          </p>
        </div>
      </div>

      <SavedViews filters={filters} onApply={setFilters} />

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
        <JobTable
          jobs={filtered}
          onRowClick={setSelectedJobId}
          selectedIds={selectedIds}
          allVisibleSelected={allVisibleSelected}
          onToggleOne={toggleOne}
          onToggleAll={toggleAll}
        />
      )}

      <JobDetailDrawer jobId={selectedJobId} onClose={() => setSelectedJobId(null)} />

      {/* Sticky bulk action bar */}
      {selectedIds.size > 0 ? (
        <div
          className={cn(
            'fixed bottom-4 left-1/2 -translate-x-1/2 z-30',
            'surface rounded-full shadow-xl border border-zinc-300 dark:border-zinc-700',
            'flex items-center gap-1 px-3 py-1.5',
          )}
        >
          <span className="text-sm font-medium px-2 tabular-nums">
            {selectedIds.size} selected
          </span>
          <span className="w-px h-5 bg-zinc-200 dark:bg-zinc-700" />
          <button
            className="btn-ghost"
            onClick={() => bulkUpdate({ status: 'saved' }, 'save')}
            disabled={bulkBusy}
            title="Save selected"
          >
            <FiBookmark className="h-3.5 w-3.5" /> Save
          </button>
          <button
            className="btn-ghost"
            onClick={() => bulkUpdate({ status: 'applied' }, 'apply')}
            disabled={bulkBusy}
            title="Mark as applied"
          >
            <FiSend className="h-3.5 w-3.5" /> Apply
          </button>
          <button
            className="btn-ghost"
            onClick={() => bulkUpdate({ status: 'rejected' }, 'reject')}
            disabled={bulkBusy}
            title="Reject selected"
          >
            <FiSlash className="h-3.5 w-3.5" /> Reject
          </button>
          <span className="w-px h-5 bg-zinc-200 dark:bg-zinc-700" />
          <div className="flex items-center gap-1 px-1">
            <FiTag className="h-3.5 w-3.5 text-zinc-400" />
            <input
              className="bg-transparent text-sm outline-none w-24 placeholder:text-zinc-400"
              placeholder="Add tag…"
              value={tagDraft}
              onChange={(e) => setTagDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') bulkAddTag()
              }}
              disabled={bulkBusy}
            />
            <button
              className="btn-ghost text-xs"
              onClick={bulkAddTag}
              disabled={bulkBusy || !tagDraft.trim()}
            >
              Add
            </button>
          </div>
          <span className="w-px h-5 bg-zinc-200 dark:bg-zinc-700" />
          <button
            className="btn-ghost"
            onClick={clearSelection}
            disabled={bulkBusy}
            aria-label="Clear selection"
            title="Clear selection (Esc)"
          >
            <FiX className="h-4 w-4" />
          </button>
        </div>
      ) : null}
    </div>
  )
}
