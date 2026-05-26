import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatDate(d?: string | null): string {
  if (!d) return '—'
  const date = new Date(d)
  if (Number.isNaN(date.getTime())) return d
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
}

export function formatRelative(d?: string | null): string {
  if (!d) return '—'
  const date = new Date(d)
  const diff = Date.now() - date.getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  if (days < 30) return `${days}d ago`
  return formatDate(d)
}

/**
 * Returns a 0–100 match score for display, preferring the slice-1 local
 * semantic score (`match_score`, [0, 1]) over the legacy LLM-based
 * `resume_match_score` ([0, 100]). Null when neither is set.
 */
export function effectiveMatchScore(job: {
  match_score?: number | null
  resume_match_score?: number | null
}): number | null {
  if (job.match_score != null) return Math.round(job.match_score * 100)
  if (job.resume_match_score != null) return Math.round(job.resume_match_score)
  return null
}

export function scoreColor(score?: number | null): string {
  if (score == null) return 'bg-zinc-200 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300'
  if (score >= 90) return 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300'
  if (score >= 70) return 'bg-lime-100 text-lime-700 dark:bg-lime-950 dark:text-lime-300'
  if (score >= 50) return 'bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300'
  return 'bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400'
}

export function statusLabel(status?: string | null): string {
  if (!status) return 'New'
  return status
    .split('_')
    .map((s) => s.charAt(0).toUpperCase() + s.slice(1))
    .join(' ')
}

export function nextActionFor(status?: string | null): string {
  switch (status) {
    case 'new': return 'Review'
    case 'saved': return 'Tailor resume'
    case 'tailoring_resume': return 'Apply'
    case 'applied': return 'Follow up'
    case 'recruiter_screen': return 'Prep call'
    case 'technical_interview': return 'Prep tech'
    case 'final': return 'Send thank-you'
    case 'interviewing': return 'Prep'
    case 'offer': return 'Negotiate'
    case 'rejected': return '—'
    default: return 'Review'
  }
}

export function daysSince(d?: string | null): number | null {
  if (!d) return null
  const t = new Date(d).getTime()
  if (Number.isNaN(t)) return null
  return Math.floor((Date.now() - t) / 86400000)
}

export function statusColor(status?: string | null): string {
  switch (status) {
    case 'saved': return 'bg-sky-100 text-sky-700 dark:bg-sky-950 dark:text-sky-300'
    case 'tailoring_resume': return 'bg-cyan-100 text-cyan-700 dark:bg-cyan-950 dark:text-cyan-300'
    case 'applied': return 'bg-indigo-100 text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300'
    case 'recruiter_screen': return 'bg-fuchsia-100 text-fuchsia-700 dark:bg-fuchsia-950 dark:text-fuchsia-300'
    case 'technical_interview': return 'bg-violet-100 text-violet-700 dark:bg-violet-950 dark:text-violet-300'
    case 'interviewing': return 'bg-violet-100 text-violet-700 dark:bg-violet-950 dark:text-violet-300'
    case 'final': return 'bg-purple-100 text-purple-700 dark:bg-purple-950 dark:text-purple-300'
    case 'offer': return 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300'
    case 'rejected': return 'bg-rose-100 text-rose-700 dark:bg-rose-950 dark:text-rose-300'
    default: return 'bg-zinc-100 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300'
  }
}

export interface CompanyColor {
  bg: string
  bgSolid: string
  border: string
  text: string
  dot: string
  ring: string
}

const COMPANY_PALETTE: CompanyColor[] = [
  {
    bg: 'bg-rose-50 dark:bg-rose-950/40',
    bgSolid: 'bg-rose-500',
    border: 'border-rose-400 dark:border-rose-500',
    text: 'text-rose-900 dark:text-rose-100',
    dot: 'bg-rose-500',
    ring: 'ring-rose-400/40',
  },
  {
    bg: 'bg-amber-50 dark:bg-amber-950/40',
    bgSolid: 'bg-amber-500',
    border: 'border-amber-400 dark:border-amber-500',
    text: 'text-amber-900 dark:text-amber-100',
    dot: 'bg-amber-500',
    ring: 'ring-amber-400/40',
  },
  {
    bg: 'bg-lime-50 dark:bg-lime-950/40',
    bgSolid: 'bg-lime-500',
    border: 'border-lime-400 dark:border-lime-500',
    text: 'text-lime-900 dark:text-lime-100',
    dot: 'bg-lime-500',
    ring: 'ring-lime-400/40',
  },
  {
    bg: 'bg-emerald-50 dark:bg-emerald-950/40',
    bgSolid: 'bg-emerald-500',
    border: 'border-emerald-400 dark:border-emerald-500',
    text: 'text-emerald-900 dark:text-emerald-100',
    dot: 'bg-emerald-500',
    ring: 'ring-emerald-400/40',
  },
  {
    bg: 'bg-teal-50 dark:bg-teal-950/40',
    bgSolid: 'bg-teal-500',
    border: 'border-teal-400 dark:border-teal-500',
    text: 'text-teal-900 dark:text-teal-100',
    dot: 'bg-teal-500',
    ring: 'ring-teal-400/40',
  },
  {
    bg: 'bg-cyan-50 dark:bg-cyan-950/40',
    bgSolid: 'bg-cyan-500',
    border: 'border-cyan-400 dark:border-cyan-500',
    text: 'text-cyan-900 dark:text-cyan-100',
    dot: 'bg-cyan-500',
    ring: 'ring-cyan-400/40',
  },
  {
    bg: 'bg-sky-50 dark:bg-sky-950/40',
    bgSolid: 'bg-sky-500',
    border: 'border-sky-400 dark:border-sky-500',
    text: 'text-sky-900 dark:text-sky-100',
    dot: 'bg-sky-500',
    ring: 'ring-sky-400/40',
  },
  {
    bg: 'bg-blue-50 dark:bg-blue-950/40',
    bgSolid: 'bg-blue-500',
    border: 'border-blue-400 dark:border-blue-500',
    text: 'text-blue-900 dark:text-blue-100',
    dot: 'bg-blue-500',
    ring: 'ring-blue-400/40',
  },
  {
    bg: 'bg-indigo-50 dark:bg-indigo-950/40',
    bgSolid: 'bg-indigo-500',
    border: 'border-indigo-400 dark:border-indigo-500',
    text: 'text-indigo-900 dark:text-indigo-100',
    dot: 'bg-indigo-500',
    ring: 'ring-indigo-400/40',
  },
  {
    bg: 'bg-violet-50 dark:bg-violet-950/40',
    bgSolid: 'bg-violet-500',
    border: 'border-violet-400 dark:border-violet-500',
    text: 'text-violet-900 dark:text-violet-100',
    dot: 'bg-violet-500',
    ring: 'ring-violet-400/40',
  },
  {
    bg: 'bg-fuchsia-50 dark:bg-fuchsia-950/40',
    bgSolid: 'bg-fuchsia-500',
    border: 'border-fuchsia-400 dark:border-fuchsia-500',
    text: 'text-fuchsia-900 dark:text-fuchsia-100',
    dot: 'bg-fuchsia-500',
    ring: 'ring-fuchsia-400/40',
  },
  {
    bg: 'bg-pink-50 dark:bg-pink-950/40',
    bgSolid: 'bg-pink-500',
    border: 'border-pink-400 dark:border-pink-500',
    text: 'text-pink-900 dark:text-pink-100',
    dot: 'bg-pink-500',
    ring: 'ring-pink-400/40',
  },
]

const NEUTRAL_COMPANY_COLOR: CompanyColor = {
  bg: 'bg-zinc-100 dark:bg-zinc-800/60',
  bgSolid: 'bg-zinc-400',
  border: 'border-zinc-300 dark:border-zinc-600',
  text: 'text-zinc-800 dark:text-zinc-200',
  dot: 'bg-zinc-400',
  ring: 'ring-zinc-300/40',
}

export function companyColor(name?: string | null): CompanyColor {
  const norm = (name || '').trim().toLowerCase()
  if (!norm || norm === 'unknown company' || norm === 'unknown') {
    return NEUTRAL_COMPANY_COLOR
  }
  let h = 5381
  for (let i = 0; i < norm.length; i++) {
    h = ((h << 5) + h + norm.charCodeAt(i)) | 0
  }
  return COMPANY_PALETTE[Math.abs(h) % COMPANY_PALETTE.length]
}
