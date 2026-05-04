import { Link } from 'react-router-dom'
import { FiAlertCircle, FiCheckCircle, FiArrowRight } from 'react-icons/fi'
import { useSetupStatus } from '@/hooks/useSetup'
import { cn } from '@/lib/utils'

/**
 * Compact "Finish setup (3 of 5)" strip — only renders when the required
 * items aren't all complete. Each remaining item is a link to its hint route.
 */
export function SetupBanner() {
  const { data } = useSetupStatus()
  if (!data || data.complete) return null

  const requiredItems = data.items.filter((i) => !i.optional)
  const completedRequired = requiredItems.filter((i) => i.complete).length
  const totalRequired = requiredItems.length
  const remaining = data.items.filter((i) => !i.complete)

  return (
    <div
      className={cn(
        'rounded-lg border border-amber-300/70 bg-amber-50 dark:border-amber-700/50 dark:bg-amber-950/40',
        'px-4 py-3 flex flex-wrap items-center gap-x-4 gap-y-2',
      )}
    >
      <div className="flex items-center gap-2 text-amber-900 dark:text-amber-200">
        <FiAlertCircle className="h-4 w-4 shrink-0" />
        <span className="text-sm font-semibold">
          Finish setup ({completedRequired} of {totalRequired})
        </span>
      </div>
      <ul className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-amber-900/90 dark:text-amber-100/90">
        {remaining.map((item, i) => (
          <li key={item.id} className="flex items-center gap-1">
            {i > 0 ? <span className="text-amber-700/50 dark:text-amber-300/40">·</span> : null}
            {item.hint ? (
              <Link
                to={item.hint}
                className="inline-flex items-center gap-1 underline-offset-2 hover:underline"
              >
                {item.complete ? (
                  <FiCheckCircle className="h-3.5 w-3.5 text-emerald-600" />
                ) : null}
                {item.label}
                {item.optional ? (
                  <span className="text-[10px] uppercase tracking-wide text-amber-700/70 dark:text-amber-300/60 ml-1">
                    optional
                  </span>
                ) : null}
                <FiArrowRight className="h-3 w-3 opacity-60" />
              </Link>
            ) : (
              <span>{item.label}</span>
            )}
          </li>
        ))}
      </ul>
    </div>
  )
}
