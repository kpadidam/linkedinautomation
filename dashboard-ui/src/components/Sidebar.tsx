import { NavLink } from 'react-router-dom'
import { FiGrid, FiInbox, FiTrello, FiActivity } from 'react-icons/fi'
import { cn } from '@/lib/utils'

// Calendar + Settings live in the header's right rail (utility nav).
// The sidebar is reserved for working surfaces.
const links = [
  { to: '/', icon: FiGrid, label: 'Dashboard', end: true },
  { to: '/review-queue', icon: FiInbox, label: 'Review Queue' },
  { to: '/pipeline', icon: FiTrello, label: 'Pipeline' },
  { to: '/session', icon: FiActivity, label: 'Session' },
]

export function Sidebar() {
  return (
    <aside className="hidden md:flex w-56 shrink-0 flex-col border-r border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900">
      <div className="h-14 px-4 flex items-center border-b border-zinc-200 dark:border-zinc-800">
        <div className="font-semibold tracking-tight">LinkedIn<span className="text-brand-600">.</span>Hunter</div>
      </div>
      <nav className="flex-1 p-2 space-y-0.5">
        {links.map(({ to, icon: Icon, label, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 px-3 py-2 rounded-md text-sm transition',
                isActive
                  ? 'bg-zinc-100 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-50 font-medium'
                  : 'text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800 hover:text-zinc-900 dark:hover:text-zinc-50'
              )
            }
          >
            <Icon className="h-4 w-4" />
            {label}
          </NavLink>
        ))}
      </nav>
      <div className="p-3 text-xs text-zinc-500 dark:text-zinc-500 border-t border-zinc-200 dark:border-zinc-800">
        v0.1 · Phase 1
      </div>
    </aside>
  )
}
