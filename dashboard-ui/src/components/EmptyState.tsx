import type { IconType } from 'react-icons'

export function EmptyState({
  icon: Icon,
  title,
  description,
}: {
  icon?: IconType
  title: string
  description?: string
}) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      {Icon ? <Icon className="h-10 w-10 text-zinc-400" /> : null}
      <div className="mt-3 font-medium">{title}</div>
      {description ? (
        <div className="mt-1 text-sm text-zinc-500 dark:text-zinc-400 max-w-sm">{description}</div>
      ) : null}
    </div>
  )
}
