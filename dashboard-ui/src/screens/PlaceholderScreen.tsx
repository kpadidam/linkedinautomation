import type { IconType } from 'react-icons'
import { FiClock } from 'react-icons/fi'

export function PlaceholderScreen({
  title,
  phase,
  icon: Icon = FiClock,
}: {
  title: string
  phase: string
  icon?: IconType
}) {
  return (
    <div className="p-4 md:p-6">
      <h1 className="text-xl font-semibold">{title}</h1>
      <div className="mt-6 surface rounded-lg p-8 flex items-center gap-4">
        <Icon className="h-10 w-10 text-zinc-400" />
        <div>
          <div className="font-medium">Coming in {phase}</div>
          <div className="text-sm text-zinc-500 dark:text-zinc-400">
            This screen is scaffolded but not wired yet.
          </div>
        </div>
      </div>
    </div>
  )
}
