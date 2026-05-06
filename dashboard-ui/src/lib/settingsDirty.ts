import { create } from 'zustand'

interface SettingsDirtyState {
  dirty: boolean
  dirtySince: number | null
  markDirty: () => void
  clearDirty: () => void
}

/**
 * Tracks whether settings were updated since the last session start.
 *
 * Flow:
 *   useUpdateSettings.onSuccess  → markDirty()
 *   useStartSession.onSuccess    → clearDirty()
 *   Header reads `dirty` and shows an amber pill while a session is running.
 */
export const useSettingsDirty = create<SettingsDirtyState>((set) => ({
  dirty: false,
  dirtySince: null,
  markDirty: () => set({ dirty: true, dirtySince: Date.now() }),
  clearDirty: () => set({ dirty: false, dirtySince: null }),
}))

// Plain helpers so non-component code (mutation callbacks) can mutate the store.
export function markSettingsDirty() {
  useSettingsDirty.getState().markDirty()
}

export function clearSettingsDirty() {
  useSettingsDirty.getState().clearDirty()
}
