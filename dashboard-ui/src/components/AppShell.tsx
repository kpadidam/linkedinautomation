import { Outlet } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { Header } from './Header'
import { UndoToast } from './UndoToast'

export function AppShell() {
  return (
    <div className="flex h-full">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <Header />
        <main className="flex-1 overflow-auto bg-zinc-50 dark:bg-zinc-950">
          <Outlet />
        </main>
      </div>
      <UndoToast />
    </div>
  )
}
