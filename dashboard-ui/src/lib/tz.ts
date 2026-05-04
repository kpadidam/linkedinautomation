// Helpers for rendering interview times in two timezones.

export function getLocalTz(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC'
  } catch {
    return 'UTC'
  }
}

const TZ_LABELS: Record<string, string> = {
  'America/Los_Angeles': 'Pacific',
  'America/Denver': 'Mountain',
  'America/Chicago': 'Central',
  'America/New_York': 'Eastern',
  'Europe/London': 'London',
  'Europe/Berlin': 'Berlin',
  'Europe/Paris': 'Paris',
  'Asia/Kolkata': 'India',
  'Asia/Singapore': 'Singapore',
  'Asia/Tokyo': 'Tokyo',
  'Australia/Sydney': 'Sydney',
}

const TZ_ABBREVS: Record<string, string> = {
  'America/Los_Angeles': 'PT',
  'America/Denver': 'MT',
  'America/Chicago': 'CT',
  'America/New_York': 'ET',
  'Europe/London': 'UK',
  'Europe/Berlin': 'CET',
  'Europe/Paris': 'CET',
  'Asia/Kolkata': 'IST',
  'Asia/Singapore': 'SGT',
  'Asia/Tokyo': 'JST',
  'Australia/Sydney': 'AET',
}

export function tzLabel(tz: string): string {
  return TZ_LABELS[tz] || tz.split('/').pop() || tz
}

export function tzAbbrev(tz: string): string {
  return TZ_ABBREVS[tz] || tz.split('/').pop() || tz
}

export function formatInTz(date: Date | string, tz: string, opts?: Intl.DateTimeFormatOptions): string {
  const d = typeof date === 'string' ? new Date(date) : date
  return new Intl.DateTimeFormat(undefined, {
    hour: 'numeric',
    minute: '2-digit',
    timeZone: tz,
    ...opts,
  }).format(d)
}

/**
 * Returns true when an interviewer_tz is set AND it differs from the user's
 * local IANA timezone. Empty / null means "same as me" → no dual-display.
 */
export function shouldShowDualTime(interviewerTz?: string | null, localTz?: string): boolean {
  if (!interviewerTz) return false
  const local = localTz ?? getLocalTz()
  return interviewerTz !== local
}

/** "(2:00 PM Eastern · 11:00 AM here)" */
export function formatDualTime(date: Date | string, interviewerTz: string): string {
  const them = formatInTz(date, interviewerTz)
  const me = (typeof date === 'string' ? new Date(date) : date).toLocaleTimeString(undefined, {
    hour: 'numeric',
    minute: '2-digit',
  })
  return `(${them} ${tzLabel(interviewerTz)} · ${me} here)`
}

/** "2:00 PM ET" — compact form for tight chips. */
export function formatCompactWithTz(date: Date | string, interviewerTz: string): string {
  return `${formatInTz(date, interviewerTz)} ${tzAbbrev(interviewerTz)}`
}
