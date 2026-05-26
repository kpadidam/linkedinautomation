import {
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
  type ColumnDef,
  type SortingState,
} from '@tanstack/react-table'
import { useMemo, useState } from 'react'
import { FiBookmark, FiTag, FiExternalLink, FiCopy, FiArrowRight } from 'react-icons/fi'
import type { Job } from '@/lib/types'
import { cn, effectiveMatchScore, formatRelative, nextActionFor, scoreColor } from '@/lib/utils'
import { useUpdateJob } from '@/hooks/useJobs'
import { useSettings } from '@/hooks/useSettings'
import { StatusSelect } from './StatusSelect'

type GroupedJob = Job & { _dupCount?: number }

function groupDuplicates(jobs: Job[]): GroupedJob[] {
  const seen = new Map<string, GroupedJob>()
  for (const j of jobs) {
    const key = `${(j.company || '').trim().toLowerCase()}|${(j.title || '').trim().toLowerCase()}`
    const existing = seen.get(key)
    if (!existing) {
      seen.set(key, { ...j, _dupCount: 1 })
    } else {
      existing._dupCount = (existing._dupCount || 1) + 1
      const a = new Date(existing.scraped_at || 0).getTime()
      const b = new Date(j.scraped_at || 0).getTime()
      if (b > a) {
        const count = existing._dupCount
        seen.set(key, { ...j, _dupCount: count })
      }
    }
  }
  return Array.from(seen.values())
}

export function JobTable({
  jobs,
  onRowClick,
  selectedIds,
  allVisibleSelected,
  onToggleOne,
  onToggleAll,
}: {
  jobs: Job[]
  onRowClick: (jobId: string) => void
  selectedIds?: Set<string>
  allVisibleSelected?: boolean
  onToggleOne?: (id: string) => void
  onToggleAll?: () => void
}) {
  const update = useUpdateJob()
  const { data: settings } = useSettings()
  // Default to enabled while loading so the UI doesn't flicker hidden→visible.
  const matchingEnabled = settings?.enable_resume_matching ?? true
  const [sorting, setSorting] = useState<SortingState>([{ id: 'scraped_at', desc: true }])
  const [groupDupes, setGroupDupes] = useState(true)

  const data = useMemo(() => (groupDupes ? groupDuplicates(jobs) : jobs), [jobs, groupDupes])
  const dupesHidden = jobs.length - data.length

  const enableSelection = !!selectedIds && !!onToggleOne && !!onToggleAll

  const columns = useMemo<ColumnDef<GroupedJob>[]>(
    () => [
      ...(enableSelection
        ? [
            {
              id: 'select',
              size: 36,
              header: () => (
                <input
                  type="checkbox"
                  className="accent-brand-600 cursor-pointer"
                  checked={!!allVisibleSelected}
                  onChange={() => onToggleAll?.()}
                  onClick={(e) => e.stopPropagation()}
                  aria-label="Select all visible"
                />
              ),
              cell: ({ row }: { row: { original: GroupedJob } }) => (
                <input
                  type="checkbox"
                  className="accent-brand-600 cursor-pointer"
                  checked={selectedIds?.has(row.original.job_id) ?? false}
                  onChange={() => onToggleOne?.(row.original.job_id)}
                  onClick={(e) => e.stopPropagation()}
                  aria-label="Select row"
                />
              ),
            } as ColumnDef<GroupedJob>,
          ]
        : []),
      {
        id: 'bookmark',
        header: '',
        size: 40,
        cell: ({ row }) => (
          <button
            className="p-1 rounded hover:bg-zinc-100 dark:hover:bg-zinc-800"
            onClick={(e) => {
              e.stopPropagation()
              const next = row.original.status === 'saved' ? 'new' : 'saved'
              update.mutate({ jobId: row.original.job_id, body: { status: next } })
            }}
            aria-label="Toggle bookmark"
          >
            <FiBookmark
              className={cn(
                'h-4 w-4',
                row.original.status === 'saved' ? 'fill-brand-600 text-brand-600' : 'text-zinc-400'
              )}
            />
          </button>
        ),
      },
      {
        accessorKey: 'title',
        header: 'Job',
        cell: ({ row }) => (
          <div className="min-w-0">
            <div className="font-medium truncate flex items-center gap-1.5">
              <span className="truncate">{row.original.title}</span>
              {row.original._dupCount && row.original._dupCount > 1 ? (
                <span
                  className="chip text-[10px] bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400"
                  title={`${row.original._dupCount} similar postings`}
                >
                  <FiCopy className="h-2.5 w-2.5" />×{row.original._dupCount}
                </span>
              ) : null}
            </div>
            <div className="text-xs text-zinc-500 dark:text-zinc-400 truncate">
              {row.original.company}
              {row.original.location ? <> · {row.original.location}</> : null}
            </div>
          </div>
        ),
      },
      ...(matchingEnabled
        ? ([
            {
              id: 'match_score',
              header: 'Match',
              size: 80,
              // Prefer the slice-1 local semantic score; fall back to the
              // legacy LLM score. ``effectiveMatchScore`` returns 0–100.
              accessorFn: (row: GroupedJob) => effectiveMatchScore(row),
              cell: ({ getValue }) => {
                const v = getValue<number | null>()
                if (v == null) return <span className="text-zinc-400 text-xs">—</span>
                return <span className={cn('chip', scoreColor(v))}>{v}%</span>
              },
            },
            {
              id: 'why',
              header: 'Why match',
              size: 220,
              cell: ({ row }: { row: { original: GroupedJob } }) => {
                // Defensive: legacy LLM matcher wrote list[str]; older
                // serializations may have a dict — guard before .slice().
                const raw = row.original.match_reasons
                const reasons = Array.isArray(raw) ? raw.slice(0, 3) : []
                if (reasons.length === 0) {
                  const skills = (row.original.skills || []).slice(0, 3)
                  if (skills.length === 0) return <span className="text-zinc-400 text-xs">—</span>
                  return (
                    <div className="flex flex-wrap gap-1">
                      {skills.map((s) => (
                        <span key={s} className="chip text-[10px] bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300">
                          {s}
                        </span>
                      ))}
                    </div>
                  )
                }
                return (
                  <div className="flex flex-wrap gap-1">
                    {reasons.map((r, i) => (
                      <span key={i} className="chip text-[10px] bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300" title={r}>
                        {r.length > 28 ? r.slice(0, 26) + '…' : r}
                      </span>
                    ))}
                  </div>
                )
              },
            },
            {
              id: 'gaps',
              header: 'Gaps',
              size: 180,
              cell: ({ row }: { row: { original: GroupedJob } }) => {
                const gaps = (row.original.resume_gaps || []).slice(0, 3)
                if (gaps.length === 0) return <span className="text-zinc-400 text-xs">—</span>
                return (
                  <div className="flex flex-wrap gap-1">
                    {gaps.map((g, i) => (
                      <span key={i} className="chip text-[10px] bg-rose-50 text-rose-700 dark:bg-rose-950 dark:text-rose-300" title={g}>
                        {g.length > 22 ? g.slice(0, 20) + '…' : g}
                      </span>
                    ))}
                  </div>
                )
              },
            },
          ] as ColumnDef<GroupedJob>[])
        : []),
      {
        accessorKey: 'status',
        header: 'Stage',
        size: 130,
        cell: ({ row }) => (
          <StatusSelect jobId={row.original.job_id} status={row.original.status} />
        ),
      },
      {
        id: 'next_action',
        header: 'Next action',
        size: 130,
        cell: ({ row }) => (
          <span className="inline-flex items-center gap-1 text-xs text-zinc-600 dark:text-zinc-300">
            <FiArrowRight className="h-3 w-3 text-brand-500" />
            {nextActionFor(row.original.status)}
          </span>
        ),
      },
      {
        id: 'open',
        header: '',
        size: 36,
        cell: ({ row }) =>
          row.original.url ? (
            <a
              href={row.original.url}
              target="_blank"
              rel="noreferrer"
              onClick={(e) => e.stopPropagation()}
              className="p-1 rounded hover:bg-zinc-100 dark:hover:bg-zinc-800 inline-flex"
              title="Open on LinkedIn"
            >
              <FiExternalLink className="h-4 w-4 text-zinc-500" />
            </a>
          ) : null,
      },
      {
        accessorKey: 'tags',
        header: 'Labels',
        size: 140,
        cell: ({ getValue }) => {
          const tags = (getValue<string[] | undefined>() || []).slice(0, 2)
          if (tags.length === 0) return <span className="text-zinc-400 text-xs">—</span>
          return (
            <div className="flex flex-wrap gap-1">
              {tags.map((t) => (
                <span key={t} className="chip bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300">
                  <FiTag className="h-2.5 w-2.5" />
                  {t}
                </span>
              ))}
            </div>
          )
        },
      },
      {
        accessorKey: 'scraped_at',
        header: 'Scraped',
        size: 100,
        cell: ({ getValue }) => (
          <span className="text-xs text-zinc-500 dark:text-zinc-400">{formatRelative(getValue<string>())}</span>
        ),
      },
    ],
    [update, enableSelection, allVisibleSelected, selectedIds, onToggleOne, onToggleAll, matchingEnabled]
  )

  const table = useReactTable({
    data,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  })

  return (
    <div className="surface rounded-lg overflow-hidden">
      <div className="flex items-center justify-between px-3 py-2 border-b border-zinc-200 dark:border-zinc-800 bg-zinc-50/60 dark:bg-zinc-900/40">
        <label className="flex items-center gap-2 text-xs text-zinc-600 dark:text-zinc-400 cursor-pointer">
          <input
            type="checkbox"
            checked={groupDupes}
            onChange={(e) => setGroupDupes(e.target.checked)}
            className="accent-brand-600"
          />
          Group duplicates
          {groupDupes && dupesHidden > 0 ? (
            <span className="text-zinc-400">({dupesHidden} hidden)</span>
          ) : null}
        </label>
        <span className="text-xs text-zinc-500 tabular-nums">{data.length} rows</span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-zinc-50 dark:bg-zinc-900/60 border-b border-zinc-200 dark:border-zinc-800 sticky top-0">
            {table.getHeaderGroups().map((hg) => (
              <tr key={hg.id}>
                {hg.headers.map((h) => (
                  <th
                    key={h.id}
                    style={{ width: h.getSize() }}
                    className="px-3 py-2 text-left text-xs font-medium uppercase tracking-wide text-zinc-500 dark:text-zinc-400 cursor-pointer select-none"
                    onClick={h.column.getToggleSortingHandler()}
                  >
                    {flexRender(h.column.columnDef.header, h.getContext())}
                    {h.column.getIsSorted() ? (h.column.getIsSorted() === 'desc' ? ' ↓' : ' ↑') : null}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.map((row) => (
              <tr
                key={row.id}
                className="border-b border-zinc-100 dark:border-zinc-800 hover:bg-zinc-50 dark:hover:bg-zinc-800/40 cursor-pointer"
                onClick={() => onRowClick(row.original.job_id)}
              >
                {row.getVisibleCells().map((cell) => (
                  <td key={cell.id} className="px-3 py-2.5 align-middle">
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
