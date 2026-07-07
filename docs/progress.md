# Progress — auto-apply build

What's actually shipped, what's uncommitted in the working tree, and what's
next. Pair with `docs/auto-apply-plan.md` (forward-looking) and the
`.paircode/focus-*/` directories (peer-review audit trail).

Branch: `feat/dagster-auto-apply` (name retained for continuity; the
implementation does **not** use Dagster — APScheduler instead).

---

## Status legend

- ✅ committed and pushed
- 🟡 in working tree, uncommitted (verify locally before committing)
- ⬜ planned, not started

---

## Slice 0 — Foundation (committed before this branch)

| | Work | Where |
|---|---|---|
| ✅ | Existing FastAPI backend + React/Vite dashboard + SQLite | repo root |
| ✅ | LinkedIn scraper (Playwright, persistent profile) | `scrapers/linkedin_scraper_robust.py` |
| ✅ | Scrape session manager with SSE log stream + Pause/Resume | `services/session_manager.py` |
| ✅ | Auto-search scheduler (`_auto_search_loop`) — minute-precision cadence | `app/main.py:190` |
| ✅ | OpenAI/Groq resume matcher (the *old* LLM matcher — kept for back-compat) | `services/resume_matcher.py` |
| ✅ | Google Sheets export | `services/google_sheets_service.py` |
| ✅ | Setup wizard + gated session start + editable secrets in DB | dashboard + `app/main.py` |
| ✅ | UTC timestamp serialization (`_utc_iso`) | `database/models.py`, `services/session_manager.py` |
| ✅ | Auto-search baseline reset bug fix | `app/main.py` (commit `48be1c4`) |

## Slice 0.5 — Cross-platform support + plan (committed on this branch)

| | Work | Commit |
|---|---|---|
| ✅ | Windows bootstrap / setup / start scripts | `aa0bc33` |
| ✅ | Pinned `requirements-lock.txt` (uvloop gated to non-Windows) | `aa0bc33` |
| ✅ | UTC-aware timestamps + auto-search baseline sync (carryover) | `b889f3e` |
| ✅ | Canonical auto-apply plan doc (post paircode round 2) | `22b22f3` → `docs/auto-apply-plan.md` |

## Slice 1 — Local semantic matcher ✅ shipped 2026-05-26 (PR #3, `e4f3f61`)

Observation-only — no apply capability ships in this slice.
Diary: `docs/diary/2026-05-26-slice-1-matcher-and-ui-fixes.md`.

| | Work | Files |
|---|---|---|
| ✅ | `sentence-transformers` + transitive (torch, transformers, scikit-learn) added | `requirements.txt`, `requirements-lock.txt` |
| ✅ | `JobEmbedding` table (composite PK on `job_id` + `embedding_model`); vectors stored as numpy bytes via `np.save` into `BytesIO` | `database/models.py` |
| ✅ | New columns on `Job`: `apply_status`, `match_score`, `match_score_percentile`, `match_computed_at` | `database/models.py` |
| ✅ | New columns on `UserProfile`: `auto_match_enabled`, `match_percentile_threshold` | `database/models.py` |
| ✅ | Idempotent SQLite migration entries for all six columns | `app/main.py:148` |
| ✅ | JD parser: requirements bullets, years-required, title family, must-have skills — pure regex, no NLP deps | `services/jd_parser.py` |
| ✅ | Embedding matcher: lazy-loaded `all-MiniLM-L6-v2`, hard filters → chunked per-requirement cosine → keyword overlap → composite, percentile gate | `services/embed_matcher.py` |
| ✅ | `POST /api/match/run` (operator-triggered; scheduler is slice 3) and `GET /api/match/candidates` | `app/main.py:1080` |
| ✅ | Bug fix: matcher wrote `match_reasons` as a dict, crashed JobTable. Now writes `list[str]` of human-readable bullets; JobTable defensively `Array.isArray`-guards | `app/main.py`, `dashboard-ui/src/features/jobs/JobTable.tsx` |

**Smoke test on existing 101 jobs** (recorded in pre-revert commit `160e7d7`):
score distribution mean=0.38, p50=0.40, p90=0.58, max=0.75; 11/101 pass the
90th-percentile gate. Top hits skew correctly toward Fullstack/React/Node;
bottom skews to MBSE/Staff Engineer.

**Known limitation:** scraped descriptions are ~500 chars (snippet-level, not
full JD). Match quality should improve once the scraper captures full
descriptions.

## UI consistency fixes ✅ shipped 2026-05-26 (PR #3, `e4f3f61`)

Audit found six inconsistencies during active scrape; all fixed. Pair-review
artifact: `.paircode/focus-03-ui-inconsistency-during-scrape/`.

| | Severity | Fix | Files |
|---|---|---|---|
| ✅ | 🔴 | SessionScreen rendered `started_at.slice(11,19)` (raw UTC) → now `toLocaleTimeString`; derives `paused`, branches dot color | `dashboard-ui/src/screens/SessionScreen.tsx` |
| ✅ | 🟠 | Frontend `Job` type missing slice-1 fields → added; `effectiveMatchScore()` helper prefers `match_score` over legacy `resume_match_score` | `dashboard-ui/src/lib/types.ts`, `dashboard-ui/src/lib/utils.ts` |
| ✅ | 🟠 | Polling cadence drift (session=2s, jobs=5s, stats=10s) → unified via `LIVE_POLL_MS=2000` in shared module | `dashboard-ui/src/lib/poll.ts` (new), `dashboard-ui/src/hooks/useJobs.ts`, `useSetup.ts` |
| ✅ | 🟠 | `useLogStream` kept prior session's lines → added `resetKey` param keyed on `started_at`; SessionScreen passes it | `dashboard-ui/src/hooks/useSession.ts`, `SessionScreen.tsx` |
| ✅ | 🟡 | Dashboard CTA stayed "Start Session" during active runs → flips to "View Live Session" via `useSessionStatus` | `dashboard-ui/src/screens/DashboardScreen.tsx` |
| ✅ | 🟢 | `JobFilters` status options stale (missing `tailoring_resume`, `recruiter_screen`, etc.) → generated from `PIPELINE_STAGES` | `dashboard-ui/src/features/jobs/JobFilters.tsx` |
| ✅ | — | `JobTable`, `PipelineScreen`, `JobDetailDrawer` all migrated from `resume_match_score` direct read to `effectiveMatchScore()` helper | three files |
| ✅ | — | Gitignore: bare `lib/` rule silently untracked `dashboard-ui/src/lib/` and broke fresh clones. Anchored to `/lib/`; added 9 previously-ignored lib files | `.gitignore`, `dashboard-ui/src/lib/*` |
| ✅ | — | ReviewQueueScreen stale "updates every 5s" copy fixed to "live updates" (now LIVE_POLL_MS=2s) | `dashboard-ui/src/screens/ReviewQueueScreen.tsx` |

Verified live in browser via Playwright walkthrough. TypeScript clean.

---

## Up next (planned — `docs/auto-apply-plan.md`)

### Slice 2 — Apply Queue UI 🟡 in tree, uncommitted

Operator review surface: card-based list of jobs the matcher gated as
`eligible`. Approve flips `apply_status='approved'` (slice 3 apply loop
will pick up). Skip flips `apply_status='skipped_by_operator'` (sticky —
matcher won't re-promote on rerun, verified end-to-end via Playwright).

| | Work | Files |
|---|---|---|
| 🟡 | `GET /api/apply/queue`, `POST /api/apply/approve/{job_id}`, `POST /api/apply/skip/{job_id}` | `app/main.py` |
| 🟡 | Matcher now respects operator/runtime terminal states (`approved`, `applied`, `applying`, `skipped_*`, `failed_*`) — only mutates `apply_status` from `eligible`/`not_eligible`/null | `app/main.py` |
| 🟡 | `useApplyQueue()` + `useApproveJob()` + `useSkipJob()` hooks; api client extensions | `dashboard-ui/src/hooks/useApplyQueue.ts` (new), `dashboard-ui/src/lib/api.ts` |
| 🟡 | `ApplyQueueScreen` with card layout: match%, percentile, matched skills (green) / missing skills (struck-through), score breakdown, description preview, Approve/Skip buttons | `dashboard-ui/src/screens/ApplyQueueScreen.tsx` (new) |
| 🟡 | Sidebar entry between Review Queue and Pipeline; `/apply-queue` route | `dashboard-ui/src/components/Sidebar.tsx`, `dashboard-ui/src/App.tsx` |

**End-to-end verified via Playwright:** 12 cards rendered, clicked Approve
on one → queue dropped to 11, DB shows `apply_status='approved'`. Clicked
Skip on another → queue dropped to 10, DB shows `skipped_by_operator`.
Re-ran matcher with `force=true` — both terminal states preserved
(stickiness works).

### Slice 3 — APScheduler loops + state machine + circuit breaker 🟡 in tree, uncommitted

Full dry-run plumbing. The bot picks up `approved` jobs every 5 min,
opens the URL via Playwright, dwells, screenshots, runs the breaker
against live LinkedIn responses, writes `ApplicationRun` rows. **Never
clicks Apply** — slice 4 ships the first real submits.

| | Work | Files |
|---|---|---|
| 🟡 | `ApplicationRun` table (full state machine, screenshot paths, dedup_key, form_log slot for slice 4) | `database/models.py` |
| 🟡 | `UserProfile` apply-loop columns: `auto_apply_enabled` (default false — dry-run kill switch), `daily_apply_cap`, `quiet_hours_start/end`, `last_apply_at`, `circuit_tripped*`, `apply_browser_mode` | `database/models.py` |
| 🟡 | `services/pacing.py` — `should_apply_now()`: circuit / toggle / quiet hours / daily cap / lognormal gap | `services/pacing.py` (new) |
| 🟡 | `services/circuit_breaker.py` — 8 LinkedIn tripwires (999, repeated 429, voyager 403, /checkpoint/, li_at expiry, /login redirect, body signals, captcha hosts) + consecutive-failure trip + auth-wall helper | `services/circuit_breaker.py` (new) |
| 🟡 | `services/browser_acquirer.py` — `attached_chrome` / `chromium_persistent` / `chromium_ephemeral`; stealth NOT applied under attached_chrome per paircode r2 | `services/browser_acquirer.py` (new) |
| 🟡 | `services/apply_runner.py` — dry-run orchestrator: acquire → navigate → dwell (lognormal 33s mean) → screenshot → state write. Never clicks submit. Honors more-specific pre-set state on `CircuitTripped` | `services/apply_runner.py` (new) |
| 🟡 | `_match_loop` (every 10 min) + `_apply_loop` (every 5 min, pacing-gated) wired into `startup_event`, mirror `_auto_search_loop` pattern | `app/main.py` |
| 🟡 | New endpoints: `GET /api/apply/runs`, `GET /api/apply/runs/{id}/screenshot/{n}`, `POST /api/apply/circuit/reset`, `GET /api/apply/circuit/status` | `app/main.py` |

**End-to-end verified live against real LinkedIn:** dry-run fired against an
`approved` job, browser launched in ephemeral mode, navigated to the JD
URL, hit LinkedIn's auth wall (expected without a session), correctly
identified `auth_wall_no_session` and exited cleanly without burning the
breaker. Screenshot saved (`data/apply_runs/2/01_opened.png`), API
served PNG correctly (1366×768). Dedup key computed
(`9ba8a2f3c7cef2df|marketsmart|fullstack software engineer...|united states remote`).

Two bugs surfaced and fixed mid-verification:
1. `captcha_iframe_present` was too greedy — matched LinkedIn pages that
   merely contained the word "captcha" + iframes. Tightened to require
   actual captcha provider hosts (arkoselabs / funcaptcha / hcaptcha /
   google recaptcha).
2. `CircuitTripped` exception handler overwrote more-specific terminal
   states (`blocked_captcha` → `blocked_auth`). Now only sets the
   default when the state is still `opened`.

**Apply Runs UI (slice 3.5, in tree):**
- `ApplicationRun` / `CircuitStatus` types + `applyRunStateColor()` helper
- `useApplyRuns()`, `useCircuitStatus()`, `useResetCircuit()` hooks + api client extensions
- `ApplyRunsScreen` — table with state badges, click-to-expand detail panel showing run metadata + inline screenshots, circuit-tripped banner with Reset button at the top when active
- Sidebar entry "Apply Runs" between Apply Queue and Pipeline

Verified live: 3 rows rendered with correct state colors (blue
`submitted_dry_run`, orange `blocked_auth`), expanded detail shows
metadata + inline screenshots, screenshot serving works via
`GET /api/apply/runs/{id}/screenshot/{n}`.

**Open follow-ups surfaced during slice-3 verification:**
- 🐛 LinkedIn "Page not found" (job removed since scrape) classified as
  `submitted_dry_run`. Apply runner has no 404 detection. Slice 4's
  per-ATS adapters will close this (no Apply button = job dead → mark
  `failed_terminal` / `skipped_unavailable`).
- 🐛 Ephemeral mode always hits the auth wall on LinkedIn (no `li_at`).
  Expected; clean signal. Real visibility lands with `attached_chrome`
  mode in slice 5.
- Cosmetic: a "Re-promote" action would let the operator turn
  `dry_run_complete` back into `approved` to re-test. Defer to slice 4.

### Polish (deferred — do before slice 4 ships)

Small wins that pay off once real submits land. Bundled as ~2-3 hours of
work, low risk, no architecture change.

- **Settings tab in dashboard** — toggle `auto_apply_enabled` / daily
  cap / quiet hours / browser mode + browser-mode wizard (CDP attach
  instructions for slice 5). Without this the only way to flip the
  kill switch is `venv/bin/python` against the DB, which is hostile
  the moment something goes wrong at midnight.
- **404 detection in `services/apply_runner.py`** — LinkedIn returns a
  "Page not found" template for removed jobs; current runner classifies
  it as `submitted_dry_run`. Add an early check (page title / canonical
  URL match) and set state `failed_unavailable` instead. ~30 min.
- **Re-promote action** — UI button / endpoint that turns
  `dry_run_complete` back into `approved` for re-testing without DB
  poking. ~15 min.

### Slice 4 — Greenhouse adapter 🟡 in tree, uncommitted

ATS framework + Greenhouse implementation. Framework lifted from
paircode peer fan-out (4 peers, one ATS each, single PR integration).

| | Work | Files |
|---|---|---|
| 🟡 | `ATSAdapter` ABC + `ApplyResult`/`ApplyStatus`/`FormField`/`ATSKind` enums + `detect_ats(url, page)` + `@register_adapter` registry | `services/ats/base.py`, `services/ats/__init__.py` |
| 🟡 | `field_map.yaml` heuristic regex → profile-key map (operator-editable) | `services/ats/field_map.yaml` |
| 🟡 | `services/dedup.py` — cross-source identity hash (normalized company + title + location), 90-day window, blocking-state filter | `services/dedup.py` |
| 🟡 | `services/ats/llm_fallback.py` — cached free-text Q&A via Groq → OpenAI fallback; uses existing analysis_cache table | `services/ats/llm_fallback.py` |
| 🟡 | `services/ats/greenhouse.py` — peer-a-codex deliverable. URL patterns, recognize(), cover-letter detection (SKIPPED_REQUIRES_COVER_LETTER), submit + confirmation polling | `services/ats/greenhouse.py` |
| 🟡 | `apply_runner.py` — dedup pre-check, detect_ats() dispatch, adapter outcome mirroring to Job.apply_status, form_log persistence | `services/apply_runner.py` |

**Verified end-to-end:** Runner against synthetic Greenhouse URL produced
`state=submitted_dry_run, ats=greenhouse, 3 screenshots, 2 form_log entries`.

### Slice 5 — LinkedIn Easy Apply + attached_chrome + pacing 🟡 in tree, uncommitted

| | Work | Files |
|---|---|---|
| 🟡 | `services/ats/easyapply.py` — peer-b-gemini deliverable. Multi-step modal walk (up to 8 steps), auth-wall preflight, captcha-in-modal sniff, save-and-submit-later detection (NEEDS_USER_INPUT), lognormal-typed keystrokes, hover-before-click, modal-signature mutation polling, resume-radio filename matching | `services/ats/easyapply.py` |
| 🟡 | `services/browser_acquirer.py` — attached_chrome mode hardened. Connection failure surfaces operator-actionable error (Chrome 136+ debug-profile constraint with exact command). Empty-context guard | `services/browser_acquirer.py` |
| 🟡 | `services/pacing.py` — weekend cap multiplier (0.4×). `_effective_daily_cap()` adjusts per local weekday. Lognormal gap, quiet hours, circuit/toggle gates all in place from slice 3 | `services/pacing.py` |

### Slice 6 — Workday / Lever / Ashby + universal fallback 🟡 in tree, uncommitted

| | Work | Files |
|---|---|---|
| 🟡 | `services/ats/workday.py` — peer-c-codex deliverable. data-automation-id selectors, multi-page wizard walk (8 page cap), EEO opt-out (Prefer-not-to-say), no account creation per paircode r2, file uploads via hidden input | `services/ats/workday.py` |
| 🟡 | `services/ats/lever.py` — peer-d-gemini deliverable. Single-page form walk, custom-question logging, /thanks confirmation detection | `services/ats/lever.py` |
| 🟡 | `services/ats/ashby.py` — peer-d-gemini deliverable. React-rendered form, aria-label-anchored selectors, role=combobox custom-dropdown handling | `services/ats/ashby.py` |
| 🟡 | `services/ats/universal_fallback.py` — `UniversalAdapter` scaffold for browser-use opt-in. Currently returns NEEDS_USER_INPUT — full browser-use wiring ships after operator validates the 5 hardcoded adapters | `services/ats/universal_fallback.py` |

**Verified registry**: all 5 hardcoded adapters register and dispatch
correctly on synthetic URLs (boards.greenhouse.io / linkedin.com/jobs/view /
myworkdayjobs.com / jobs.lever.co / jobs.ashbyhq.com) and via DOM
recognize() probes.

**Open follow-ups from peer reports:**
- 🐛 `peer-d`: Lever EEO section lives in `#eeo-frame` iframe — walker
  doesn't descend, required-EEO postings will skip
- 🐛 `peer-d`: Ashby progressive-disclosure "Add work experience" sections
  not expanded; common case is they're optional
- 🐛 `peer-b`: `_MAX_STEPS=8` is a safety net; 9+-step Easy Apply variants
  return NEEDS_USER_INPUT instead of proceeding
- 🐛 `peer-b`: resume-radio defaults to "first option" when filename match
  fails — could submit stale resume when operator has multiple
- ⚠ `peer-c`: Workday account-creation bypass returns NEEDS_USER_INPUT;
  no auto-signin (deferred to slice 6 even with creds)
- ⚠ `UserProfile` missing fields the adapters need: `phone`, `linkedin_url`,
  `years_experience`, `current_company`, `city`, `country`,
  `work_authorized`, `needs_sponsorship`. Currently `getattr` defaults
  to None → adapter logs `source=skipped`. Add Settings UI for these
  before flipping any adapter to non-dry-run.
- ⚠ No real LLM call from `llm_fallback` yet — slice 4's adapters
  intentionally heuristic-only during initial calibration. Wire in slice
  4.5 once the operator has reviewed enough dry-run form_log entries to
  trust the cache.
- ⚠ `UniversalAdapter` (browser-use) is scaffold only — slice 6 ships
  the actual LLM-driven flow after hardcoded adapters are validated
`ats/base.py` + `ats/greenhouse.py` + `field_map.yaml` + `llm_fallback.py`
+ `dedup.py`. Behavioral-noise session-state realism layer. Real submits
behind `auto_apply_enabled=true`. Lower ToS risk than LinkedIn — ships
before slice 5 on purpose. ~3-4 days.

### Slice 5 — LinkedIn Easy Apply + pacing engine ⬜
Lognormal-spread scheduler, quiet hours, weekday/weekend jitter, hard cap
15/day, human warmup. Attached-Chrome mode default; dedicated debug
profile setup wizard. JA4 sanity check on fallback modes. ~4 days.

### Slice 6 — Workday / Lever / Ashby + browser-use fallback ⬜
Coverage expansion. Optional cover-letter generation. Later.

**ETA to first real apply (slice 4): ~9 days. First LinkedIn apply (slice
5): ~13 days.**

---

## Decisions on record

- **LinkedIn ToS:** automated submission may result in account
  restriction; operator accepted the risk before slice 1.
- **Cover letters v1:** jobs that require one are skipped
  (`skipped_requires_cover_letter`). LLM-generated cover letters come
  post-MVP.
- **Two-account model:** burner for scraping, real account for applying;
  separate `user_data_dir` per account, never run concurrently.
- **`auto_apply_enabled` defaults to false** — first run cannot submit by
  accident.
- **Branch name:** `feat/dagster-auto-apply` retained for continuity; the
  build uses APScheduler in-process, not Dagster.

---

_Last updated: 2026-05-26._
