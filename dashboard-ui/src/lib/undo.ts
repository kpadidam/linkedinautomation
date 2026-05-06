import { create } from 'zustand'

export interface UndoEntry {
  id: number
  label: string
  undo: () => void | Promise<void>
  expiresAt: number
}

interface UndoStore {
  current: UndoEntry | null
  push: (entry: { label: string; undo: () => void | Promise<void> }) => void
  runUndo: () => void
  clear: () => void
}

const TTL_MS = 5000
let pendingTimeout: ReturnType<typeof setTimeout> | null = null

function clearPending() {
  if (pendingTimeout) {
    clearTimeout(pendingTimeout)
    pendingTimeout = null
  }
}

export const useUndoStore = create<UndoStore>((set, get) => ({
  current: null,
  push: ({ label, undo }) => {
    clearPending()
    const id = Date.now()
    const entry: UndoEntry = { id, label, undo, expiresAt: id + TTL_MS }
    set({ current: entry })
    pendingTimeout = setTimeout(() => {
      // only clear if this entry is still the current one
      const cur = get().current
      if (cur && cur.id === id) set({ current: null })
      pendingTimeout = null
    }, TTL_MS)
  },
  runUndo: () => {
    const cur = get().current
    if (!cur) return
    clearPending()
    set({ current: null })
    try {
      void cur.undo()
    } catch (e) {
      // swallow — undo is best-effort
      console.error('undo failed', e)
    }
  },
  clear: () => {
    clearPending()
    set({ current: null })
  },
}))
