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

## Slice 1 — Local semantic matcher (uncommitted)

Observation-only — no apply capability ships in this slice.

| | Work | Files |
|---|---|---|
| 🟡 | `sentence-transformers` + transitive (torch, transformers, scikit-learn) added | `requirements.txt`, `requirements-lock.txt` |
| 🟡 | `JobEmbedding` table (composite PK on `job_id` + `embedding_model`); vectors stored as numpy bytes via `np.save` into `BytesIO` | `database/models.py` |
| 🟡 | New columns on `Job`: `apply_status`, `match_score`, `match_score_percentile`, `match_computed_at` | `database/models.py` |
| 🟡 | New columns on `UserProfile`: `auto_match_enabled`, `match_percentile_threshold` | `database/models.py` |
| 🟡 | Idempotent SQLite migration entries for all six columns | `app/main.py:148` |
| 🟡 | JD parser: requirements bullets, years-required, title family, must-have skills — pure regex, no NLP deps | `services/jd_parser.py` (new) |
| 🟡 | Embedding matcher: lazy-loaded `all-MiniLM-L6-v2`, hard filters → chunked per-requirement cosine → keyword overlap → composite, percentile gate | `services/embed_matcher.py` (new) |
| 🟡 | `POST /api/match/run` (operator-triggered; scheduler is slice 3) and `GET /api/match/candidates` | `app/main.py:1080` |

**Smoke test on existing 101 jobs** (recorded in pre-revert commit `160e7d7`):
score distribution mean=0.38, p50=0.40, p90=0.58, max=0.75; 11/101 pass the
90th-percentile gate. Top hits skew correctly toward Fullstack/React/Node;
bottom skews to MBSE/Staff Engineer.

**Known limitation:** scraped descriptions are ~500 chars (snippet-level, not
full JD). Match quality should improve once the scraper captures full
descriptions.

## UI consistency fixes (uncommitted) — paircode focus-03

Audit found six inconsistencies during active scrape; all fixed. Pair-review
artifact: `.paircode/focus-03-ui-inconsistency-during-scrape/`.

| | Severity | Fix | Files |
|---|---|---|---|
| 🟡 | 🔴 | SessionScreen rendered `started_at.slice(11,19)` (raw UTC) → now `toLocaleTimeString`; derives `paused`, branches dot color | `dashboard-ui/src/screens/SessionScreen.tsx` |
| 🟡 | 🟠 | Frontend `Job` type missing slice-1 fields → added; `effectiveMatchScore()` helper prefers `match_score` over legacy `resume_match_score` | `dashboard-ui/src/lib/types.ts`, `dashboard-ui/src/lib/utils.ts` |
| 🟡 | 🟠 | Polling cadence drift (session=2s, jobs=5s, stats=10s) → unified via `LIVE_POLL_MS=2000` in shared module | `dashboard-ui/src/lib/poll.ts` (new), `dashboard-ui/src/hooks/useJobs.ts`, `useSetup.ts` |
| 🟡 | 🟠 | `useLogStream` kept prior session's lines → added `resetKey` param keyed on `started_at`; SessionScreen passes it | `dashboard-ui/src/hooks/useSession.ts`, `SessionScreen.tsx` |
| 🟡 | 🟡 | Dashboard CTA stayed "Start Session" during active runs → flips to "View Live Session" via `useSessionStatus` | `dashboard-ui/src/screens/DashboardScreen.tsx` |
| 🟡 | 🟢 | `JobFilters` status options stale (missing `tailoring_resume`, `recruiter_screen`, etc.) → generated from `PIPELINE_STAGES` | `dashboard-ui/src/features/jobs/JobFilters.tsx` |
| 🟡 | — | `JobTable`, `PipelineScreen`, `JobDetailDrawer` all migrated from `resume_match_score` direct read to `effectiveMatchScore()` helper | three files |

TypeScript compiles clean (`npx tsc --noEmit` returned no errors).

---

## Up next (planned — `docs/auto-apply-plan.md`)

### Slice 2 — Apply Queue UI ⬜
Operator review queue: Pending tab listing eligible scored jobs with
approve/reject. No submit logic. ~1-2 days.

### Slice 3 — APScheduler loops + state machine + circuit breaker ⬜
`_match_loop` + `_apply_loop` skeleton inside FastAPI. `ApplicationRun`
table, 15-state per-attempt state machine, `pacing.py`,
`circuit_breaker.py` with all 8 LinkedIn-specific tripwires from paircode
r2 (999, 429, /checkpoint/, li_at expiry, captcha frame, ...).
`browser_acquirer.py` with `attached_chrome` / `chromium_persistent` /
`chromium_ephemeral` modes. `apply_runner` writes screenshots; still no
real submit. ~2 days.

### Slice 4 — Greenhouse adapter (first real applies) ⬜
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
