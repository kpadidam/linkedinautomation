import { useQuery } from '@tanstack/react-query'

export interface SetupItem {
  id: 'profile' | 'roles' | 'resume' | 'llm' | 'sheets' | string
  label: string
  complete: boolean
  optional?: boolean
  hint?: string // route to navigate to (e.g. "/settings/profile")
}

export interface SetupStatus {
  complete: boolean
  missing_required: string[]
  items: SetupItem[]
}

export function useSetupStatus() {
  return useQuery({
    queryKey: ['setup-status'],
    queryFn: async () => {
      const r = await fetch('/api/setup/status')
      if (!r.ok) throw new Error(`${r.status}`)
      return (await r.json()) as SetupStatus
    },
    refetchInterval: 5000,
  })
}
