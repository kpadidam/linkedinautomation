import { useEffect, useState } from 'react'
import { FiChevronUp, FiChevronDown } from 'react-icons/fi'
import {
  SettingsCard,
  FieldRow,
  TextInput,
  Toggle,
} from './_components'
import { useSessionStatus } from '@/hooks/useSession'
import { useSettings, useUpdateSettings } from '@/hooks/useSettings'
import { cn } from '@/lib/utils'

// Hard floor — any value below this is rejected client-side. The 30-minute
// minimum is the rate-limit guardrail; sustained sub-30m polling will get
// the LinkedIn account flagged. To bypass for testing hit /api/settings
// directly with curl.
const FREQUENCY_MIN_MINUTES = 30
const FREQUENCY_MAX_MINUTES = 1440 // 24h
const FREQUENCY_STEP_MINUTES = 5

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

  // Local draft for the stepper so users can type freely; we commit on
  // blur or stepper-button click so the server isn't hammered per keystroke.
  const [freqDraft, setFreqDraft] = useState<string>('')
  useEffect(() => {
    if (settings.data) setFreqDraft(String(settings.data.search_frequency_minutes))
  }, [settings.data?.search_frequency_minutes])

  const commitFrequency = (raw: string | number) => {
    const n = Math.round(Number(raw))
    if (!Number.isFinite(n)) {
      setFreqDraft(String(frequencyMinutes))
      return
    }
    const clamped = Math.min(
      FREQUENCY_MAX_MINUTES,
      Math.max(FREQUENCY_MIN_MINUTES, n),
    )
    setFreqDraft(String(clamped))
    if (clamped === frequencyMinutes) return
    updateSettings.mutate({ search_frequency_minutes: clamped })
  }
  const stepFrequency = (delta: number) => {
    const base = Number(freqDraft) || frequencyMinutes
    commitFrequency(base + delta)
  }

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

  const draftValue = Number(freqDraft) || frequencyMinutes
  const atMin = draftValue <= FREQUENCY_MIN_MINUTES
  const atMax = draftValue >= FREQUENCY_MAX_MINUTES

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
        <FieldRow
          label="Frequency"
          hint={`Minutes between runs. Minimum ${FREQUENCY_MIN_MINUTES}m (rate-limit floor), maximum 24h. ↑/↓ keys or buttons step by ${FREQUENCY_STEP_MINUTES}m; type any value in-between.`}
          align="start"
        >
          <div className="flex items-center gap-3">
            <div className="inline-flex items-stretch rounded-xl border border-zinc-900/30 dark:border-zinc-100/30 bg-white dark:bg-zinc-950 overflow-hidden">
              <button
                type="button"
                onClick={() => stepFrequency(-FREQUENCY_STEP_MINUTES)}
                disabled={atMin || updateSettings.isPending}
                className={cn(
                  'px-3 flex items-center justify-center hover:bg-zinc-100 dark:hover:bg-zinc-900 transition-colors',
                  atMin && 'opacity-30 cursor-not-allowed',
                )}
                aria-label={`Decrease by ${FREQUENCY_STEP_MINUTES} minutes`}
                title={`-${FREQUENCY_STEP_MINUTES}m`}
              >
                <FiChevronDown className="h-4 w-4" />
              </button>
              <input
                type="number"
                min={FREQUENCY_MIN_MINUTES}
                max={FREQUENCY_MAX_MINUTES}
                step={1}
                value={freqDraft}
                onChange={(e) => setFreqDraft(e.target.value)}
                onBlur={() => commitFrequency(freqDraft)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') (e.target as HTMLInputElement).blur()
                  if (e.key === 'ArrowUp') {
                    e.preventDefault()
                    stepFrequency(FREQUENCY_STEP_MINUTES)
                  }
                  if (e.key === 'ArrowDown') {
                    e.preventDefault()
                    stepFrequency(-FREQUENCY_STEP_MINUTES)
                  }
                }}
                className={cn(
                  'w-20 text-center text-sm font-mono tabular-nums px-2 py-2',
                  'bg-transparent border-x border-zinc-900/15 dark:border-zinc-100/15',
                  'focus:outline-none focus:bg-zinc-50 dark:focus:bg-zinc-900',
                )}
                aria-label="Auto-search frequency in minutes"
              />
              <button
                type="button"
                onClick={() => stepFrequency(FREQUENCY_STEP_MINUTES)}
                disabled={atMax || updateSettings.isPending}
                className={cn(
                  'px-3 flex items-center justify-center hover:bg-zinc-100 dark:hover:bg-zinc-900 transition-colors',
                  atMax && 'opacity-30 cursor-not-allowed',
                )}
                aria-label={`Increase by ${FREQUENCY_STEP_MINUTES} minutes`}
                title={`+${FREQUENCY_STEP_MINUTES}m`}
              >
                <FiChevronUp className="h-4 w-4" />
              </button>
            </div>
            <span className="text-sm text-zinc-500 dark:text-zinc-400">
              minutes ·{' '}
              <span className="font-mono text-zinc-700 dark:text-zinc-300">
                {fmtCadence(draftValue)}
              </span>
            </span>
          </div>
        </FieldRow>
        <FieldRow label="Schedule" align="start">
          <div className="text-sm text-zinc-700 dark:text-zinc-300 space-y-0.5">
            <div>
              Cadence:{' '}
              <span className="font-mono">{fmtCadence(frequencyMinutes)}</span>
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
