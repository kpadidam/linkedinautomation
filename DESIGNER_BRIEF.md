# Designer Brief — LinkedIn Job Automation

> **Read this first.** This document describes **what the product does**, not how it should look. Information architecture, navigation pattern, layout, visual language, and interaction model are **all your call**. Do not assume the existing UI is correct — it's a working v1 built without a designer. Treat it as a feature inventory, not a reference design.

---

## How to use this document

1. **Read end-to-end before sketching.** Some features depend on others (e.g. the scraper feeds the queue, the queue feeds the pipeline, the pipeline feeds the calendar).
2. **Research deeply.** Look at how Huntr, Teal, Simplify, Notion job trackers, Pipedrive, Linear, and Trello solve similar problems. The user has not committed to any IA pattern — sidebar, top-nav, bento dashboard, command palette, modal-first, drawer-first are all on the table.
3. **Decide for yourself**: nav model, page count, what collapses into one screen vs. splits into many, what's a modal vs. a drawer vs. a full page, dense vs. spacious, light vs. dark first.
4. **Question the existing screens.** The current 6-screen split (Dashboard / Queue / Pipeline / Calendar / Session / Settings) is one possible decomposition. You may find that Queue and Pipeline are the same surface in two views, or that Session belongs in Settings, or that the Dashboard should be the homepage of every screen, etc. Justify your choice; don't inherit it.

---

## 1. Product in one paragraph

A **personal AI job-hunting assistant** that runs locally on the user's machine. The user defines what jobs they want and feeds it their resume. A **headless browser driven by GPT-4** scrapes LinkedIn Jobs continuously. Each scraped job is **scored against the user's resume by an LLM (0–100% match)**. Jobs flow through a Kanban-style pipeline (Saved → Applied → Interviews → Offer / Rejected). Interviews and follow-up reminders are tracked. Everything is mirrored in real time to a **Google Sheet**. Single-user, no auth, no multi-tenancy.

---

## 2. Who is this for

A **single power-user** managing their own job search. Likely technical-leaning. Wants control, transparency (sees the scraper logs), and density of information. Will spend 30+ minutes/day in the tool. Already comfortable with developer tools, spreadsheets, and Kanban boards. Not a casual user — designs that are too hand-holding will feel patronizing.

---

## 3. The complete feature inventory

### 3.1 Job discovery (the scraper)

- **One-shot search** — user enters keywords, location, filters (job type, experience level, remote, posted-within: 24h/week/month), max results, toggles (LLM matching on/off, save-to-sheets on/off). Backend launches an async background task. UI must reflect progress (started → running → completed/failed) and final counts (jobs scraped, jobs matched).
- **Background scraper session** — long-running process that the user starts/stops. Has live state: idle / running (PID, started-at) / stopped (exit code).
- **Live log stream** — Server-Sent Events feed of every line the scraper writes. Auto-scroll, pause, clear, line count. The user *will* watch this — it's how they trust the system is working.
- **Search history** — every search run is persisted with: keywords, location, all filters, started_at, completed_at, duration_seconds, total_results, jobs_scraped, jobs_matched, status (running/completed/failed), error_message.

### 3.2 Job triage (the queue)

- A **list of every scraped job**, refreshing live (currently every 5 s).
- **Filters**: free-text (title / company / location), status, minimum match score.
- **Sorting**: by match score, scraped date, title, company, location.
- **Counter**: "X of Y" filtered/total.
- **Bulk actions are not yet implemented** — opportunity for designer to spec.

### 3.3 Job detail surface

This is the **most-reused element in the product**. It opens from the queue, the pipeline, and the calendar. It must contain **all** of the following on one job:

- Title, company, location, URL (link out to LinkedIn).
- Full description, requirements (list), qualifications (list), responsibilities (list), benefits (list).
- Job type, experience level, salary range, employment type, industry, company size.
- Posted date, application deadline, applicants count.
- **Match score** (0–100) + **match reasons** (LLM-generated list explaining the score) + matching skills + missing skills.
- Extracted keywords and skills.
- **Editable**: status (changes the Kanban column), notes (free text), tags/labels (chips).
- Tracking flags: viewed (auto-set on open), applied (auto-set when status → applied), applied_date.
- Linked **followups** and **interview events** for this job.

### 3.4 Pipeline (application tracking)

A **Kanban with 8 stages**, in this exact order:

`Saved → Tailoring Resume → Applied → Recruiter Screen → Technical Interview → Final → Offer → Rejected`

- Cards are draggable between stages. Drag = status update via API.
- Cards must show: title, company, location, match score, **age in days** (since scraped or since last status change).
- **Smart badges** the system already computes:
  - "Stale 7d" — job has sat in current stage ≥ 7 days, status not offer/rejected.
  - "High match · apply" — job is in *Saved* and match score ≥ 85.
- Click card → opens job detail surface.
- Counter: total jobs in pipeline.
- **8 columns is a lot** — designer must decide: horizontal scroll, collapsible groups, swimlanes, alternative views (list grouped by stage, table with stage as a column, etc.).

### 3.5 Calendar (interview tracking)

- Month view with interview events plotted on dates.
- Each event: linked job, **stage** (phone / tech / onsite / final / offer — free string today, designer can propose a fixed taxonomy), datetime, location (text — could be a URL for video, an address, or a room), notes.
- Click event → opens linked job's detail surface.
- Add / edit / delete inline.
- Month nav + "Today" jump.
- **Open design questions**: week view? day view? agenda view? timezone handling? recurring events? drag-to-reschedule?

### 3.6 Followups / reminders

- Per-job reminders. Fields: due_at (datetime), note (text), done (bool).
- Listed on the dashboard with overdue highlighting.
- Full CRUD.
- **Open design question**: are these surfaced as a separate "Tasks" view, embedded in the job detail, or both?

### 3.7 Dashboard / home

Currently shows:

- **Stat cards** (6): new jobs in last 24h, saved, high matches (≥80%), applied, interviews, offers.
- **"Today's Plan"** — dynamic action list (review N new jobs, complete N followups, prep for N upcoming interviews).
- **Recent searches** summary (last few scrape runs + counts).
- **Top 5 best-matched jobs** (by match score).
- **Upcoming followups** with overdue flags.

Designer should treat the dashboard as a **decision surface** ("what should I do right now?") rather than just a metrics dashboard. The user is here to act, not to admire numbers.

### 3.8 Profile / preferences / configuration

The product has **multiple configuration layers** that need surfacing:

**A. User profile (UI-editable today):**
- Name, email
- **Resume text** (pasted or uploaded — the LLM reads this for matching)
- **Skills** (list of strings)
- **Preferred locations** (list)
- **Search roles** (list of titles to scrape, e.g. "Frontend Engineer", "Product Engineer" — overrides the file-based config below)

**B. File-based job preferences** (`config/job_preferences.json` — currently invisible in UI, **opportunity to surface**):
- Multiple **job categories**, each with: category name, keywords[], required skills[], location, remote_ok flag, job_type[], experience_level, posted_within (week/month), max_results.
- Defaults: enable_matching, save_to_sheets, min_match_threshold, search_delay_seconds.

**C. Environment variables** (`.env` — invisible in UI today, **major opportunity**):
- API keys: OpenAI, Groq, Google Sheets credentials, Google Sheets ID
- LinkedIn credentials (optional)
- Feature flag: `ENABLE_RESUME_MATCHING` (toggles LLM scoring globally; requires restart today)
- Browser flags: headless on/off, timeout
- Defaults: location, job type, max results per search, delay between requests
- Resume file path

**D. User profile flags (in DB, partly UI):**
- auto_search_enabled, search_frequency_hours, last_auto_search (cron-style; **scheduler infra exists but is empty — feature is essentially unbuilt**)
- email_notifications, min_match_score_alert (threshold for high-match alerts; **also unbuilt end-to-end**)

**Designer task**: design a real **Settings / Integrations / Preferences** experience. Today's settings page is a stub. There should probably be sections for: Profile & Resume, Search Roles & Categories, Integrations (OpenAI key, Google Sheets, LinkedIn), Automation (auto-search schedule, notification thresholds), System (feature flags, browser config, data cleanup).

### 3.9 First-run / onboarding

**Currently does not exist.** When the user starts the app for the first time, they need to:

1. Provide an OpenAI (or Groq) API key.
2. Connect Google Sheets (service account JSON + sheet ID, or auto-create a sheet).
3. Optionally provide LinkedIn credentials.
4. Paste / upload their resume.
5. Define their target roles, skills, locations.
6. Run their first search.

Right now the user has to edit `.env` files and JSON manually. **Designing this onboarding flow is a high-leverage task.**

### 3.10 Integrations (must be visible somewhere)

- **OpenAI / Groq** — LLM for resume matching + Browser-Use scraping. Status (connected / key invalid / quota exhausted) should be visible.
- **Google Sheets** — auto-creates a sheet named "LinkedIn Jobs" with **18 columns** (Job ID, Date, Time, Role, Company, Location, Job Type, Level, Link, Responsibilities, Preferred Skills, Matching Skills, Role Match %, Salary, Posted, Number of Applicants, Status, Notes). Sheet URL must be linkable from the UI. User can trigger "create new sheet."
- **LinkedIn** — login is optional. The scraper can run logged-out but gets better results logged in. Credentials live in `.env`.
- **Email notifications** — flag exists, implementation is partial.

### 3.11 System actions

- **Cleanup old data** — delete records older than N days (7–365). Currently a single endpoint, no UI.
- **Database export** — not currently exposed; could be designed.
- **Health check** — endpoint exists; no UI.

---

## 4. The data model (so you know what fields exist on every screen)

### Job — the central entity

```
job_id (unique), title, company, location, url,
description, requirements[], qualifications[], responsibilities[], benefits[],
job_type, experience_level, salary_range, employment_type,
industry, company_size,
posted_date, application_deadline, applicants_count,
scraped_at, last_updated, source ("LinkedIn"),
status, keywords[], skills[],
resume_match_score (0–100), match_reasons[],
notes, tags[],
viewed (bool), applied (bool), applied_date
```

### Job statuses (the Kanban columns + initial state)
`new → saved → tailoring_resume → applied → recruiter_screen → technical_interview → final → offer | rejected`

There is also a legacy `interviewing` and `viewed` status floating around — designer can propose deprecating these.

### SearchRun
`search_id, keywords, location, job_type, experience_level, remote, posted_within, total_results, jobs_scraped, jobs_matched, started_at, completed_at, duration_seconds, status, error_message`

### UserProfile
`name, email, resume_text, resume_file_path, skills[], preferred_locations[], preferred_job_types[], search_roles[], minimum_salary, auto_search_enabled, search_frequency_hours, last_auto_search, email_notifications, min_match_score_alert`

### Followup
`id, job_id, due_at, note, done, created_at`

### InterviewEvent
`id, job_id, stage, scheduled_at, location, notes, created_at`

### AnalysisCache
`job_id, analysis_type, analysis_result, created_at, expires_at` *(LLM result cache — invisible to user but it's why the system feels fast on revisits)*

### LLM analysis output (per job)
`technical_skills[], soft_skills[], tools_technologies[], certifications[], overall_match_score, skills_match_score, experience_match_score, missing_skills[], matching_skills[], recommendations[], ai_summary, ai_fit_assessment, interview_tips[]`

The **interview_tips, ai_summary, and ai_fit_assessment** fields exist in the model but are **not currently surfaced anywhere in the UI**. Big design opportunity.

---

## 5. All API endpoints (so you know what the frontend can fetch)

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | Service alive check |
| POST | `/api/search` | Start a one-shot search (background task) |
| GET | `/api/search/{search_id}` | Poll one search's progress |
| GET | `/api/jobs` | List jobs (limit, offset, status, min_score) |
| GET | `/api/jobs/{job_id}` | Single job + auto-marks viewed |
| PUT | `/api/jobs/{job_id}` | Update status / notes / labels |
| GET | `/api/profile` | Read profile + prefs |
| PUT | `/api/profile` | Save profile (re-inits LLM matcher with new resume) |
| GET | `/api/statistics` | Dashboard aggregates (totals, applied, high matches, avg score, sheet URL) |
| GET | `/api/searches` | Recent search runs list |
| POST | `/api/sheets/create` | Create new Google Sheet |
| POST | `/api/cleanup` | Delete old records (days param 7–365) |
| GET | `/api/sessions/status` | Background scraper status (running, PID, started_at, exit_code) |
| POST | `/api/sessions/start` | Start background scraper |
| POST | `/api/sessions/stop` | Stop background scraper |
| GET | `/api/sessions/logs/stream` | **SSE live log feed** |
| GET / POST / PUT / DELETE | `/api/followups[/:id]` | Reminder CRUD |
| GET / POST / PUT / DELETE | `/api/interviews[/:id]` | Interview event CRUD |

---

## 6. State machines & lifecycles (design the transitions)

**Job lifecycle:**
`scraped (new) → viewed → saved → tailoring_resume → applied (sets applied_date) → recruiter_screen → technical_interview → final → offer | rejected`

Edge cases: skipping stages (saved → applied), going backward (rejected → applied if resurrected), multiple parallel applications at the same company. Designer should decide what's allowed.

**Search run:**
`queued → running → completed | failed (with error_message)`
Failures need a UI — currently only logged.

**Background scraper session:**
`idle → running (PID assigned, log stream live) → idle (exit_code captured)`
Crashes vs. clean stops are different states the user cares about.

**Auto-search (planned, not yet built):**
`auto_search_enabled + search_frequency_hours → fires every N hours → updates last_auto_search`

---

## 7. Live / streaming surfaces (special design care)

These pieces are **not static** and need explicit thought about loading, empty, stale, error, and streaming states:

1. **Review queue list** — polls every 5 s. New rows can appear at any time. How do they enter? Highlight? Counter increment animation?
2. **Scraper log feed** — SSE. Lines arrive one at a time, fast. Auto-scroll vs. pause. Error lines vs. info lines vs. success lines.
3. **Search progress** — long-running task. Spinner? Progress bar? Per-job feedback ("Just found: Senior Engineer @ Acme")?
4. **Session status** — running indicator must always be honest. What if the process crashes mid-session?
5. **Match score computation** — LLM call takes seconds. Show pending state per job? Block save? Best-effort with retry?

---

## 8. UX moments worth highlighting

- **Match score is the most important number in the product.** The user looks at it on every job. Color/scale/threshold language must be designed deliberately. Score `0` (unscored) and score `null` (matching disabled) are different states and should look different.
- **The system already has opinions** — "Stale 7d" warnings, "High match · apply" nudges, "Today's Plan" action list. The product has a voice; the design should reinforce that opinionated, prescriptive voice.
- **The user is also a developer.** A live log feed, a PID readout, and `.env` configuration are not weird here. Power-user surfaces (keyboard shortcuts, command palette, dense tables) will be appreciated.
- **Single-user, local app.** No accounts, no avatars, no team features, no notifications-bell-icon-with-badge-count UX. Don't design for a SaaS.
- **No login / onboarding exists.** This is the biggest greenfield design surface.
- **Many backend features are not surfaced in the UI yet** — auto-search scheduler, email notifications, AI interview tips, AI fit assessment, AI summary, cleanup, search-run failure handling, file-based config editing. Decide what's worth surfacing and when.

---

## 9. What the current UI looks like (reference only — not a constraint)

For context, the existing v1 has 6 routes: Dashboard, Review Queue, Pipeline, Calendar, Session, Settings, with a job detail panel that opens as a side drawer from three of them. There's a sidebar + header layout. **None of this is sacred.** If you think the right answer is a single-page app with a command palette, or a three-pane email-client layout, or a tabbed Notion-style workspace, propose it.

---

## 10. Tech context (for feasibility, not for design)

- React + TypeScript + Vite SPA
- React Router for routing (any nav model is implementable)
- React Query for data fetching (live polling already in place)
- SSE for log streaming (works in browser natively)
- FastAPI backend, all data over JSON-REST
- No design system in place — you're free to pick / build one (Tailwind is in the stack, but switching is fine)
- No accessibility audit has been done — please make the redesign WCAG-aware from the start

---

## 11. Your deliverables (suggested — adjust as you see fit)

1. **Research summary** — competitive scan of Huntr, Teal, Simplify, Notion templates, plus any non-obvious references (CRMs, IDEs, terminals — this product has DNA from all of them).
2. **IA & nav decision** — what are the top-level surfaces, how does the user move between them, how does the job detail surface integrate.
3. **Wireframes** — every screen, including empty states, loading states, error states, and the onboarding flow.
4. **High-fidelity designs** — for at least: dashboard, queue, pipeline, calendar, job detail, scraper-running state, settings/integrations, onboarding.
5. **Interaction notes** — drag-and-drop behavior, keyboard shortcuts, live-update animations, modal vs. drawer rules.
6. **Design system** — type scale, color (including match-score color ramp), spacing, components.

---

## 12. Open questions for the user

Things the user has not yet decided — flag these and ask before finalizing:

- Light mode, dark mode, or both?
- Mobile / responsive? (Currently desktop-only; the user may or may not care.)
- Brand identity / tone — is this a tool that feels like Linear (sharp, opinionated), Notion (warm, flexible), or a Bloomberg terminal (dense, info-first)?
- Is multi-user / sharing ever in scope? (Currently no, but it changes architecture if yes.)
- Any specific competitor whose UX they admire?

---

**TL;DR for the designer:**

> Single-user local job-hunting tool. AI scrapes LinkedIn, scores jobs vs. resume, tracks them through an 8-stage pipeline, schedules interviews, reminds about followups, mirrors everything to a Google Sheet. Live data everywhere. No login. No onboarding yet. The job detail surface is the most-reused element. Match score is the most important number. The system has opinions ("stale", "apply now"). Design from scratch — don't inherit the v1.
