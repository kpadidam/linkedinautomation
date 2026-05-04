import type { IconType } from 'react-icons'
import { FiArrowUpRight } from 'react-icons/fi'
import { Link } from 'react-router-dom'
import { cn } from '@/lib/utils'

interface CommonProps {
  label: string
  value: string | number
  hint?: string
  icon?: IconType
  /** When provided, the card becomes a clickable Link to this route. */
  to?: string
  /** Tooltip / aria — surfaces what clicking will do. */
  title?: string
}

export function StatCard(props: CommonProps) {
  const { label, value, hint, icon: Icon, to, title } = props

  const inner = (
    <>
      <div className="flex items-center justify-between">
        <div className="text-xs uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
          {label}
        </div>
        {Icon ? <Icon className="h-4 w-4 text-zinc-400" /> : null}
      </div>
      <div className="mt-2 text-2xl font-semibold tabular-nums">{value}</div>
      {hint ? (
        <div className="mt-1 text-xs text-zinc-500 dark:text-zinc-400">{hint}</div>
      ) : null}
      {to ? (
        <FiArrowUpRight
          aria-hidden
          className="absolute top-3 right-3 h-3.5 w-3.5 text-zinc-300 opacity-0 group-hover:opacity-100 transition-opacity"
        />
      ) : null}
    </>
  )

  if (to) {
    return (
      <Link
        to={to}
        title={title ?? `Open ${label}`}
        className={cn(
          'group surface rounded-lg p-4 relative block',
          'hover:border-brand-500 dark:hover:border-brand-500/60',
          'hover:bg-zinc-50/60 dark:hover:bg-zinc-900/60',
          'transition-colors',
        )}
      >
        {inner}
      </Link>
    )
  }

  return <div className="surface rounded-lg p-4 relative">{inner}</div>
}
