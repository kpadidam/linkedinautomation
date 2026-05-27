import { useEffect } from 'react'
import { NavLink } from 'react-router-dom'
import {
  FiGrid,
  FiInbox,
  FiSend,
  FiTrello,
  FiActivity,
  FiSettings,
  FiCalendar,
  FiChevronLeft,
  FiChevronRight,
} from 'react-icons/fi'
import { cn } from '@/lib/utils'
import { useSidebar } from '@/lib/sidebar'

const links = [
  { to: '/', icon: FiGrid, label: 'Dashboard', end: true },
  { to: '/review-queue', icon: FiInbox, label: 'Review Queue' },
  { to: '/apply-queue', icon: FiSend, label: 'Apply Queue' },
  { to: '/apply-runs', icon: FiActivity, label: 'Apply Runs' },
  { to: '/pipeline', icon: FiTrello, label: 'Pipeline' },
  { to: '/calendar', icon: FiCalendar, label: 'Calendar' },
  { to: '/session', icon: FiActivity, label: 'Session' },
  { to: '/settings', icon: FiSettings, label: 'Settings' },
]

export function Sidebar() {
  const collapsed = useSidebar((s) => s.collapsed)
  const toggle = useSidebar((s) => s.toggle)

  // ⌘\ (or Ctrl+\) to toggle collapse — match the button's tooltip.
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === '\\') {
        e.preventDefault()
        toggle()
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [toggle])

  return (
    <aside
      className={cn(
        'hidden md:flex shrink-0 flex-col border-r border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 transition-[width] duration-200 ease-out',
        collapsed ? 'w-14' : 'w-56',
      )}
    >
      <div
        className={cn(
          'h-14 flex items-center border-b border-zinc-200 dark:border-zinc-800',
          collapsed ? 'justify-center px-0' : 'justify-between px-4',
        )}
      >
        {!collapsed ? (
          <div className="font-semibold tracking-tight">
            LinkedIn<span className="text-brand-600">.</span>Hunter
          </div>
        ) : null}
        <button
          type="button"
          onClick={toggle}
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          title={collapsed ? 'Expand (⌘\\)' : 'Collapse (⌘\\)'}
          className="inline-flex items-center justify-center h-7 w-7 rounded-md text-zinc-500 hover:bg-zinc-100 dark:hover:bg-zinc-800 hover:text-zinc-900 dark:hover:text-zinc-50"
        >
          {collapsed ? <FiChevronRight className="h-4 w-4" /> : <FiChevronLeft className="h-4 w-4" />}
        </button>
      </div>
      <nav className={cn('flex-1 space-y-0.5', collapsed ? 'p-1.5' : 'p-2')}>
        {links.map(({ to, icon: Icon, label, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            title={collapsed ? label : undefined}
            className={({ isActive }) =>
              cn(
                'flex items-center rounded-md text-sm transition',
                collapsed ? 'justify-center h-9 w-9 mx-auto' : 'gap-3 px-3 py-2',
                isActive
                  ? 'bg-zinc-100 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-50 font-medium'
                  : 'text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800 hover:text-zinc-900 dark:hover:text-zinc-50',
              )
            }
          >
            <Icon className="h-4 w-4 shrink-0" />
            {!collapsed ? <span className="truncate">{label}</span> : null}
          </NavLink>
        ))}
      </nav>
      {!collapsed ? (
        <div className="p-3 text-xs text-zinc-500 dark:text-zinc-500 border-t border-zinc-200 dark:border-zinc-800">
          v0.1 · Phase 1
        </div>
      ) : null}
    </aside>
  )
}
