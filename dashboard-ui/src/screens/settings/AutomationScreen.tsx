import { useEffect, useState } from 'react'
import {
  SettingsCard,
  FieldRow,
  TextInput,
  Select,
  Toggle,
} from './_components'
import { useSessionStatus } from '@/hooks/useSession'
import { useSettings, useUpdateSettings } from '@/hooks/useSettings'

const RECOMMENDED_MIN_MINUTES = 30
const FREQUENCY_OPTIONS = [
  { value: '2', label: '2 minutes — testing only ⚠️' },
  { value: '5', label: '5 minutes — testing only ⚠️' },
  { value: '15', label: '15 minutes (rate-limit risk)' },
  { value: '30', label: '30 minutes (recommended minimum)' },
  { value: '60', label: '1 hour' },
  { value: '180', label: '3 hours' },
  { value: '360', label: '6 hours' },
  { value: '720', label: '12 hours' },
  { value: '1440', label: '24 hours' },
]

function fmtCadence(m: number): string {
  if (m < 60) return `${m}m`
  if (m % 60 === 0) return `${m / 60}h`
  return `${Math.floor(m / 60)}h ${m % 60}m`
}

export default function AutomationScreen() {
  const settings = useSettings()
  const updateSettings = useUpdateSettings()
  const { data: sessionStatus } = useSessionStatus()

  const autoEnabled = settings.data?.auto_search_enabled ?? true
  const frequencyMinutes = settings.data?.search_frequency_minutes ?? 60
  const emailEnabled = settings.data?.email_notifications ?? true
  const lastRun = sessionStatus?.next_trigger?.last_run_at
  const nextAt = sessionStatus?.next_trigger?.next_at

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

  // Round to a known option; if user has a custom value (legacy hours-only)
  // we still match 60/180/360/720/1440 cleanly. Otherwise fall through to
  // the closest stamp.
  const optionValue = FREQUENCY_OPTIONS.find((o) => Number(o.value) === frequencyMinutes)
    ? String(frequencyMinutes)
    : String(frequencyMinutes)

  const isLowFrequency = frequencyMinutes < RECOMMENDED_MIN_MINUTES

  return (
    <div className="space-y-8">
      <SettingsCard title="Auto-search" subtitle="The scraper auto-fires on this cadence when enabled">
        <FieldRow label="Enabled">
          <Toggle
            checked={autoEnabled}
            onChange={(v) => updateSettings.mutate({ auto_search_enabled: v })}
            label="Enable auto-search"
          />
        </FieldRow>
        <FieldRow label="Frequency" hint={isLowFrequency ? 'Below recommended 30-minute floor — only use for short testing windows. Sustained sub-30-minute polling risks LinkedIn rate limiting / detection.' : undefined} align="start">
          <Select
            value={optionValue}
            onChange={(v) => updateSettings.mutate({ search_frequency_minutes: Number(v) })}
            options={FREQUENCY_OPTIONS}
          />
        </FieldRow>
        <FieldRow label="Schedule" align="start">
          <div className="text-sm text-zinc-700 dark:text-zinc-300 space-y-0.5">
            <div>
              Cadence:{' '}
              <span className="font-mono">{fmtCadence(frequencyMinutes)}</span>
              {isLowFrequency ? (
                <span className="ml-2 text-amber-700 dark:text-amber-400 text-xs">
                  ⚠️ testing window
                </span>
              ) : null}
            </div>
            <div className="text-xs text-zinc-500 dark:text-zinc-400">
              Last run: {lastRun ? new Date(lastRun).toLocaleString() : '—'}
            </div>
            <div className="text-xs text-zinc-500 dark:text-zinc-400">
              Next at: {autoEnabled && nextAt ? new Date(nextAt).toLocaleString() : 'auto-search disabled'}
            </div>
          </div>
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
