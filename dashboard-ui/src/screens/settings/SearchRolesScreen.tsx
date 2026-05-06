import { useState } from 'react'
import { FiPlus } from 'react-icons/fi'
import { SettingsCard, Chip } from './_components'

interface Category {
  id: string
  name: string
  remote: 'remote ok' | 'onsite' | 'hybrid'
  roles: string[]
}

const SEED: Category[] = [
  {
    id: 'senior-frontend',
    name: 'Senior Frontend',
    remote: 'remote ok',
    roles: ['Senior Frontend Engineer', 'Senior Software Engineer · Frontend'],
  },
  {
    id: 'product-engineer',
    name: 'Product Engineer',
    remote: 'remote ok',
    roles: ['Product Engineer', 'Full-stack Engineer'],
  },
  {
    id: 'staff-ic',
    name: 'Staff IC',
    remote: 'onsite',
    roles: ['Staff Engineer', 'Staff Software Engineer'],
  },
]

export default function SearchRolesScreen() {
  const [cats, setCats] = useState<Category[]>(SEED)

  const removeRole = (id: string, role: string) =>
    setCats((cs) =>
      cs.map((c) =>
        c.id === id ? { ...c, roles: c.roles.filter((r) => r !== role) } : c,
      ),
    )

  const addCategory = () => {
    const id = `cat-${cats.length + 1}-${Date.now()}`
    setCats((cs) => [
      ...cs,
      { id, name: 'New category', remote: 'remote ok', roles: [] },
    ])
  }

  return (
    <SettingsCard title="Job categories" subtitle="config/job_preferences.json — edit visually">
      <div className="p-6 space-y-4">
        {cats.map((c) => (
          <CategoryRow key={c.id} cat={c} onRemoveRole={(r) => removeRole(c.id, r)} />
        ))}

        <button
          type="button"
          onClick={addCategory}
          className="w-full rounded-2xl border-2 border-dashed border-zinc-900/30 dark:border-zinc-100/30 px-5 py-4 text-sm hover:border-zinc-900 dark:hover:border-zinc-100 transition-colors flex items-center justify-center gap-2"
        >
          <FiPlus className="h-4 w-4" />
          Add category
        </button>
      </div>
    </SettingsCard>
  )
}

function CategoryRow({
  cat,
  onRemoveRole,
}: {
  cat: Category
  onRemoveRole: (role: string) => void
}) {
  return (
    <div className="rounded-2xl border border-zinc-900/30 dark:border-zinc-100/30 px-5 py-4">
      <div className="flex items-start justify-between gap-4 mb-3">
        <h3 className="text-base font-medium">{cat.name}</h3>
        <span className="text-sm text-zinc-500 dark:text-zinc-400 shrink-0">{cat.remote}</span>
      </div>
      <div className="flex flex-wrap gap-2">
        {cat.roles.map((r) => (
          <Chip key={r} onRemove={() => onRemoveRole(r)}>
            {r}
          </Chip>
        ))}
        {cat.roles.length === 0 ? (
          <span className="text-sm text-zinc-500 dark:text-zinc-400">No roles yet</span>
        ) : null}
      </div>
    </div>
  )
}
