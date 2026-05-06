import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { markSettingsDirty } from '@/lib/settingsDirty'

export type SecretSource = 'db' | 'env' | null

export interface AppSettingsSecrets {
  openai_configured: boolean
  openai_source: SecretSource
  groq_configured: boolean
  groq_source: SecretSource
  linkedin_configured: boolean
  linkedin_source: SecretSource
  sheets_configured: boolean
  sheets_source: SecretSource
}

export interface AppSettings {
  enable_resume_matching: boolean
  headless_browser: boolean
  browser_timeout: number
  auto_search_enabled: boolean
  /** Legacy hour-precision cadence. Prefer ``search_frequency_minutes``. */
  search_frequency_hours: number
  /** Effective minute-precision cadence (canonical). */
  search_frequency_minutes: number
  min_match_score_alert: number
  email_notifications: boolean
  secrets: AppSettingsSecrets
}

export interface AppSettingsUpdate {
  enable_resume_matching?: boolean
  headless_browser?: boolean
  browser_timeout?: number
  auto_search_enabled?: boolean
  search_frequency_hours?: number
  search_frequency_minutes?: number
  min_match_score_alert?: number
  email_notifications?: boolean
  // Secrets — empty string clears (falls back to .env). undefined = no change.
  openai_api_key?: string
  groq_api_key?: string
  linkedin_email?: string
  linkedin_password?: string
}

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
