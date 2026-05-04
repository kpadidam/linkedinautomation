import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { FiExternalLink, FiCheck } from 'react-icons/fi'
import {
  SettingsCard,
  FieldRow,
  TextInput,
  GhostButton,
  StatusOk,
  StatusBad,
} from './_components'
import { useSettings } from '@/hooks/useSettings'

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

const SECRET_NOTE =
  'Set in `.env` and restart the server to change. The UI cannot edit secrets.'

export default function IntegrationsScreen() {
  const qc = useQueryClient()
  const stats = useQuery({ queryKey: ['statistics'], queryFn: () => http<Statistics>('/api/statistics') })
  const health = useQuery({
    queryKey: ['health'],
    queryFn: () => http<{ status: string }>('/api/health'),
    refetchInterval: 30_000,
  })
  const settings = useSettings()
  const createSheet = useMutation({
    mutationFn: () => http<{ sheet_url: string }>('/api/sheets/create', { method: 'POST' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['statistics'] }),
  })

  const sheetUrl = stats.data?.sheet_url || null
  const sheetIdShort = sheetUrl ? extractShortId(sheetUrl) : null
  const secrets = settings.data?.secrets
  const openaiOk = !!secrets?.openai_configured
  const groqOk = !!secrets?.groq_configured
  const linkedinOk = !!secrets?.linkedin_configured
  const sheetsOk = !!secrets?.sheets_configured
  const llmConnected = openaiOk && health.data?.status === 'healthy'

  return (
    <div className="space-y-8">
      <SettingsCard title="LLM provider" subtitle="Used for resume matching and Browser-Use scraping">
        <SecretRow label="OpenAI" configured={openaiOk} />
        <FieldRow label="Status">
          {llmConnected ? (
            <StatusOk>Connected · gpt-4o</StatusOk>
          ) : openaiOk ? (
            <span className="text-sm text-zinc-500">Configured · health check failing</span>
          ) : (
            <span className="text-sm text-zinc-500">Not connected</span>
          )}
        </FieldRow>
        <SecretRow label="Groq fallback" configured={groqOk} />
      </SettingsCard>

      <SettingsCard title="Google Sheets" subtitle="Auto-mirrors all scraped jobs to a sheet">
        <SecretRow label="Service account" configured={sheetsOk} />
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
        <SecretRow label="Credentials" configured={linkedinOk} />
      </SettingsCard>
    </div>
  )
}

function SecretRow({ label, configured }: { label: string; configured: boolean }) {
  return (
    <FieldRow label={label} hint={SECRET_NOTE} align="start">
      {configured ? (
        <StatusOk>Configured</StatusOk>
      ) : (
        <StatusBad>Not configured</StatusBad>
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
