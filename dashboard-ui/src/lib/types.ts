export type JobStatus =
  | 'new'
  | 'saved'
  | 'tailoring_resume'
  | 'applied'
  | 'recruiter_screen'
  | 'technical_interview'
  | 'final'
  | 'interviewing'
  | 'offer'
  | 'rejected'

export const PIPELINE_STAGES: { id: Exclude<JobStatus, 'new'>; label: string }[] = [
  { id: 'saved', label: 'Saved' },
  { id: 'tailoring_resume', label: 'Tailoring Resume' },
  { id: 'applied', label: 'Applied' },
  { id: 'recruiter_screen', label: 'Recruiter Screen' },
  { id: 'technical_interview', label: 'Technical Interview' },
  { id: 'final', label: 'Final' },
  { id: 'offer', label: 'Offer' },
  { id: 'rejected', label: 'Rejected' },
]

export interface Job {
  id: number
  job_id: string
  title: string
  company: string
  location?: string | null
  url?: string | null
  description?: string | null
  requirements?: string[] | null
  qualifications?: string[] | null
  responsibilities?: string[] | null
  benefits?: string[] | null
  job_type?: string | null
  experience_level?: string | null
  salary_range?: string | null
  employment_type?: string | null
  industry?: string | null
  company_size?: string | null
  posted_date?: string | null
  application_deadline?: string | null
  applicants_count?: number | null
  scraped_at?: string | null
  last_updated?: string | null
  source?: string | null
  status?: JobStatus | string | null
  keywords?: string[] | null
  skills?: string[] | null
  resume_match_score?: number | null
  match_reasons?: string[] | null
  resume_gaps?: string[] | null
  notes?: string | null
  tags?: string[] | null
  viewed?: boolean
  applied?: boolean
  applied_date?: string | null
  // Slice 1 — local semantic matcher outputs (services/embed_matcher.py).
  // `match_score` is the raw composite in [0, 1]; the legacy
  // `resume_match_score` field is the older LLM-based score in [0, 100].
  // Prefer `match_score` via `effectiveMatchScore()` in lib/utils.ts.
  apply_status?: 'eligible' | 'not_eligible' | 'approved' | 'applying' | 'applied' | 'failed_retryable' | 'failed_terminal' | 'skipped_duplicate' | string | null
  match_score?: number | null
  match_score_percentile?: number | null
  match_computed_at?: string | null
}

export interface SearchRun {
  id: number
  search_id: string
  keywords?: string
  location?: string
  jobs_scraped?: number
  jobs_matched?: number
  status?: string
  started_at?: string
  completed_at?: string | null
  duration_seconds?: number | null
}

export interface Statistics {
  total_jobs: number
  applied_jobs: number
  high_match_jobs: number
  average_match_score: number
}

export interface JobsQuery {
  limit?: number
  offset?: number
  status?: string
  min_score?: number
}

export interface JobUpdate {
  status?: string
  notes?: string
  labels?: string[]
}

/**
 * One attempt by the auto-apply loop to apply to one job.
 * See database/models.py::ApplicationRun for the state taxonomy.
 */
export interface ApplicationRun {
  id: number
  job_id: string
  ats: string
  state:
    | 'opened'
    | 'form_parsed'
    | 'needs_user_input'
    | 'ready_to_submit'
    | 'submitted'
    | 'submitted_dry_run'
    | 'blocked_captcha'
    | 'blocked_auth'
    | 'failed_retryable'
    | 'failed_terminal'
    | 'failed_unavailable'
    | string
  started_at: string | null
  ended_at: string | null
  exit_reason: string | null
  screenshot_paths: string[]
  form_log: unknown[]
  error_message: string | null
  dedup_key: string | null
}

export interface CircuitStatus {
  tripped: boolean
  tripped_at: string | null
  reason: string | null
  consecutive_failures: number
}
