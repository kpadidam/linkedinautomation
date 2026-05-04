import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { markSettingsDirty } from '@/lib/settingsDirty'

export interface AppSettingsSecrets {
  openai_configured: boolean
  groq_configured: boolean
  linkedin_configured: boolean
  sheets_configured: boolean
}

export interface AppSettings {
  enable_resume_matching: boolean
  headless_browser: boolean
  browser_timeout: number
  auto_search_enabled: boolean
  search_frequency_hours: number
  min_match_score_alert: number
  email_notifications: boolean
  secrets: AppSettingsSecrets
}

export type AppSettingsUpdate = Partial<Omit<AppSettings, 'secrets'>>

async function http<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
  })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json() as Promise<T>
}

export function useSettings() {
  return useQuery({
    queryKey: ['settings'],
    queryFn: () => http<AppSettings>('/api/settings'),
    refetchInterval: 30_000,
    staleTime: 10_000,
  })
}

export function useUpdateSettings() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: AppSettingsUpdate) =>
      http<AppSettings>('/api/settings', {
        method: 'PUT',
        body: JSON.stringify(body),
      }),
    onSuccess: (data) => {
      qc.setQueryData(['settings'], data)
      qc.invalidateQueries({ queryKey: ['settings'] })
      markSettingsDirty()
    },
  })
}
