import { useEffect, useState } from 'react'
import {
  SettingsCard,
  FieldRow,
  TextInput,
  Select,
  Toggle,
} from './_components'
import { useSettings, useUpdateSettings } from '@/hooks/useSettings'

export default function AutomationScreen() {
  const settings = useSettings()
  const updateSettings = useUpdateSettings()

  const autoEnabled = settings.data?.auto_search_enabled ?? true
  const frequency = String(settings.data?.search_frequency_hours ?? 6)
  const emailEnabled = settings.data?.email_notifications ?? true

  const [minMatch, setMinMatch] = useState<string>('')
  useEffect(() => {
    if (settings.data) setMinMatch(String(settings.data.min_match_score_alert ?? 0))
  }, [settings.data?.min_match_score_alert])

  const commitMinMatch = () => {
    if (!settings.data) return
    const n = Number(minMatch)
    if (!Number.isFinite(n) || n < 0 || n > 100) {
      setMinMatch(String(settings.data.min_match_score_alert))
      return
    }
    if (n === settings.data.min_match_score_alert) return
    updateSettings.mutate({ min_match_score_alert: n })
  }

  return (
    <div className="space-y-8">
      <SettingsCard title="Auto-search" subtitle="Runs every N hours and updates the queue">
        <FieldRow label="Enabled">
          <Toggle
            checked={autoEnabled}
            onChange={(v) => updateSettings.mutate({ auto_search_enabled: v })}
            label="Enable auto-search"
          />
        </FieldRow>
        <FieldRow label="Frequency">
          <Select
            value={frequency}
            onChange={(v) => updateSettings.mutate({ search_frequency_hours: Number(v) })}
            options={[
              { value: '1', label: '1 hour' },
              { value: '3', label: '3 hours' },
              { value: '6', label: '6 hours' },
              { value: '12', label: '12 hours' },
              { value: '24', label: '24 hours' },
            ]}
          />
        </FieldRow>
        <FieldRow label="Last run" hint="ETA next run: 4h 12m" align="start">
          <span className="text-sm text-zinc-700 dark:text-zinc-300 font-mono">
            2026-05-04 09:00 UTC
          </span>
        </FieldRow>
      </SettingsCard>

      <SettingsCard
        title="Notifications"
        subtitle="Email me when something interesting hits the queue"
      >
        <FieldRow label="Email alerts">
          <Toggle
            checked={emailEnabled}
            onChange={(v) => updateSettings.mutate({ email_notifications: v })}
            label="Enable email alerts"
          />
        </FieldRow>
        <FieldRow label="Min match for alert" hint="Score threshold to trigger an email. Saves on blur." align="start">
          <TextInput
            type="number"
            min={0}
            max={100}
            value={minMatch}
            disabled={!settings.data || updateSettings.isPending}
            onChange={(e) => setMinMatch(e.target.value)}
            onBlur={commitMinMatch}
            onKeyDown={(e) => {
              if (e.key === 'Enter') (e.target as HTMLInputElement).blur()
            }}
          />
        </FieldRow>
      </SettingsCard>
    </div>
  )
}
