import { FiX, FiExternalLink, FiBookmark, FiMapPin, FiClock, FiUsers, FiDollarSign, FiFileText, FiCalendar, FiSend, FiSlash } from 'react-icons/fi'
import { useEffect, useRef, useState } from 'react'
import { useJob, useUpdateJob } from '@/hooks/useJobs'
import { useSettings } from '@/hooks/useSettings'
import { JobLabels } from './JobLabels'
import { FollowupList } from '@/features/bookmarks/FollowupList'
import { InterviewList } from '@/features/interviews/InterviewList'
import { cn, formatRelative, nextActionFor, scoreColor, statusColor, statusLabel } from '@/lib/utils'
import { PIPELINE_STAGES } from '@/lib/types'

const ALL_STATUSES = ['new', ...PIPELINE_STAGES.map((s) => s.id)]

export function JobDetailDrawer({ jobId, onClose }: { jobId: string | null; onClose: () => void }) {
  const { data: job } = useJob(jobId)
  const update = useUpdateJob()
  const { data: settings } = useSettings()
  const matchingEnabled = settings?.enable_resume_matching ?? true
  const [notes, setNotes] = useState('')
  const followupRef = useRef<HTMLElement | null>(null)

  useEffect(() => {
    setNotes(job?.notes || '')
  }, [job?.job_id])

  if (jobId == null) return null
  const labels: string[] = job?.tags || []

  const saveNotes = () => {
    if (!job) return
    if (notes !== (job.notes || '')) update.mutate({ jobId: job.job_id, body: { notes } })
  }

  const setStatus = (status: string) => {
    if (job) update.mutate({ jobId: job.job_id, body: { status } })
  }

  const scrollToFollowups = () => {
    followupRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }

  return (
    <div className="fixed inset-0 z-40 flex" role="dialog" aria-modal="true">
      <div className="flex-1 bg-zinc-900/30 dark:bg-black/50" onClick={onClose} />
      <aside className="w-full max-w-xl h-full bg-white dark:bg-zinc-900 border-l border-zinc-200 dark:border-zinc-800 flex flex-col">
        <div className="h-14 px-5 flex items-center justify-between border-b border-zinc-200 dark:border-zinc-800">
          <div className="flex items-center gap-1.5">
            <button
              className="btn-ghost"
              onClick={() => setStatus(job?.status === 'saved' ? 'new' : 'saved')}
            >
              <FiBookmark className={cn('h-4 w-4', job?.status === 'saved' && 'fill-current text-brand-600')} />
              {job?.status === 'saved' ? 'Saved' : 'Save'}
            </button>
            <button className="btn-ghost" onClick={() => setStatus('rejected')}>
              <FiSlash className="h-4 w-4" /> Reject
            </button>
            {job?.url ? (
              <a className="btn-ghost" href={job.url} target="_blank" rel="noreferrer">
                <FiExternalLink className="h-4 w-4" /> Open
              </a>
            ) : null}
          </div>
          <button className="btn-ghost" onClick={onClose} aria-label="Close">
            <FiX className="h-5 w-5" />
          </button>
        </div>
        <div className="flex-1 overflow-auto px-5 py-5 space-y-6">
          {!job ? (
            <div className="text-sm text-zinc-500">Loading…</div>
          ) : (
            <>
              <div>
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h2 className="text-xl font-semibold leading-tight">{job.title}</h2>
                    <div className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">{job.company}</div>
                  </div>
                  {matchingEnabled && job.resume_match_score != null ? (
                    <span className={cn('chip text-sm font-semibold', scoreColor(job.resume_match_score))}>
                      {Math.round(job.resume_match_score)}% match
                    </span>
                  ) : null}
                </div>
                <div className="mt-3 flex flex-wrap gap-3 text-xs text-zinc-500 dark:text-zinc-400">
                  {job.location ? <span className="flex items-center gap-1"><FiMapPin className="h-3 w-3" />{job.location}</span> : null}
                  {job.posted_date ? <span className="flex items-center gap-1"><FiClock className="h-3 w-3" />{formatRelative(job.posted_date)}</span> : null}
                  {job.applicants_count != null ? <span className="flex items-center gap-1"><FiUsers className="h-3 w-3" />{job.applicants_count}</span> : null}
                  {job.salary_range ? <span className="flex items-center gap-1"><FiDollarSign className="h-3 w-3" />{job.salary_range}</span> : null}
                  {job.source ? <span className="chip bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400">{job.source}</span> : null}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <button className="btn-primary justify-center" onClick={() => setStatus('tailoring_resume')}>
                  <FiFileText className="h-4 w-4" /> Tailor Resume
                </button>
                <button className="btn-primary justify-center" onClick={() => setStatus('applied')}>
                  <FiSend className="h-4 w-4" /> Mark Applied
                </button>
                <button className="btn-ghost justify-center col-span-2" onClick={scrollToFollowups}>
                  <FiCalendar className="h-4 w-4" /> Schedule Follow-up
                </button>
              </div>

              <div className="rounded-md border border-zinc-200 dark:border-zinc-800 bg-zinc-50/60 dark:bg-zinc-900/40 px-3 py-2 text-xs flex items-center justify-between">
                <span className="text-zinc-500 dark:text-zinc-400">Next action</span>
                <span className="font-medium text-zinc-800 dark:text-zinc-200">{nextActionFor(job.status)}</span>
              </div>

              <Section title="Stage">
                <div className="flex flex-wrap gap-1.5">
                  {ALL_STATUSES.map((s) => (
                    <button
                      key={s}
                      onClick={() => setStatus(s)}
                      className={cn(
                        'chip',
                        job.status === s
                          ? statusColor(s) + ' ring-2 ring-offset-1 ring-brand-500 dark:ring-offset-zinc-900'
                          : statusColor(s) + ' opacity-50 hover:opacity-100'
                      )}
                    >
                      {statusLabel(s)}
                    </button>
                  ))}
                </div>
              </Section>

              {matchingEnabled && job.match_reasons && job.match_reasons.length > 0 ? (
                <Section title="Why it matches">
                  <ul className="space-y-1 text-sm">
                    {job.match_reasons.map((r, i) => (
                      <li key={i} className="flex gap-2 text-zinc-700 dark:text-zinc-300">
                        <span className="text-emerald-500 mt-0.5">✓</span>
                        <span>{r}</span>
                      </li>
                    ))}
                  </ul>
                </Section>
              ) : null}

              {matchingEnabled && job.resume_gaps && job.resume_gaps.length > 0 ? (
                <Section title="Resume gaps">
                  <ul className="space-y-1 text-sm">
                    {job.resume_gaps.map((g, i) => (
                      <li key={i} className="flex gap-2 text-zinc-700 dark:text-zinc-300">
                        <span className="text-rose-500 mt-0.5">✗</span>
                        <span>{g}</span>
                      </li>
                    ))}
                  </ul>
                </Section>
              ) : null}

              <Section title="Labels">
                <JobLabels jobId={job.job_id} labels={labels} />
              </Section>

              <Section title="Notes">
                <textarea
                  className="input min-h-[120px]"
                  value={notes}
                  placeholder="Recruiter contact, observations…"
                  onChange={(e) => setNotes(e.target.value)}
                  onBlur={saveNotes}
                />
              </Section>

              <section ref={followupRef as React.RefObject<HTMLElement>}>
                <h3 className="text-xs uppercase tracking-wide text-zinc-500 dark:text-zinc-400 mb-2">Follow-ups</h3>
                <FollowupList jobId={job.job_id} />
              </section>

              <Section title="Interviews">
                <InterviewList jobId={job.job_id} />
              </Section>

              {job.skills && job.skills.length > 0 ? (
                <Section title="Skills">
                  <div className="flex flex-wrap gap-1.5">
                    {job.skills.map((s) => (
                      <span key={s} className="chip bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300">{s}</span>
                    ))}
                  </div>
                </Section>
              ) : null}

              {job.responsibilities && job.responsibilities.length > 0 ? (
                <Section title="Responsibilities">
                  <ul className="list-disc pl-5 space-y-1 text-sm text-zinc-700 dark:text-zinc-300">
                    {job.responsibilities.map((r, i) => <li key={i}>{r}</li>)}
                  </ul>
                </Section>
              ) : null}

              {job.requirements && job.requirements.length > 0 ? (
                <Section title="Requirements">
                  <ul className="list-disc pl-5 space-y-1 text-sm text-zinc-700 dark:text-zinc-300">
                    {job.requirements.map((r, i) => <li key={i}>{r}</li>)}
                  </ul>
                </Section>
              ) : null}

              {job.description ? (
                <Section title="Description">
                  <div className="text-sm text-zinc-700 dark:text-zinc-300 whitespace-pre-wrap">{job.description}</div>
                </Section>
              ) : null}
            </>
          )}
        </div>
      </aside>
    </div>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section>
      <h3 className="text-xs uppercase tracking-wide text-zinc-500 dark:text-zinc-400 mb-2">{title}</h3>
      {children}
    </section>
  )
}
