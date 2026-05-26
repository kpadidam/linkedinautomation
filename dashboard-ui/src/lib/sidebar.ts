import { create } from 'zustand'

const STORAGE_KEY = 'sidebar.collapsed.v1'

function readInitial(): boolean {
  if (typeof window === 'undefined') return false
  try {
    return window.localStorage.getItem(STORAGE_KEY) === '1'
  } catch {
    return false
  }
}

function persist(collapsed: boolean) {
  try {
    window.localStorage.setItem(STORAGE_KEY, collapsed ? '1' : '0')
  } catch {
    // localStorage unavailable; non-fatal
  }
}

interface SidebarState {
  collapsed: boolean
  toggle: () => void
  setCollapsed: (v: boolean) => void
}

export const useSidebar = create<SidebarState>((set) => ({
  collapsed: readInitial(),
  toggle: () =>
    set((s) => {
      const next = !s.collapsed
      persist(next)
      return { collapsed: next }
    }),
  setCollapsed: (v) => {
    persist(v)
    set({ collapsed: v })
  },
}))
