import { useEffect, useState } from 'react'
import { FiRotateCcw } from 'react-icons/fi'
import { useUndoStore } from '@/lib/undo'

const TTL_MS = 5000

export function UndoToast() {
  const current = useUndoStore((s) => s.current)
  const runUndo = useUndoStore((s) => s.runUndo)
  const [, setTick] = useState(0)

  // re-render every 80ms while a toast is active so the progress bar drains smoothly
  useEffect(() => {
    if (!current) return
    const i = setInterval(() => setTick((t) => t + 1), 80)
    return () => clearInterval(i)
  }, [current])

  if (!current) return null

  const remaining = Math.max(0, current.expiresAt - Date.now())
  const pct = Math.max(0, Math.min(100, (remaining / TTL_MS) * 100))

  return (
    <div
      role="status"
      aria-live="polite"
      className="fixed bottom-4 left-1/2 -translate-x-1/2 z-40 flex items-center gap-3 pl-4 pr-1 py-1 rounded-full bg-zinc-900 dark:bg-zinc-100 text-zinc-100 dark:text-zinc-900 shadow-xl overflow-hidden"
    >
      <span className="text-sm font-medium whitespace-nowrap">{current.label}</span>
      <button
        type="button"
        onClick={runUndo}
        className="flex items-center gap-1 px-3 py-1.5 rounded-full text-sm font-semibold bg-zinc-700 dark:bg-zinc-300 hover:bg-zinc-600 dark:hover:bg-zinc-400 text-white dark:text-zinc-900"
      >
        <FiRotateCcw className="h-3.5 w-3.5" /> Undo
      </button>
      <div
        className="absolute left-0 bottom-0 h-0.5 bg-brand-500 transition-[width] duration-75 ease-linear"
        style={{ width: `${pct}%` }}
        aria-hidden
      />
    </div>
  )
}
