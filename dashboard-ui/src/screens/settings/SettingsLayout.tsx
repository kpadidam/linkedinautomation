import { NavLink, Outlet } from 'react-router-dom'
import { FiFileText, FiSliders, FiKey, FiZap, FiDatabase, FiSearch } from 'react-icons/fi'
import { useSessionStatus } from '@/hooks/useSession'
import { cn } from '@/lib/utils'

const SECTIONS = [
  { to: 'profile', label: 'Profile & Resume', icon: FiFileText },
  { to: 'roles', label: 'Search Roles', icon: FiSliders },
  { to: 'integrations', label: 'Integrations', icon: FiKey },
  { to: 'automation', label: 'Automation', icon: FiZap },
  { to: 'system', label: 'System', icon: FiDatabase },
] as const

export default function SettingsLayout() {
  const { data: status } = useSessionStatus()
  const isLive = !!status?.running

  return (
    <div className="min-h-full bg-white dark:bg-zinc-950 text-zinc-900 dark:text-zinc-50">
      <PageHeader isLive={isLive} />
      <div className="grid grid-cols-[260px_1fr] min-h-[calc(100vh-57px)]">
        <SubNav />
        <div className="border-l border-zinc-900/15 dark:border-zinc-100/15">
          <div className="max-w-[920px] px-8 py-8">
            <Outlet />
          </div>
        </div>
      </div>
    </div>
  )
}

function PageHeader({ isLive }: { isLive: boolean }) {
  return (
    <header className="px-8 py-4 flex items-center justify-between border-b border-zinc-900/15 dark:border-zinc-100/15">
      <div className="flex items-baseline gap-2">
        <h1 className="text-lg font-semibold tracking-tight">Settings</h1>
        <span className="text-sm text-zinc-500 dark:text-zinc-400">
          · preferences, integrations, system
        </span>
      </div>
      <div className="flex items-center gap-3">
        <button
          type="button"
          className={cn(
            'inline-flex items-center gap-2 rounded-xl border border-zinc-900/30 dark:border-zinc-100/30 pl-3 pr-2 py-2',
            'text-sm text-zinc-500 dark:text-zinc-400 min-w-[280px]',
            'hover:border-zinc-900 dark:hover:border-zinc-100 transition-colors',
          )}
          aria-label="Open command palette"
        >
          <FiSearch className="h-4 w-4" />
          <span className="flex-1 text-left">Jump to job, action…</span>
          <kbd className="rounded-md border border-zinc-900/30 dark:border-zinc-100/30 px-1.5 py-0.5 text-[10px] font-mono">
            ⌘K
          </kbd>
        </button>
        <span
          className={cn(
            'inline-flex items-center rounded-xl border px-3 py-1.5 text-sm',
            isLive
              ? 'border-emerald-500/50 bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-300'
              : 'border-zinc-900/30 dark:border-zinc-100/30 bg-white dark:bg-zinc-950 text-zinc-500 dark:text-zinc-400',
          )}
        >
          {isLive ? 'live' : 'idle'}
        </span>
      </div>
    </header>
  )
}

function SubNav() {
  return (
    <aside className="px-5 py-6">
      <div className="text-[11px] font-medium tracking-[0.14em] text-zinc-500 dark:text-zinc-400 uppercase mb-3 px-3">
        Preferences
      </div>
      <nav className="space-y-1">
        {SECTIONS.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition',
                isActive
                  ? 'border border-zinc-900 dark:border-zinc-100 text-zinc-900 dark:text-zinc-50'
                  : 'border border-transparent text-zinc-700 dark:text-zinc-300 hover:bg-zinc-100/50 dark:hover:bg-zinc-900/50',
              )
            }
          >
            <Icon className="h-4 w-4 shrink-0" />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>
    </aside>
  )
}
