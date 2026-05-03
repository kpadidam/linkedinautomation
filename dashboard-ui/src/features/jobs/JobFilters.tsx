import { FiSearch, FiFilter, FiX } from 'react-icons/fi'

export interface JobFiltersValue {
  q: string
  status: string
  minScore: number
}

export function JobFilters({
  value,
  onChange,
}: {
  value: JobFiltersValue
  onChange: (v: JobFiltersValue) => void
}) {
  const clear = () => onChange({ q: '', status: '', minScore: 0 })
  const dirty = value.q || value.status || value.minScore > 0

  return (
    <div className="flex flex-wrap items-center gap-2">
      <div className="relative flex-1 min-w-[200px]">
        <FiSearch className="absolute left-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-400" />
        <input
          className="input pl-8"
          placeholder="Search title, company…"
          value={value.q}
          onChange={(e) => onChange({ ...value, q: e.target.value })}
        />
      </div>
      <select
        className="input w-auto"
        value={value.status}
        onChange={(e) => onChange({ ...value, status: e.target.value })}
      >
        <option value="">All status</option>
        <option value="new">New</option>
        <option value="saved">Saved</option>
        <option value="applied">Applied</option>
        <option value="interviewing">Interviewing</option>
        <option value="offer">Offer</option>
        <option value="rejected">Rejected</option>
      </select>
      <div className="flex items-center gap-2 surface rounded-md px-3 py-1.5">
        <FiFilter className="h-4 w-4 text-zinc-400" />
        <span className="text-sm text-zinc-600 dark:text-zinc-400">Min score</span>
        <input
          type="number"
          min={0}
          max={100}
          className="w-14 bg-transparent text-sm tabular-nums focus:outline-none"
          value={value.minScore || ''}
          placeholder="0"
          onChange={(e) => onChange({ ...value, minScore: Number(e.target.value) || 0 })}
        />
        <span className="text-sm text-zinc-400">%</span>
      </div>
      {dirty ? (
        <button className="btn-ghost" onClick={clear}>
          <FiX className="h-4 w-4" /> Clear
        </button>
      ) : null}
    </div>
  )
}
