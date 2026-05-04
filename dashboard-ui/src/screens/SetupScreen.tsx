import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  FiArrowRight,
  FiArrowLeft,
  FiCheckCircle,
  FiCircle,
  FiUser,
  FiSliders,
  FiFileText,
  FiKey,
  FiGrid,
  FiSkipForward,
} from 'react-icons/fi'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useSetupStatus } from '@/hooks/useSetup'
import { useUpdateSettings } from '@/hooks/useSettings'
import { cn } from '@/lib/utils'

interface Profile {
  name?: string
  email?: string
  resume_text?: string
  skills?: string[]
  preferred_locations?: string[]
  search_roles?: string[]
}

async function http<T>(url: string, init?: RequestInit): Promise<T> {
  const r = await fetch(url, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
  })
  if (!r.ok) throw new Error(`${r.status}`)
  return r.json() as Promise<T>
}

const STEPS = [
  { id: 'profile', label: 'You', icon: FiUser },
  { id: 'roles', label: 'Search Roles', icon: FiSliders },
  { id: 'resume', label: 'Resume', icon: FiFileText },
  { id: 'llm', label: 'LLM key', icon: FiKey },
  { id: 'sheets', label: 'Google Sheets', icon: FiGrid },
] as const

type StepId = (typeof STEPS)[number]['id']

export default function SetupScreen() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const { data: setup } = useSetupStatus()
  const updateSettings = useUpdateSettings()

  const profile = useQuery({
    queryKey: ['profile'],
    queryFn: () => http<Profile>('/api/profile'),
  })
  const saveProfile = useMutation({
    mutationFn: (body: Profile) =>
      http<Profile>('/api/profile', { method: 'PUT', body: JSON.stringify(body) }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['profile'] })
      qc.invalidateQueries({ queryKey: ['setup-status'] })
    },
  })

  const itemsById = useMemo(() => {
    const m: Record<string, boolean> = {}
    setup?.items.forEach((i) => (m[i.id] = i.complete))
    return m
  }, [setup])

  const [step, setStep] = useState(0)

  // On first render, jump to first incomplete required step.
  useEffect(() => {
    if (!setup) return
    const firstIncomplete = STEPS.findIndex((s) => {
      const item = setup.items.find((i) => i.id === s.id)
      return item && !item.complete && !item.optional
    })
    if (firstIncomplete >= 0) setStep(firstIncomplete)
    else setStep(STEPS.length) // all done → final summary
    // Run only when setup data first arrives.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [setup?.complete])

  const allRequiredComplete = !!setup && setup.complete

  // ------- step-local form state ----------
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [roleDraft, setRoleDraft] = useState('')
  const [resumeText, setResumeText] = useState('')
  const [llmKey, setLlmKey] = useState('')
  const [llmProvider, setLlmProvider] = useState<'openai' | 'groq'>('openai')

  // Hydrate state from server profile when it arrives.
  useEffect(() => {
    if (!profile.data) return
    setName(profile.data.name || '')
    setEmail(profile.data.email || '')
    setResumeText(profile.data.resume_text || '')
  }, [profile.data])

  const roles: string[] = profile.data?.search_roles || []

  const goNext = () => setStep((s) => Math.min(s + 1, STEPS.length))
  const goBack = () => setStep((s) => Math.max(s - 1, 0))

  // ------- step handlers ----------
  const submitProfile = () => {
    saveProfile.mutate({ name: name.trim(), email: email.trim() }, { onSuccess: () => goNext() })
  }
  const addRole = (v?: string) => {
    const value = (v ?? roleDraft).trim()
    if (!value) return
    if (roles.includes(value)) {
      setRoleDraft('')
      return
    }
    saveProfile.mutate({ search_roles: [...roles, value] }, {
      onSuccess: () => setRoleDraft(''),
    })
  }
  const removeRole = (v: string) => {
    saveProfile.mutate({ search_roles: roles.filter((r) => r !== v) })
  }
  const submitResume = () => {
    saveProfile.mutate({ resume_text: resumeText.trim() }, { onSuccess: () => goNext() })
  }
  const submitLlm = () => {
    const trimmed = llmKey.trim()
    if (!trimmed) return
    const payload = llmProvider === 'openai'
      ? { openai_api_key: trimmed }
      : { groq_api_key: trimmed }
    updateSettings.mutate(payload, {
      onSuccess: () => {
        setLlmKey('')
        qc.invalidateQueries({ queryKey: ['setup-status'] })
        goNext()
      },
    })
  }

  return (
    <div className="min-h-full bg-white dark:bg-zinc-950 text-zinc-900 dark:text-zinc-50">
      <div className="max-w-2xl mx-auto px-6 py-10 space-y-8">
        <header>
          <h1 className="text-2xl font-bold tracking-tight">Welcome — let's set up</h1>
          <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
            5 quick steps. The scraper needs all required items before it'll start.
          </p>
        </header>

        <Stepper step={step} setStep={setStep} itemsById={itemsById} />

        {/* ---------- panels ---------- */}
        {step === 0 ? (
          <Panel
            title="You"
            subtitle="Used for resume matching and outreach drafts."
            done={itemsById.profile}
            onSkip={null}
          >
            <Field label="Name">
              <input
                className="input"
                value={name}
                placeholder="Casey Morgan"
                onChange={(e) => setName(e.target.value)}
              />
            </Field>
            <Field label="Email">
              <input
                type="email"
                className="input"
                value={email}
                placeholder="casey@morgan.dev"
                onChange={(e) => setEmail(e.target.value)}
              />
            </Field>
            <Footer
              onBack={null}
              onNext={submitProfile}
              nextDisabled={!name.trim() && !email.trim()}
              nextLabel={itemsById.profile ? 'Save & continue' : 'Continue'}
              busy={saveProfile.isPending}
            />
          </Panel>
        ) : null}

        {step === 1 ? (
          <Panel
            title="Search Roles"
            subtitle="The scraper queries LinkedIn for these roles. Add at least one."
            done={itemsById.roles}
            onSkip={null}
          >
            <Field label="Add a role">
              <div className="flex gap-2">
                <input
                  className="input"
                  placeholder="e.g. Senior Frontend Engineer"
                  value={roleDraft}
                  onChange={(e) => setRoleDraft(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault()
                      addRole()
                    }
                  }}
                />
                <button
                  type="button"
                  className="btn-ghost"
                  onClick={() => addRole()}
                  disabled={!roleDraft.trim() || saveProfile.isPending}
                >
                  Add
                </button>
              </div>
            </Field>
            {roles.length > 0 ? (
              <div className="flex flex-wrap gap-1.5">
                {roles.map((r) => (
                  <span
                    key={r}
                    className="chip bg-brand-50 text-brand-700 dark:bg-brand-700/20 dark:text-brand-100"
                  >
                    {r}
                    <button
                      className="ml-1 opacity-60 hover:opacity-100"
                      onClick={() => removeRole(r)}
                      aria-label={`Remove ${r}`}
                    >
                      ×
                    </button>
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-xs text-zinc-500">No roles yet — add one to continue.</p>
            )}
            <Footer
              onBack={goBack}
              onNext={goNext}
              nextDisabled={roles.length === 0}
              nextLabel="Continue"
              busy={saveProfile.isPending}
            />
          </Panel>
        ) : null}

        {step === 2 ? (
          <Panel
            title="Resume"
            subtitle="Pasted text is what the LLM scores jobs against."
            done={itemsById.resume}
            onSkip={null}
          >
            <Field label="Resume text">
              <textarea
                rows={10}
                className="input min-h-[180px]"
                placeholder="Paste your resume…"
                value={resumeText}
                onChange={(e) => setResumeText(e.target.value)}
              />
            </Field>
            <Footer
              onBack={goBack}
              onNext={submitResume}
              nextDisabled={!resumeText.trim()}
              nextLabel={itemsById.resume ? 'Save & continue' : 'Continue'}
              busy={saveProfile.isPending}
            />
          </Panel>
        ) : null}

        {step === 3 ? (
          <Panel
            title="LLM API key"
            subtitle="Used by Browser-Use scraping and resume matching. OpenAI is preferred; Groq works as a fallback."
            done={itemsById.llm}
            onSkip={null}
          >
            <Field label="Provider">
              <div className="inline-flex rounded-lg border border-zinc-300 dark:border-zinc-700 p-0.5 text-sm">
                {(['openai', 'groq'] as const).map((p) => (
                  <button
                    key={p}
                    type="button"
                    className={cn(
                      'px-3 py-1 rounded capitalize',
                      llmProvider === p
                        ? 'bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900'
                        : 'text-zinc-600 dark:text-zinc-400',
                    )}
                    onClick={() => setLlmProvider(p)}
                  >
                    {p === 'openai' ? 'OpenAI' : 'Groq'}
                  </button>
                ))}
              </div>
            </Field>
            <Field
              label={llmProvider === 'openai' ? 'OpenAI API key' : 'Groq API key'}
              hint="Stored in the local SQLite DB. Beats any value in .env."
            >
              <input
                type="password"
                className="input font-mono"
                placeholder={llmProvider === 'openai' ? 'sk-…' : 'gsk_…'}
                value={llmKey}
                onChange={(e) => setLlmKey(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') submitLlm()
                }}
              />
            </Field>
            {itemsById.llm ? (
              <p className="text-xs text-emerald-700 dark:text-emerald-400">
                ✓ A key is already configured. You can replace it or skip.
              </p>
            ) : null}
            <Footer
              onBack={goBack}
              onNext={submitLlm}
              nextDisabled={!llmKey.trim()}
              nextLabel="Save & continue"
              extraRight={
                itemsById.llm ? (
                  <button type="button" className="btn-ghost" onClick={goNext}>
                    Skip
                  </button>
                ) : null
              }
              busy={updateSettings.isPending}
            />
          </Panel>
        ) : null}

        {step === 4 ? (
          <Panel
            title="Google Sheets"
            subtitle="Optional. Mirrors every scraped job to a Google Sheet for archiving / sharing."
            done={itemsById.sheets}
            onSkip={() => goNext()}
          >
            {itemsById.sheets ? (
              <p className="text-sm text-emerald-700 dark:text-emerald-400">
                ✓ Sheet is configured. You're ready.
              </p>
            ) : (
              <div className="space-y-3 text-sm text-zinc-600 dark:text-zinc-400">
                <p>
                  This requires a Google service-account JSON. The UI can't upload it (yet) — drop it
                  at <code className="font-mono text-xs">credentials.json</code> in the project root and
                  set <code className="font-mono text-xs">GOOGLE_SHEETS_ID</code> in your{' '}
                  <code className="font-mono text-xs">.env</code>.
                </p>
                <p>You can skip and add it later from Settings → Integrations.</p>
              </div>
            )}
            <Footer
              onBack={goBack}
              onNext={goNext}
              nextDisabled={false}
              nextLabel="Continue"
              busy={false}
            />
          </Panel>
        ) : null}

        {step >= STEPS.length ? (
          <Panel
            title={allRequiredComplete ? "You're all set" : 'Almost there'}
            subtitle={
              allRequiredComplete
                ? 'The scraper has everything it needs. Click below to head to the dashboard and start your first session.'
                : 'Some required items are still missing — go back and finish them, or jump to Settings.'
            }
            done={allRequiredComplete}
            onSkip={null}
          >
            <ul className="space-y-2 text-sm">
              {STEPS.map((s) => {
                const done = itemsById[s.id as StepId]
                return (
                  <li key={s.id} className="flex items-center gap-2">
                    {done ? (
                      <FiCheckCircle className="h-4 w-4 text-emerald-600" />
                    ) : (
                      <FiCircle className="h-4 w-4 text-zinc-400" />
                    )}
                    <span className={done ? 'text-zinc-700 dark:text-zinc-300' : 'text-zinc-500'}>
                      {s.label}
                    </span>
                  </li>
                )
              })}
            </ul>
            <div className="flex items-center justify-between gap-2 pt-2">
              <button type="button" className="btn-ghost" onClick={() => setStep(0)}>
                <FiArrowLeft className="h-4 w-4" />
                Back to start
              </button>
              <button
                type="button"
                className="btn-primary"
                onClick={() => navigate('/')}
                disabled={!allRequiredComplete}
              >
                <FiArrowRight className="h-4 w-4" />
                {allRequiredComplete ? 'Go to dashboard' : 'Finish required steps first'}
              </button>
            </div>
          </Panel>
        ) : null}
      </div>
    </div>
  )
}

// ---------- helpers ----------

function Stepper({
  step,
  setStep,
  itemsById,
}: {
  step: number
  setStep: (n: number) => void
  itemsById: Record<string, boolean>
}) {
  return (
    <ol className="flex items-center gap-1 overflow-x-auto -mx-1 px-1">
      {STEPS.map((s, i) => {
        const done = itemsById[s.id]
        const active = step === i
        return (
          <li key={s.id} className="flex items-center gap-1">
            <button
              type="button"
              onClick={() => setStep(i)}
              className={cn(
                'inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs whitespace-nowrap transition-colors',
                active
                  ? 'border-zinc-900 dark:border-zinc-100 bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900'
                  : done
                    ? 'border-emerald-300 bg-emerald-50 text-emerald-700 dark:border-emerald-700/50 dark:bg-emerald-950/40 dark:text-emerald-200'
                    : 'border-zinc-300 dark:border-zinc-700 text-zinc-600 dark:text-zinc-400 hover:border-zinc-500',
              )}
            >
              {done ? (
                <FiCheckCircle className="h-3 w-3" />
              ) : (
                <span className="font-mono">{i + 1}</span>
              )}
              <s.icon className="h-3 w-3 opacity-70" />
              {s.label}
            </button>
            {i < STEPS.length - 1 ? <span className="text-zinc-300 dark:text-zinc-700">·</span> : null}
          </li>
        )
      })}
    </ol>
  )
}

function Panel({
  title,
  subtitle,
  children,
  done,
  onSkip,
}: {
  title: string
  subtitle?: string
  children: React.ReactNode
  done: boolean
  onSkip: (() => void) | null
}) {
  return (
    <section className="rounded-2xl border border-zinc-900/15 dark:border-zinc-100/15 p-6 space-y-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold flex items-center gap-2">
            {title}
            {done ? <FiCheckCircle className="h-4 w-4 text-emerald-600" /> : null}
          </h2>
          {subtitle ? (
            <p className="mt-0.5 text-sm text-zinc-500 dark:text-zinc-400">{subtitle}</p>
          ) : null}
        </div>
        {onSkip ? (
          <button type="button" className="btn-ghost text-xs" onClick={onSkip}>
            <FiSkipForward className="h-3.5 w-3.5" />
            Skip
          </button>
        ) : null}
      </div>
      {children}
    </section>
  )
}

function Field({
  label,
  hint,
  children,
}: {
  label: string
  hint?: string
  children: React.ReactNode
}) {
  return (
    <label className="block">
      <div className="text-xs uppercase tracking-wide text-zinc-500 dark:text-zinc-400 mb-1">{label}</div>
      {children}
      {hint ? <div className="mt-1 text-[11px] text-zinc-500 dark:text-zinc-400">{hint}</div> : null}
    </label>
  )
}

function Footer({
  onBack,
  onNext,
  nextDisabled,
  nextLabel,
  busy,
  extraRight,
}: {
  onBack: (() => void) | null
  onNext: () => void
  nextDisabled: boolean
  nextLabel: string
  busy: boolean
  extraRight?: React.ReactNode
}) {
  return (
    <div className="flex items-center justify-between gap-2 pt-2 border-t border-zinc-200 dark:border-zinc-800">
      <div>
        {onBack ? (
          <button type="button" className="btn-ghost" onClick={onBack} disabled={busy}>
            <FiArrowLeft className="h-4 w-4" />
            Back
          </button>
        ) : (
          <Link to="/" className="btn-ghost">
            <FiArrowLeft className="h-4 w-4" />
            Cancel
          </Link>
        )}
      </div>
      <div className="flex items-center gap-2">
        {extraRight}
        <button
          type="button"
          className="btn-primary"
          onClick={onNext}
          disabled={nextDisabled || busy}
        >
          {busy ? 'Saving…' : nextLabel}
          {!busy ? <FiArrowRight className="h-4 w-4" /> : null}
        </button>
      </div>
    </div>
  )
}
