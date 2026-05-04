import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { FiUpload, FiSave } from 'react-icons/fi'
import {
  SettingsCard,
  FieldRow,
  TextInput,
  TextArea,
  GhostButton,
} from './_components'

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
  const r = await fetch(url, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
  })
  if (!r.ok) throw new Error(`${r.status}`)
  return r.json() as Promise<T>
}

export default function ProfileResumeScreen() {
  const qc = useQueryClient()
  const { data } = useQuery({
    queryKey: ['profile'],
    queryFn: () => http<Profile>('/api/profile'),
  })
  const save = useMutation({
    mutationFn: (body: Profile) =>
      http('/api/profile', { method: 'PUT', body: JSON.stringify(body) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['profile'] }),
  })

  const [profile, setProfile] = useState<Profile>({})
  const [minSalary, setMinSalary] = useState('$180,000')

  useEffect(() => {
    if (data) setProfile(data)
  }, [data])

  const set = <K extends keyof Profile>(k: K, v: Profile[K]) =>
    setProfile((p) => ({ ...p, [k]: v }))

  const skillsValue = (profile.skills || []).join(', ')
  const locationsValue = (profile.preferred_locations || []).join(', ')

  return (
    <div className="space-y-8">
      <SettingsCard title="You" subtitle="Used for resume matching and outreach drafts">
        <FieldRow label="Name">
          <TextInput
            value={profile.name || ''}
            placeholder="Casey Morgan"
            onChange={(e) => set('name', e.target.value)}
          />
        </FieldRow>
        <FieldRow label="Email">
          <TextInput
            type="email"
            value={profile.email || ''}
            placeholder="casey@morgan.dev"
            onChange={(e) => set('email', e.target.value)}
          />
        </FieldRow>
      </SettingsCard>

      <SettingsCard
        title="Resume"
        subtitle="Pasted text is what the LLM scores jobs against"
      >
        <div className="px-6 py-5 space-y-4">
          <TextArea
            rows={10}
            value={profile.resume_text || ''}
            placeholder="Paste your resume here…"
            onChange={(e) => set('resume_text', e.target.value)}
          />
          <div>
            <GhostButton type="button" disabled title="PDF upload (coming soon)">
              <FiUpload className="h-4 w-4" />
              Upload .pdf
            </GhostButton>
          </div>
        </div>
      </SettingsCard>

      <SettingsCard title="Skills & locations">
        <FieldRow label="Skills">
          <TextInput
            value={skillsValue}
            placeholder="React, TypeScript, GraphQL, Postgres…"
            onChange={(e) =>
              set(
                'skills',
                e.target.value
                  .split(',')
                  .map((s) => s.trim())
                  .filter(Boolean),
              )
            }
          />
        </FieldRow>
        <FieldRow label="Preferred locations">
          <TextInput
            value={locationsValue}
            placeholder="San Francisco, New York, Remote"
            onChange={(e) =>
              set(
                'preferred_locations',
                e.target.value
                  .split(',')
                  .map((s) => s.trim())
                  .filter(Boolean),
              )
            }
          />
        </FieldRow>
        <FieldRow label="Min salary">
          <TextInput
            value={minSalary}
            placeholder="$180,000"
            onChange={(e) => setMinSalary(e.target.value)}
          />
        </FieldRow>
      </SettingsCard>

      <div className="flex justify-end">
        <button
          type="button"
          onClick={() => save.mutate(profile)}
          disabled={save.isPending}
          className="inline-flex items-center gap-2 rounded-xl bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 px-5 py-2.5 text-sm font-medium hover:opacity-90 disabled:opacity-50"
        >
          <FiSave className="h-4 w-4" />
          {save.isPending ? 'Saving…' : 'Save changes'}
        </button>
      </div>
    </div>
  )
}
