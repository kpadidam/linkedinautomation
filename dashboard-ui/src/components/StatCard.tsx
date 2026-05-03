import type { IconType } from 'react-icons'

export function StatCard({
  label,
  value,
  hint,
  icon: Icon,
}: {
  label: string
  value: string | number
  hint?: string
  icon?: IconType
}) {
  return (
    <div className="surface rounded-lg p-4">
      <div className="flex items-center justify-between">
        <div className="text-xs uppercase tracking-wide text-zinc-500 dark:text-zinc-400">{label}</div>
        {Icon ? <Icon className="h-4 w-4 text-zinc-400" /> : null}
      </div>
      <div className="mt-2 text-2xl font-semibold tabular-nums">{value}</div>
      {hint ? <div className="mt-1 text-xs text-zinc-500 dark:text-zinc-400">{hint}</div> : null}
    </div>
  )
}
