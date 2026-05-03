import { useEffect, useState } from 'react'
import { FiSave, FiSettings, FiPlus, FiX, FiSearch } from 'react-icons/fi'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

interface Profile {
  name?: string
  email?: string
  skills?: string[]
  preferred_locations?: string[]
  search_roles?: string[]
  resume_text?: string
  auto_search_enabled?: boolean
}

async function http<T>(url: string, init?: RequestInit): Promise<T> {
  const r = await fetch(url, { ...init, headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) } })
  if (!r.ok) throw new Error(`${r.status}`)
  return r.json() as Promise<T>
}

export default function SettingsScreen() {
  const qc = useQueryClient()
  const { data, isLoading } = useQuery({
    queryKey: ['profile'],
    queryFn: () => http<Profile>('/api/profile'),
  })
  const save = useMutation({
    mutationFn: (body: Profile) => http('/api/profile', { method: 'PUT', body: JSON.stringify(body) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['profile'] }),
  })

  const [profile, setProfile] = useState<Profile>({})
  const [newRole, setNewRole] = useState('')
  useEffect(() => { if (data) setProfile(data) }, [data])

  const roles = profile.search_roles || []
  const addRole = () => {
    const v = newRole.trim()
    if (!v) return
    if (roles.includes(v)) { setNewRole(''); return }
    setProfile({ ...profile, search_roles: [...roles, v] })
    setNewRole('')
  }
  const removeRole = (r: string) =>
    setProfile({ ...profile, search_roles: roles.filter((x) => x !== r) })

  return (
    <div className="p-4 md:p-6 space-y-6 max-w-3xl">
      <div>
        <h1 className="text-xl font-semibold flex items-center gap-2"><FiSettings /> Settings</h1>
        <p className="text-sm text-zinc-500 dark:text-zinc-400">Profile, capture roles, and feature flags.</p>
      </div>

      <div className="surface rounded-lg p-5 space-y-4">
        <div>
          <h2 className="text-sm font-medium flex items-center gap-2"><FiSearch className="h-4 w-4" /> Capture roles</h2>
          <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1">
            Roles to import on every session. Leave empty to use <code className="px-1 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800 text-[10px]">job_search_config.json</code>.
          </p>
        </div>
        {roles.length > 0 ? (
          <div className="flex flex-wrap gap-1.5">
            {roles.map((r) => (
              <span key={r} className="chip bg-brand-50 text-brand-700 dark:bg-brand-700/20 dark:text-brand-100">
                {r}
                <button className="ml-0.5 opacity-60 hover:opacity-100" onClick={() => removeRole(r)} aria-label={`Remove ${r}`}>
                  <FiX className="h-3 w-3" />
                </button>
              </span>
            ))}
          </div>
        ) : (
          <div className="text-xs text-zinc-500">No roles set — falls back to file config.</div>
        )}
        <div className="flex gap-2">
          <input
            className="input"
            placeholder="e.g. Frontend Engineer"
            value={newRole}
            onChange={(e) => setNewRole(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addRole() } }}
          />
          <button className="btn-ghost" onClick={addRole} disabled={!newRole.trim()}>
            <FiPlus className="h-4 w-4" /> Add
          </button>
        </div>
      </div>

      <div className="surface rounded-lg p-5 space-y-4">
        <h2 className="text-sm font-medium">Profile</h2>
        {isLoading ? <div className="text-sm text-zinc-500">Loading…</div> : null}
        <Field label="Name">
          <input className="input" value={profile.name || ''} onChange={(e) => setProfile({ ...profile, name: e.target.value })} />
        </Field>
        <Field label="Email">
          <input className="input" value={profile.email || ''} onChange={(e) => setProfile({ ...profile, email: e.target.value })} />
        </Field>
        <Field label="Skills (comma-separated)">
          <input
            className="input"
            value={(profile.skills || []).join(', ')}
            onChange={(e) => setProfile({ ...profile, skills: e.target.value.split(',').map((s) => s.trim()).filter(Boolean) })}
          />
        </Field>
        <Field label="Preferred locations (comma-separated)">
          <input
            className="input"
            value={(profile.preferred_locations || []).join(', ')}
            onChange={(e) => setProfile({ ...profile, preferred_locations: e.target.value.split(',').map((s) => s.trim()).filter(Boolean) })}
          />
        </Field>
      </div>

      <div className="flex items-center justify-end">
        <button className="btn-primary" onClick={() => save.mutate(profile)} disabled={save.isPending}>
          <FiSave className="h-4 w-4" /> Save settings
        </button>
      </div>

      <div className="surface rounded-lg p-5 space-y-3">
        <h2 className="text-sm font-medium">Feature flags</h2>
        <div className="text-sm text-zinc-600 dark:text-zinc-400">
          <p>
            <code className="px-1 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800 text-xs">ENABLE_RESUME_MATCHING</code>{' '}
            controls whether the import runs ATS scoring (LLM cost). Toggle it in <code>.env</code> and restart.
          </p>
        </div>
      </div>
    </div>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <div className="text-xs uppercase tracking-wide text-zinc-500 dark:text-zinc-400 mb-1">{label}</div>
      {children}
    </label>
  )
}
