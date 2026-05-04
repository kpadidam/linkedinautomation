import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { FiExternalLink, FiCheck, FiEdit2, FiX, FiSave, FiEye, FiEyeOff } from 'react-icons/fi'
import {
  SettingsCard,
  FieldRow,
  TextInput,
  GhostButton,
  StatusOk,
  StatusBad,
} from './_components'
import { useSettings, useUpdateSettings, type SecretSource } from '@/hooks/useSettings'
import { cn } from '@/lib/utils'

interface Statistics {
  sheet_url?: string | null
  total_jobs?: number
}

async function http<T>(url: string, init?: RequestInit): Promise<T> {
  const r = await fetch(url, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
  })
  if (!r.ok) throw new Error(`${r.status}`)
  return r.json() as Promise<T>
}

export default function IntegrationsScreen() {
  const qc = useQueryClient()
  const stats = useQuery({ queryKey: ['statistics'], queryFn: () => http<Statistics>('/api/statistics') })
  const health = useQuery({
    queryKey: ['health'],
    queryFn: () => http<{ status: string }>('/api/health'),
    refetchInterval: 30_000,
  })
  const settings = useSettings()
  const updateSettings = useUpdateSettings()
  const createSheet = useMutation({
    mutationFn: () => http<{ sheet_url: string }>('/api/sheets/create', { method: 'POST' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['statistics'] }),
  })

  const sheetUrl = stats.data?.sheet_url || null
  const sheetIdShort = sheetUrl ? extractShortId(sheetUrl) : null
  const secrets = settings.data?.secrets
  const llmConnected = !!secrets?.openai_configured && health.data?.status === 'healthy'

  return (
    <div className="space-y-8">
      <SettingsCard title="LLM provider" subtitle="Used for resume matching and Browser-Use scraping">
        <SecretRow
          label="OpenAI API key"
          configured={!!secrets?.openai_configured}
          source={secrets?.openai_source ?? null}
          placeholder="sk-…"
          onSave={(v) => updateSettings.mutate({ openai_api_key: v })}
          onClear={() => updateSettings.mutate({ openai_api_key: '' })}
          saving={updateSettings.isPending}
        />
        <FieldRow label="Status">
          {llmConnected ? (
            <StatusOk>Connected · gpt-4o</StatusOk>
          ) : secrets?.openai_configured ? (
            <span className="text-sm text-zinc-500">Configured · health check failing</span>
          ) : (
            <StatusBad>Not connected — add an OpenAI key to enable matching</StatusBad>
          )}
        </FieldRow>
        <SecretRow
          label="Groq fallback (optional)"
          configured={!!secrets?.groq_configured}
          source={secrets?.groq_source ?? null}
          placeholder="gsk_…"
          onSave={(v) => updateSettings.mutate({ groq_api_key: v })}
          onClear={() => updateSettings.mutate({ groq_api_key: '' })}
          saving={updateSettings.isPending}
        />
      </SettingsCard>

      <SettingsCard title="Google Sheets" subtitle="Auto-mirrors all scraped jobs to a sheet">
        <FieldRow
          label="Service account"
          hint={
            secrets?.sheets_source === 'env'
              ? 'Configured via .env (GOOGLE_SHEETS_CREDENTIALS_PATH + GOOGLE_SHEETS_ID). Edit .env to change.'
              : 'Drop credentials.json next to your project root and set GOOGLE_SHEETS_ID in .env.'
          }
        >
          {secrets?.sheets_configured ? (
            <span className="inline-flex items-center gap-2">
              <StatusOk>Configured</StatusOk>
              <SourceBadge source={secrets.sheets_source} />
            </span>
          ) : (
            <StatusBad>Not configured</StatusBad>
          )}
        </FieldRow>
        <FieldRow label="Sheet" hint="18 columns, schema auto-managed">
          <div className="flex items-center gap-3">
            <TextInput
              readOnly
              value={sheetIdShort ? `LinkedIn Jobs · ${sheetIdShort}` : 'No sheet connected'}
            />
            {sheetUrl ? (
              <a
                href={sheetUrl}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-2 rounded-xl border border-zinc-900/30 dark:border-zinc-100/30 px-3 py-2 text-sm hover:border-zinc-900 dark:hover:border-zinc-100 shrink-0"
              >
                <FiExternalLink className="h-4 w-4" />
                Open
              </a>
            ) : null}
          </div>
        </FieldRow>
        <FieldRow label="Actions">
          <div className="flex items-center gap-3">
            <GhostButton
              type="button"
              onClick={() => createSheet.mutate()}
              disabled={createSheet.isPending}
            >
              {createSheet.isPending ? 'Creating…' : 'Create new sheet'}
            </GhostButton>
            {createSheet.isSuccess ? (
              <span className="inline-flex items-center gap-1.5 text-sm text-emerald-700 dark:text-emerald-400">
                <FiCheck className="h-4 w-4" />
                Created
              </span>
            ) : null}
          </div>
        </FieldRow>
      </SettingsCard>

      <SettingsCard title="LinkedIn" subtitle="Optional — logged-in scrapes are higher quality">
        <SecretRow
          label="Email"
          configured={!!secrets?.linkedin_configured}
          source={secrets?.linkedin_source ?? null}
          placeholder="you@example.com"
          mask={false}
          onSave={(v) => updateSettings.mutate({ linkedin_email: v })}
          onClear={() => updateSettings.mutate({ linkedin_email: '' })}
          saving={updateSettings.isPending}
        />
        <SecretRow
          label="Password"
          configured={!!secrets?.linkedin_configured}
          source={secrets?.linkedin_source ?? null}
          placeholder="••••••••"
          onSave={(v) => updateSettings.mutate({ linkedin_password: v })}
          onClear={() => updateSettings.mutate({ linkedin_password: '' })}
          saving={updateSettings.isPending}
          /* Hide source badge on password row — already shown on email row to avoid noise */
          hideSourceBadge
        />
      </SettingsCard>
    </div>
  )
}

function SourceBadge({ source }: { source: SecretSource }) {
  if (source !== 'env') return null
  return (
    <span className="inline-flex items-center rounded-md border border-zinc-300 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-900 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-zinc-600 dark:text-zinc-400">
      from .env
    </span>
  )
}

interface SecretRowProps {
  label: string
  configured: boolean
  source: SecretSource
  placeholder?: string
  mask?: boolean // false → show as plain text (e.g. for email)
  hideSourceBadge?: boolean
  saving: boolean
  onSave: (v: string) => void
  onClear: () => void
}

function SecretRow({
  label,
  configured,
  source,
  placeholder,
  mask = true,
  hideSourceBadge = false,
  saving,
  onSave,
  onClear,
}: SecretRowProps) {
  const [editing, setEditing] = useState(!configured)
  const [draft, setDraft] = useState('')
  const [show, setShow] = useState(false)

  // .env-sourced secrets aren't directly editable from the UI — the user
  // would need to clear .env first. We let the user override by setting
  // a DB value (which beats env), but flag the relationship clearly.
  const dbConfigured = configured && source === 'db'

  const handleSave = () => {
    if (!draft.trim()) return
    onSave(draft.trim())
    setDraft('')
    setEditing(false)
  }
  const handleCancel = () => {
    setDraft('')
    setEditing(configured ? false : true)
  }

  return (
    <FieldRow
      label={label}
      hint={
        source === 'env' && !editing
          ? 'Currently from .env. Set a value here to override.'
          : undefined
      }
      align="start"
    >
      {editing ? (
        <div className="flex items-center gap-2">
          <div className="relative flex-1">
            <input
              type={mask && !show ? 'password' : 'text'}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder={placeholder}
              className={cn(
                'w-full rounded-xl border border-zinc-900/30 dark:border-zinc-100/30 bg-white dark:bg-zinc-950 px-4 py-2.5 text-sm font-mono pr-10',
                'focus:outline-none focus:border-zinc-900 dark:focus:border-zinc-100',
              )}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleSave()
                if (e.key === 'Escape') handleCancel()
              }}
            />
            {mask ? (
              <button
                type="button"
                onClick={() => setShow((s) => !s)}
                aria-label={show ? 'Hide' : 'Reveal'}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100"
              >
                {show ? <FiEyeOff className="h-4 w-4" /> : <FiEye className="h-4 w-4" />}
              </button>
            ) : null}
          </div>
          <GhostButton
            type="button"
            onClick={handleSave}
            disabled={!draft.trim() || saving}
          >
            <FiSave className="h-4 w-4" />
            Save
          </GhostButton>
          {configured ? (
            <GhostButton type="button" onClick={handleCancel} disabled={saving}>
              <FiX className="h-4 w-4" />
              Cancel
            </GhostButton>
          ) : null}
        </div>
      ) : (
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-mono text-sm text-zinc-700 dark:text-zinc-300">
            {configured ? '••••••••••••' : '—'}
          </span>
          {configured ? <StatusOk>Configured</StatusOk> : <StatusBad>Not configured</StatusBad>}
          {!hideSourceBadge ? <SourceBadge source={source} /> : null}
          <GhostButton type="button" onClick={() => setEditing(true)} disabled={saving}>
            <FiEdit2 className="h-3.5 w-3.5" />
            {dbConfigured ? 'Replace' : 'Set'}
          </GhostButton>
          {dbConfigured ? (
            <GhostButton type="button" onClick={onClear} disabled={saving}>
              Clear
            </GhostButton>
          ) : null}
        </div>
      )}
    </FieldRow>
  )
}

function extractShortId(url: string) {
  const m = url.match(/\/d\/([^/]+)/)
  if (!m) return null
  const id = m[1]
  return id.length > 12 ? `${id.slice(0, 4)}…${id.slice(-3)}` : id
}
