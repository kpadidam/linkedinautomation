import { useEffect, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { FiDownload } from 'react-icons/fi'
import {
  SettingsCard,
  FieldRow,
  TextInput,
  Select,
  Toggle,
  GhostButton,
  StatusOk,
  StatusBad,
} from './_components'
import { useSettings, useUpdateSettings } from '@/hooks/useSettings'

async function http<T>(url: string, init?: RequestInit): Promise<T> {
  const r = await fetch(url, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
  })
  if (!r.ok) throw new Error(`${r.status}`)
  return r.json() as Promise<T>
}

export default function SystemScreen() {
  const settings = useSettings()
  const updateSettings = useUpdateSettings()

  // Local-mirror for the BROWSER_TIMEOUT input so users can type freely; we
  // commit on blur. Keep it in sync when the server value changes.
  const [browserTimeout, setBrowserTimeout] = useState<string>('')
  useEffect(() => {
    if (settings.data) setBrowserTimeout(String(settings.data.browser_timeout ?? ''))
  }, [settings.data?.browser_timeout])

  const [cleanupDays, setCleanupDays] = useState('90')

  const health = useQuery({
    queryKey: ['health'],
    queryFn: () => http<{ status: string }>('/api/health'),
    refetchInterval: 30_000,
  })
  const cleanup = useMutation({
    mutationFn: (days: number) =>
      http<{ deleted_records: number }>(`/api/cleanup?days=${days}`, { method: 'POST' }),
  })

  const allOk = health.data?.status === 'healthy'

  const resumeMatching = settings.data?.enable_resume_matching ?? true
  const headless = settings.data?.headless_browser ?? true
  const disabled = !settings.data || updateSettings.isPending

  const commitTimeout = () => {
    if (!settings.data) return
    const n = Number(browserTimeout)
    if (!Number.isFinite(n) || n <= 0) {
      // revert to server value on invalid input
      setBrowserTimeout(String(settings.data.browser_timeout))
      return
    }
    if (n === settings.data.browser_timeout) return
    updateSettings.mutate({ browser_timeout: n })
  }

  return (
    <div className="space-y-8">
      <SettingsCard title="Feature flags" subtitle="Some require a restart">
        <FieldRow label="ENABLE_RESUME_MATCHING">
          <Toggle
            checked={resumeMatching}
            onChange={(v) => updateSettings.mutate({ enable_resume_matching: v })}
            label="Enable resume matching"
          />
        </FieldRow>
        <FieldRow label="HEADLESS_BROWSER">
          <Toggle
            checked={headless}
            onChange={(v) => updateSettings.mutate({ headless_browser: v })}
            label="Run browser headless"
          />
        </FieldRow>
        <FieldRow label="BROWSER_TIMEOUT" hint="In milliseconds. Saves on blur.">
          <TextInput
            type="number"
            value={browserTimeout}
            disabled={disabled}
            onChange={(e) => setBrowserTimeout(e.target.value)}
            onBlur={commitTimeout}
            onKeyDown={(e) => {
              if (e.key === 'Enter') (e.target as HTMLInputElement).blur()
            }}
          />
        </FieldRow>
      </SettingsCard>

      <SettingsCard title="Data" subtitle="Cleanup keeps the DB lean">
        <FieldRow label="Cleanup older than">
          <Select
            value={cleanupDays}
            onChange={setCleanupDays}
            options={[
              { value: '7', label: '7 days' },
              { value: '30', label: '30 days' },
              { value: '60', label: '60 days' },
              { value: '90', label: '90 days' },
              { value: '180', label: '180 days' },
              { value: '365', label: '365 days' },
            ]}
          />
        </FieldRow>
        <FieldRow label="Actions">
          <div className="flex items-center gap-3 flex-wrap">
            <GhostButton
              type="button"
              onClick={() => cleanup.mutate(Number(cleanupDays))}
              disabled={cleanup.isPending}
            >
              {cleanup.isPending ? 'Running…' : 'Run cleanup'}
            </GhostButton>
            <GhostButton type="button" disabled title="Coming soon">
              <FiDownload className="h-4 w-4" />
              Export DB (JSON)
            </GhostButton>
            {cleanup.isSuccess ? (
              <span className="text-sm text-emerald-700 dark:text-emerald-400">
                Deleted {cleanup.data?.deleted_records ?? 0} records
              </span>
            ) : null}
          </div>
        </FieldRow>
        <FieldRow label="Health">
          {allOk ? (
            <StatusOk>API · Sheets · LLM all responding</StatusOk>
          ) : health.isLoading ? (
            <span className="text-sm text-zinc-500">Checking…</span>
          ) : (
            <StatusBad>One or more services not responding</StatusBad>
          )}
        </FieldRow>
      </SettingsCard>
    </div>
  )
}
