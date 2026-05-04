export interface Interview {
  id: number
  job_id: string
  stage: string
  scheduled_at: string
  location?: string | null
  notes?: string | null
  interviewer_tz?: string | null
  created_at?: string
}

export interface Followup {
  id: number
  job_id: string
  due_at: string
  note?: string | null
  done?: boolean
  created_at?: string
}
