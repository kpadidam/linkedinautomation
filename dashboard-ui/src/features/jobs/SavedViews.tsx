import { useEffect, useState } from 'react'
import { FiBookmark, FiPlus, FiTrash2, FiX } from 'react-icons/fi'
import { cn } from '@/lib/utils'
import type { JobFiltersValue } from './JobFilters'

export interface SavedView {
  id: string
  name: string
  filters: JobFiltersValue
  builtin?: boolean
}

const STORAGE_KEY = 'reviewQueue.savedViews.v1'
const ACTIVE_KEY = 'reviewQueue.activeView.v1'

export const BUILTIN_VIEWS: SavedView[] = [
  { id: 'all', name: 'All', filters: { q: '', status: '', minScore: 0 }, builtin: true },
  {
    id: 'high-match',
    name: 'High match ≥ 85',
    filters: { q: '', status: '', minScore: 85 },
    builtin: true,
  },
  {
    id: 'unreviewed',
    name: 'Unreviewed',
    filters: { q: '', status: 'new', minScore: 0 },
    builtin: true,
  },
  {
    id: 'saved',
    name: 'Saved',
    filters: { q: '', status: 'saved', minScore: 0 },
    builtin: true,
  },
]

function loadCustom(): SavedView[] {
  if (typeof window === 'undefined') return []
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

function persistCustom(views: SavedView[]) {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(views))
  } catch {
    // localStorage may be unavailable; non-fatal
  }
}

export function loadActiveViewId(): string | null {
  if (typeof window === 'undefined') return null
  try {
    return window.localStorage.getItem(ACTIVE_KEY)
  } catch {
    return null
  }
}

function persistActive(id: string | null) {
  try {
    if (id) window.localStorage.setItem(ACTIVE_KEY, id)
    else window.localStorage.removeItem(ACTIVE_KEY)
  } catch {
    // non-fatal
  }
}

function filtersEqual(a: JobFiltersValue, b: JobFiltersValue) {
  return a.q === b.q && a.status === b.status && a.minScore === b.minScore
}

function summarize(filters: JobFiltersValue): string {
  const parts: string[] = []
  if (filters.q) parts.push(`"${filters.q}"`)
  if (filters.status) parts.push(filters.status)
  if (filters.minScore > 0) parts.push(`≥${filters.minScore}%`)
  return parts.join(' · ') || 'no filters'
}

export function SavedViews({
  filters,
  onApply,
}: {
  filters: JobFiltersValue
  onApply: (next: JobFiltersValue) => void
}) {
  const [custom, setCustom] = useState<SavedView[]>(loadCustom)
  const [activeId, setActiveId] = useState<string | null>(loadActiveViewId)
  const [naming, setNaming] = useState(false)
  const [draftName, setDraftName] = useState('')

  const allViews: SavedView[] = [...BUILTIN_VIEWS, ...custom]

  // Auto-clear active view when user manually edits filters away from it
  useEffect(() => {
    if (!activeId) return
    const v = allViews.find((x) => x.id === activeId)
    if (v && !filtersEqual(v.filters, filters)) {
      setActiveId(null)
      persistActive(null)
    }
  }, [filters, activeId])

  const apply = (view: SavedView) => {
    setActiveId(view.id)
    persistActive(view.id)
    onApply(view.filters)
  }

  const save = () => {
    const name = draftName.trim()
    if (!name) {
      setNaming(false)
      return
    }
    const id = `custom-${Date.now()}`
    const next = [...custom, { id, name, filters: { ...filters } }]
    setCustom(next)
    persistCustom(next)
    setActiveId(id)
    persistActive(id)
    setDraftName('')
    setNaming(false)
  }

  const remove = (id: string) => {
    const next = custom.filter((v) => v.id !== id)
    setCustom(next)
    persistCustom(next)
    if (activeId === id) {
      setActiveId(null)
      persistActive(null)
    }
  }

  const activeView = allViews.find((v) => v.id === activeId)
  const filtersDirty =
    !!activeView && !filtersEqual(activeView.filters, filters)
  const isCustomDirtyMatchingNothing =
    !activeView &&
    (filters.q !== '' || filters.status !== '' || filters.minScore > 0)

  return (
    <div className="flex items-center gap-1 flex-wrap">
      {allViews.map((v) => (
        <div key={v.id} className="relative group">
          <button
            type="button"
            onClick={() => apply(v)}
            className={cn(
              'inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs border transition-colors',
              activeId === v.id
                ? 'bg-brand-600 text-white border-brand-600'
                : 'bg-white dark:bg-zinc-900 border-zinc-300 dark:border-zinc-700 text-zinc-700 dark:text-zinc-300 hover:border-brand-500 hover:text-brand-700 dark:hover:text-brand-300',
            )}
            title={summarize(v.filters)}
          >
            {v.builtin ? null : <FiBookmark className="h-3 w-3" />}
            {v.name}
          </button>
          {!v.builtin ? (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation()
                remove(v.id)
              }}
              className="absolute -top-1 -right-1 hidden group-hover:flex items-center justify-center h-4 w-4 rounded-full bg-zinc-600 dark:bg-zinc-300 text-white dark:text-zinc-900 text-[10px]"
              aria-label={`Delete view ${v.name}`}
              title="Delete view"
            >
              <FiX className="h-2.5 w-2.5" />
            </button>
          ) : null}
        </div>
      ))}

      {naming ? (
        <div className="inline-flex items-center gap-1 rounded-full border border-brand-500 px-2 py-0.5 bg-white dark:bg-zinc-900">
          <input
            autoFocus
            value={draftName}
            placeholder="View name…"
            onChange={(e) => setDraftName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') save()
              if (e.key === 'Escape') {
                setDraftName('')
                setNaming(false)
              }
            }}
            className="bg-transparent text-xs outline-none w-32"
          />
          <button
            className="text-xs text-brand-600 hover:underline"
            onClick={save}
            disabled={!draftName.trim()}
          >
            Save
          </button>
          <button
            className="text-xs text-zinc-400 hover:text-zinc-600"
            onClick={() => {
              setDraftName('')
              setNaming(false)
            }}
            aria-label="Cancel"
          >
            <FiX className="h-3 w-3" />
          </button>
        </div>
      ) : (filtersDirty || isCustomDirtyMatchingNothing) ? (
        <button
          type="button"
          onClick={() => setNaming(true)}
          className="inline-flex items-center gap-1 rounded-full border border-dashed border-zinc-300 dark:border-zinc-700 px-3 py-1 text-xs text-zinc-600 dark:text-zinc-400 hover:border-brand-500 hover:text-brand-700 dark:hover:text-brand-300"
        >
          <FiPlus className="h-3 w-3" />
          Save current
        </button>
      ) : null}

      {custom.length > 0 ? (
        <button
          type="button"
          onClick={() => {
            if (!confirm('Delete all custom saved views?')) return
            setCustom([])
            persistCustom([])
            if (custom.some((v) => v.id === activeId)) {
              setActiveId(null)
              persistActive(null)
            }
          }}
          className="inline-flex items-center gap-1 text-[11px] text-zinc-400 hover:text-rose-500 ml-1"
          title="Delete all custom views"
        >
          <FiTrash2 className="h-3 w-3" />
        </button>
      ) : null}
    </div>
  )
}

// Convenience: hydrate filters on first mount based on saved active view.
export function useInitialFiltersFromSavedView(
  defaultFilters: JobFiltersValue,
): JobFiltersValue {
  const id = loadActiveViewId()
  if (!id) return defaultFilters
  const all = [...BUILTIN_VIEWS, ...loadCustom()]
  return all.find((v) => v.id === id)?.filters ?? defaultFilters
}
