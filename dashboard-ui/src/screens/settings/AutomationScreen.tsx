import { useEffect, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { FiAlertOctagon, FiCheck, FiChevronUp, FiChevronDown, FiRefreshCw, FiX, FiZap } from 'react-icons/fi'
import {
  SettingsCard,
  FieldRow,
  Select,
  TextInput,
  Toggle,
} from './_components'
import { useSessionStatus } from '@/hooks/useSession'
import { useSettings, useUpdateSettings } from '@/hooks/useSettings'
import { useCircuitStatus, useResetCircuit } from '@/hooks/useApplyRuns'
import { api } from '@/lib/api'
import { cn, formatRelative } from '@/lib/utils'

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
  // While the user is typing they can briefly hold a sub-30 value before
  // commitFrequency() clamps it back up on blur. Surface a clear error
  // explaining WHY we don't allow it — LinkedIn flags bot-cadence polling.
  const belowMin = draftValue < FREQUENCY_MIN_MINUTES

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
          <div className="space-y-2">
          <div className="flex items-center gap-3">
            <div
              className={cn(
                'inline-flex items-stretch rounded-xl border bg-white dark:bg-zinc-950 overflow-hidden transition-colors',
                belowMin
                  ? 'border-rose-500 dark:border-rose-400'
                  : atMin
                    ? 'border-amber-400 dark:border-amber-500/70'
                    : 'border-zinc-900/30 dark:border-zinc-100/30',
              )}
            >
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
          {belowMin ? (
            <div
              role="alert"
              className="flex items-start gap-1.5 rounded-md border border-rose-300 dark:border-rose-700/60 bg-rose-50 dark:bg-rose-950/40 px-3 py-2 text-xs text-rose-800 dark:text-rose-200"
            >
              <span aria-hidden className="mt-0.5">⚠️</span>
              <span>
                <strong>LinkedIn has bot detection.</strong> Polling faster than{' '}
                {FREQUENCY_MIN_MINUTES} minutes risks flagging your account or
                triggering CAPTCHAs. Value will be clamped to{' '}
                {FREQUENCY_MIN_MINUTES}m on save.
              </span>
            </div>
          ) : atMin ? (
            <div className="flex items-start gap-1.5 rounded-md border border-amber-300 dark:border-amber-700/60 bg-amber-50 dark:bg-amber-950/40 px-3 py-2 text-xs text-amber-900 dark:text-amber-200">
              <span aria-hidden className="mt-0.5">ℹ️</span>
              <span>
                You're at the rate-limit floor. LinkedIn's bot detection
                triggers below {FREQUENCY_MIN_MINUTES}-minute polling, so this
                is the safest fastest cadence.
              </span>
            </div>
          ) : null}
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

      <AutoApplyCard />

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

/**
 * Auto-apply controls. Lives inside Automation Settings as a sibling
 * card to "Auto-Search" — both gate the same kind of cron-like
 * background work, just for different stages of the pipeline.
 *
 * The kill switch (auto_apply_enabled) gets prominent visual weight
 * because slice 4+ will ship code that actually clicks Submit. The
 * operator must trust that this toggle does what it says.
 */
function AutoApplyCard() {
  const settings = useSettings()
  const updateSettings = useUpdateSettings()
  const { data: circuit } = useCircuitStatus()
  const resetCircuit = useResetCircuit()

  // Defensive defaults: a fresh-cloned DB or a settings response that
  // races migrations could omit these. Render *something* sensible.
  const enabled = settings.data?.auto_apply_enabled ?? false
  const cap = settings.data?.daily_apply_cap ?? 15
  const qhStart = settings.data?.quiet_hours_start ?? 23
  const qhEnd = settings.data?.quiet_hours_end ?? 7
  const browserMode = settings.data?.apply_browser_mode ?? 'chromium_ephemeral'
  const tripped = !!circuit?.tripped

  return (
    <SettingsCard
      title="Auto-Apply"
      subtitle="The bot picks up approved jobs and (slice 4+) submits them. Off by default; flip the kill switch only when you trust the queue."
    >
      {tripped ? (
        <div className="px-6 py-4 border-b border-zinc-900/10 dark:border-zinc-100/10 bg-orange-50 dark:bg-orange-950/30 flex items-center gap-3">
          <FiAlertOctagon className="h-5 w-5 text-orange-500 shrink-0" />
          <div className="flex-1 min-w-0 text-sm">
            <div className="font-medium">Circuit breaker tripped — apply loop halted</div>
            <div className="text-xs text-zinc-600 dark:text-zinc-400">
              Reason: <span className="font-mono">{circuit?.reason ?? 'unknown'}</span>
              {circuit?.tripped_at ? <> · {formatRelative(circuit.tripped_at)}</> : null}
              {circuit?.consecutive_failures
                ? <> · {circuit.consecutive_failures} consecutive failures</>
                : null}
            </div>
          </div>
          <button
            type="button"
            onClick={() => resetCircuit.mutate()}
            disabled={resetCircuit.isPending}
            className="inline-flex items-center gap-1.5 rounded-lg border border-zinc-900 dark:border-zinc-100 px-3 py-1.5 text-xs hover:bg-zinc-100 dark:hover:bg-zinc-900"
          >
            <FiRefreshCw className={cn('h-3.5 w-3.5', resetCircuit.isPending && 'animate-spin')} />
            Reset
          </button>
        </div>
      ) : null}

      <FieldRow
        label="Kill switch"
        hint="Master toggle. When off the apply loop ticks but never fires, no matter the queue contents."
      >
        <Toggle
          checked={enabled}
          onChange={(v) => updateSettings.mutate({ auto_apply_enabled: v })}
          label="Auto-apply enabled"
        />
      </FieldRow>

      <FieldRow
        label="Daily cap"
        hint="Per local day. Successful submits (real + dry-run) count; failures don't. Hard floor 1, ceiling 50."
      >
        <TextInput
          type="number"
          min={1}
          max={50}
          value={cap}
          onChange={(e) => {
            const n = Math.round(Number(e.target.value))
            if (Number.isFinite(n) && n >= 1 && n <= 50 && n !== cap) {
              updateSettings.mutate({ daily_apply_cap: n })
            }
          }}
        />
      </FieldRow>

      <FieldRow
        label="Quiet hours"
        hint="Local 24h. Wrap supported (e.g. 23 → 7 means no apply between 11pm and 7am). Set both to the same value to disable."
        align="start"
      >
        <div className="flex items-center gap-2">
          <TextInput
            type="number"
            min={0}
            max={23}
            value={qhStart}
            onChange={(e) => {
              const n = Math.round(Number(e.target.value))
              if (Number.isFinite(n) && n >= 0 && n <= 23 && n !== qhStart) {
                updateSettings.mutate({ quiet_hours_start: n })
              }
            }}
            className="!w-20"
          />
          <span className="text-sm text-zinc-500 dark:text-zinc-400">→</span>
          <TextInput
            type="number"
            min={0}
            max={23}
            value={qhEnd}
            onChange={(e) => {
              const n = Math.round(Number(e.target.value))
              if (Number.isFinite(n) && n >= 0 && n <= 23 && n !== qhEnd) {
                updateSettings.mutate({ quiet_hours_end: n })
              }
            }}
            className="!w-20"
          />
          <span className="text-xs text-zinc-500 dark:text-zinc-400 ml-2">
            local hours (0-23)
          </span>
        </div>
      </FieldRow>

      <FieldRow
        label="Browser mode"
        hint="Playwright acquisition strategy. Ephemeral is safest for dry-runs; attached_chrome ships in slice 5 and requires a dedicated Chrome --remote-debugging-port profile."
        align="start"
      >
        <Select
          value={browserMode}
          onChange={(v) => updateSettings.mutate({ apply_browser_mode: v })}
          options={[
            { value: 'chromium_ephemeral', label: 'chromium_ephemeral (fresh launch, no profile)' },
            { value: 'chromium_persistent', label: 'chromium_persistent (Playwright + user_data_dir)' },
            { value: 'attached_chrome', label: 'attached_chrome (CDP into real Chrome — needs setup)' },
          ]}
        />
      </FieldRow>

      {browserMode === 'attached_chrome' ? <AttachedChromePanel /> : null}
    </SettingsCard>
  )
}

/**
 * Attached-Chrome connectivity verifier.
 *
 * Surfaces the exact ``Google Chrome`` launch command (Chrome 136+
 * requires ``--user-data-dir`` for the debug port) and a Test
 * Connection button. The backend tries CDP attach, reports Chrome
 * version + open tab count + whether a LinkedIn session is detected.
 * Operator-facing: this is the bridge between "I clicked the toggle"
 * and "the bot can actually drive my Chrome."
 */
function AttachedChromePanel() {
  const test = useMutation({
    mutationFn: () => api.testAttachedChrome(),
  })
  const result = test.data

  return (
    <div className="px-6 py-4 border-t border-zinc-900/10 dark:border-zinc-100/10">
      <div className="text-sm font-medium mb-2 flex items-center gap-2">
        <FiZap className="h-4 w-4 text-amber-500" />
        Attached Chrome — connection check
      </div>
      <p className="text-xs text-zinc-500 dark:text-zinc-400 mb-3 leading-snug">
        Launch Chrome with a dedicated debug profile, sign into LinkedIn in
        that window, then click Test. The bot will reuse that browser
        session for every apply attempt — that's how it bypasses the auth
        wall ephemeral mode hits today.
      </p>

      <pre className="text-[11px] font-mono bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-md p-2 overflow-x-auto mb-3">
        /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \{'\n'}
        {'  '}--remote-debugging-port=9222 \{'\n'}
        {'  '}--user-data-dir="$HOME/chrome-debug-profile"
      </pre>

      <button
        type="button"
        onClick={() => test.mutate()}
        disabled={test.isPending}
        className="inline-flex items-center gap-1.5 rounded-lg border border-zinc-900 dark:border-zinc-100 px-3 py-1.5 text-xs hover:bg-zinc-100 dark:hover:bg-zinc-900"
      >
        <FiRefreshCw className={cn('h-3.5 w-3.5', test.isPending && 'animate-spin')} />
        {test.isPending ? 'Testing…' : 'Test Connection'}
      </button>

      {result ? (
        <div
          className={cn(
            'mt-3 rounded-lg border p-3 text-xs',
            result.ok
              ? 'border-emerald-500/40 bg-emerald-50 dark:bg-emerald-950/30'
              : 'border-rose-500/40 bg-rose-50 dark:bg-rose-950/30',
          )}
        >
          <div className="flex items-center gap-2 font-medium mb-1">
            {result.ok ? (
              <FiCheck className="h-4 w-4 text-emerald-600" />
            ) : (
              <FiX className="h-4 w-4 text-rose-600" />
            )}
            {result.ok ? 'Connected to Chrome' : 'Could not connect'}
            <span className="text-zinc-500 dark:text-zinc-400 font-normal">
              · port {result.port}
            </span>
          </div>
          <div className="text-zinc-700 dark:text-zinc-300 leading-snug">
            {result.hint}
          </div>
          {result.ok ? (
            <div className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-[11px] text-zinc-600 dark:text-zinc-400">
              <div>chrome: <span className="font-mono">{result.chrome_version}</span></div>
              <div>contexts: <span className="font-mono">{result.contexts}</span></div>
              <div>tabs open: <span className="font-mono">{result.pages_open}</span></div>
              <div>
                linkedin session:{' '}
                <span className={cn(
                  'font-mono',
                  result.linkedin_session_detected ? 'text-emerald-700' : 'text-amber-700',
                )}>
                  {result.linkedin_session_detected ? 'yes ✓' : 'no — sign in first'}
                </span>
              </div>
              {result.sample_urls && result.sample_urls.length > 0 ? (
                <div className="col-span-2 truncate">
                  sample tab: <span className="font-mono text-zinc-500">{result.sample_urls[0]}</span>
                </div>
              ) : null}
            </div>
          ) : (
            <>
              {result.error ? (
                <div className="mt-2 text-[11px] font-mono text-rose-700 dark:text-rose-300 break-all">
                  {result.error}
                </div>
              ) : null}
              {result.command ? (
                <pre className="mt-2 text-[11px] font-mono bg-white/60 dark:bg-zinc-950/60 border border-zinc-200 dark:border-zinc-800 rounded p-2 overflow-x-auto">
                  {result.command}
                </pre>
              ) : null}
            </>
          )}
        </div>
      ) : null}
    </div>
  )
}
