import { type ReactNode, useState } from 'react'
import { FiEye, FiEyeOff } from 'react-icons/fi'
import { cn } from '@/lib/utils'

export function SettingsCard({
  title,
  subtitle,
  children,
  className,
}: {
  title: string
  subtitle?: string
  children: ReactNode
  className?: string
}) {
  return (
    <section
      className={cn(
        'rounded-2xl border border-zinc-900 dark:border-zinc-100 bg-white dark:bg-zinc-950 overflow-hidden',
        className,
      )}
    >
      <header className="px-6 pt-5 pb-4">
        <h2 className="text-base font-semibold text-zinc-900 dark:text-zinc-50">{title}</h2>
        {subtitle ? (
          <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">{subtitle}</p>
        ) : null}
      </header>
      <div className="border-t border-zinc-900/15 dark:border-zinc-100/15">{children}</div>
    </section>
  )
}

export function FieldRow({
  label,
  hint,
  children,
  align = 'center',
}: {
  label: string
  hint?: string
  children: ReactNode
  align?: 'start' | 'center'
}) {
  return (
    <div
      className={cn(
        'grid grid-cols-[200px_1fr] gap-6 px-6 py-4 border-b border-zinc-900/10 dark:border-zinc-100/10 last:border-b-0',
        align === 'start' ? 'items-start' : 'items-center',
      )}
    >
      <div className="text-sm">
        <div className="text-zinc-900 dark:text-zinc-100">{label}</div>
        {hint ? (
          <div className="mt-1 text-xs text-zinc-500 dark:text-zinc-400 leading-snug">{hint}</div>
        ) : null}
      </div>
      <div className="min-w-0">{children}</div>
    </div>
  )
}

export function TextInput(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className={cn(
        'w-full rounded-xl border border-zinc-900/30 dark:border-zinc-100/30 bg-white dark:bg-zinc-950 px-4 py-2.5 text-sm',
        'focus:outline-none focus:border-zinc-900 dark:focus:border-zinc-100',
        'placeholder:text-zinc-400',
        props.className,
      )}
    />
  )
}

export function TextArea(props: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      {...props}
      className={cn(
        'w-full rounded-xl border border-zinc-900/30 dark:border-zinc-100/30 bg-white dark:bg-zinc-950 px-4 py-3 text-sm leading-relaxed resize-y',
        'focus:outline-none focus:border-zinc-900 dark:focus:border-zinc-100',
        'placeholder:text-zinc-400',
        props.className,
      )}
    />
  )
}

export function Select({
  value,
  onChange,
  options,
  className,
}: {
  value: string
  onChange: (v: string) => void
  options: { value: string; label: string }[]
  className?: string
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className={cn(
        'w-full rounded-xl border border-zinc-900/30 dark:border-zinc-100/30 bg-white dark:bg-zinc-950 px-4 py-2.5 text-sm appearance-none',
        'focus:outline-none focus:border-zinc-900 dark:focus:border-zinc-100',
        className,
      )}
    >
      {options.map((o) => (
        <option key={o.value} value={o.value}>
          {o.label}
        </option>
      ))}
    </select>
  )
}

export function MaskedInput({
  value,
  onChange,
  placeholder,
}: {
  value: string
  onChange: (v: string) => void
  placeholder?: string
}) {
  const [revealed, setRevealed] = useState(false)
  const display = revealed
    ? value
    : value
      ? value.slice(0, 7) + '•'.repeat(Math.max(8, Math.min(20, value.length - 7)))
      : ''
  return (
    <div className="relative">
      <input
        type={revealed ? 'text' : 'text'}
        value={display}
        onChange={(e) => {
          if (revealed) onChange(e.target.value)
        }}
        readOnly={!revealed}
        placeholder={placeholder}
        className={cn(
          'w-full rounded-xl border border-zinc-900/30 dark:border-zinc-100/30 bg-white dark:bg-zinc-950 px-4 py-2.5 pr-10 text-sm font-mono tracking-wide',
          'focus:outline-none focus:border-zinc-900 dark:focus:border-zinc-100',
        )}
      />
      <button
        type="button"
        onClick={() => setRevealed((r) => !r)}
        aria-label={revealed ? 'Hide' : 'Reveal'}
        className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100"
      >
        {revealed ? <FiEyeOff className="h-4 w-4" /> : <FiEye className="h-4 w-4" />}
      </button>
    </div>
  )
}

export function Toggle({
  checked,
  onChange,
  label,
}: {
  checked: boolean
  onChange: (v: boolean) => void
  label?: string
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      onClick={() => onChange(!checked)}
      className={cn(
        'relative inline-flex h-6 w-11 shrink-0 rounded-full border transition-colors',
        checked
          ? 'bg-zinc-900 border-zinc-900 dark:bg-zinc-100 dark:border-zinc-100'
          : 'bg-white border-zinc-900/40 dark:bg-zinc-950 dark:border-zinc-100/40',
      )}
    >
      <span
        className={cn(
          'absolute top-1/2 -translate-y-1/2 h-4 w-4 rounded-full transition-all',
          checked
            ? 'left-[calc(100%-1.25rem)] bg-white dark:bg-zinc-900'
            : 'left-1 bg-zinc-900 dark:bg-zinc-100',
        )}
      />
    </button>
  )
}

export function GhostButton({
  children,
  className,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      {...props}
      className={cn(
        'inline-flex items-center justify-center gap-2 rounded-xl border border-zinc-900/30 dark:border-zinc-100/30 px-4 py-2 text-sm',
        'hover:border-zinc-900 dark:hover:border-zinc-100 transition-colors',
        'disabled:opacity-50 disabled:cursor-not-allowed',
        className,
      )}
    >
      {children}
    </button>
  )
}

export function Chip({
  children,
  onRemove,
}: {
  children: ReactNode
  onRemove?: () => void
}) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-lg border border-zinc-900/30 dark:border-zinc-100/30 px-3 py-1 text-sm">
      {children}
      {onRemove ? (
        <button
          type="button"
          onClick={onRemove}
          className="text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100"
          aria-label="Remove"
        >
          ×
        </button>
      ) : null}
    </span>
  )
}

export function StatusOk({ children }: { children: ReactNode }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-sm text-emerald-700 dark:text-emerald-400">
      <span aria-hidden>✓</span>
      <span className="text-zinc-700 dark:text-zinc-300">{children}</span>
    </span>
  )
}

export function StatusBad({ children }: { children: ReactNode }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-sm text-rose-700 dark:text-rose-400">
      <span aria-hidden>✗</span>
      <span>{children}</span>
    </span>
  )
}
