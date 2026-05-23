# Auto-Apply — canonical plan

Validated through two paircode rounds. This document is the source of truth; the
`.paircode/focus-02-linkedin-auto-apply-arch/` directory contains the underlying
peer critiques and consensus files.

> Branch is still named `feat/dagster-auto-apply` from the original plan. The
> name is left as-is for continuity; the implementation does **not** use Dagster.

## Decisions on record

### LinkedIn ToS — accepted risk

LinkedIn's User Agreement prohibits automated submission of applications. Using
this tool may result in account restriction or termination of the apply account.
The operator has acknowledged this risk and chooses to proceed.

Mitigations baked into the design (see "Anti-bot layer" below) lower the
probability but do not eliminate it.

### Cover letter strategy — skip for v1

Off-site ATS forms that **require** a cover letter are skipped in v1. They are
marked `skipped_requires_cover_letter` and surfaced in the review queue. Post-MVP
work will add LLM-generated cached cover letters as an opt-in.

Rationale: ~30% loss in off-site coverage is acceptable for v1; cover-letter
generation adds an LLM dependency, cost surface, and quality risk that would
delay shipping the core loop.

## Mental model

```
CRON A (already exists)             CRON B (new)
_auto_search_loop  ──►  Job  ──►  _match_loop  ──►  Job.match_score
   every N min          (status=new)    every M min
                                                          │
                                                          ▼
                                       _apply_loop  ──►  ApplicationRun
                                       every K min,
                                       gated by pacing.py
                                                          │
                                                          ▼
                                                  Job.apply_status=applied
                                                  + screenshot proof
```

No Dagster. No subprocess per asset. Three async loops inside FastAPI,
mirroring the existing `_auto_search_loop` pattern at `app/main.py:190`.

## Two-account model

Operator runs:

- **Scrape account** — burner; powers `_auto_search_loop`. If restricted, swap
  the burner; pipeline keeps running.
- **Apply account** — real account; powers `_apply_loop`. The account that
  carries the actual ban risk.

Implementation: two `linkedin_account` rows in Settings, each with its own
`user_data_dir`. Adapters take credentials per-call. Never run scrape and apply
concurrently or back-to-back (per peer-a-codex round 2).

## Anti-bot layer (post round-2)

### Browser acquisition modes

```
apply_browser_mode:
  attached_chrome      # default — CDP attach to a dedicated debug Chrome
  chromium_persistent  # fallback — Playwright launch + persistent user-data-dir
  chromium_ephemeral   # testing only — fresh launch, no profile
```

**Attached-Chrome mode caveat (Chrome 136+):** since March 2025 Chrome rejects
`--remote-debugging-port` against the default user profile. The operator must
maintain a separate dedicated debug profile. Settings UI surfaces a setup
wizard with the exact `chrome --remote-debugging-port=9222 --user-data-dir=...`
command and clearly labels this as "separate from your daily Chrome."

**`playwright-stealth` is suppressed under `attached_chrome` mode.** Stealth
patches on top of real Chrome create inconsistencies. Stealth applies only to
the chromium fallback modes.

### Behavioral noise — priority order

1. **Session-state realism (highest value)**
   - `visibilitychange` and focus/blur events on the page
   - JD-page dwell time before clicking Easy Apply (lognormal, μ≈45s)
   - Jobs-viewed-before-apply count (≥2-3 with brief read of each)
   - Occasional abandoned applies (open modal, scroll, close)
   - Hover before click — real `mousemove` to button, brief pause, then click
2. **Typing realism**
   - `page.keyboard.type(text, delay=lognormal(80, 30))` — never `input.fill()`
     for text fields
3. **Mouse movement (lowest value)**
   - Straight-line `mousemove` to target is fine. Bezier curves explicitly
     deferred — "fake-perfect bezier" is itself a tell.

### Fingerprint posture — consistency over noise

No canvas/WebGL randomization. A moving fingerprint on a single human account
is worse than a stable one. Tier-2 work is **consistency**: timezone, locale,
language, Accept-Language, screen dimensions, device-scale, WebGL
vendor/renderer all match the host hardware and stay stable across sessions.

Startup self-test: in fallback chromium modes, compare bundled-chromium JA4 to
real Chrome JA4 and warn if divergent.

### Circuit-breaker tripwires (LinkedIn-specific)

Slice 3 ships all eight:

1. HTTP `999`
2. Repeated `429`
3. `403` on authenticated Voyager endpoints
4. Redirect to any `/checkpoint/...` path
5. Missing or expired `li_at` cookie, or CSRF/JSESSIONID mismatch
6. Unauthenticated navigation to `/login`
7. Response body containing `checkpoint`, `challenge`, `security-verification`,
   or `unusual activity`
8. CAPTCHA iframe present, or Easy Apply modal replaced by auth/challenge
   content

Any tripwire → halt auto-apply, surface in UI, pacing engine pauses for ≥24h,
never auto-retry. Operator resets manually via `POST /api/apply/circuit/reset`.

## Matcher (replacing the broken `cosine@0.65` proposal)

```python
def score(jd: str, profile: dict, embedder) -> MatchResult:
    # 1. Hard filters — boolean, kill before any embedding work
    if not _title_family_ok(jd, profile.target_titles):  return reject("title_family")
    if not _years_ok(jd, profile.years_experience):      return reject("years")
    if not _location_ok(jd, profile.locations):          return reject("location")
    if not _work_auth_ok(jd, profile.work_auth):         return reject("work_auth")

    # 2. Extract requirements section (regex + heuristic)
    reqs = extract_requirements(jd)

    # 3. Per-requirement embedding match
    req_vecs = embedder.encode(reqs)
    profile_vecs = embedder.encode(profile.resume_bullets)
    per_req_scores = [max(cos(rv, pv) for pv in profile_vecs) for rv in req_vecs]
    semantic = mean(per_req_scores)

    # 4. Keyword overlap on must-haves
    must_haves = extract_must_haves(jd)
    keyword = len(must_haves & profile.skills) / max(len(must_haves), 1)

    # 5. Composite
    raw = 0.5 * semantic + 0.5 * keyword
    return MatchResult(raw_score=raw, reasons={...})

def gate(raw_score, recent_scores) -> bool:
    # Percentile gate — self-calibrates as corpus shifts
    return raw_score >= np.percentile(recent_scores[-200:], 90)
```

Model: `sentence-transformers/all-MiniLM-L6-v2` (~80MB, CPU). Percentile gate
default 90 (configurable in Settings). LLM upgrade later goes behind the same
`score()` interface — no caller change.

## State machine

**`Job.apply_status`** (new column on existing `jobs` table):

```
not_eligible       — below threshold or hard-filter rejected
eligible           — passes gating; waiting in queue
approved           — operator clicked Approve in Review Queue
applying           — in-flight (worker holds lock)
applied            — submitted successfully
failed_retryable   — DOM glitch / network — retried next loop
failed_terminal    — captcha/auth/3 consecutive fails — needs human
skipped_duplicate  — dedup hash matched a prior application
skipped_requires_cover_letter  — v1 punt
```

**`ApplicationRun.state`** (per-attempt detail, finer-grained):

```
discovered → opened → form_parsed → needs_user_input → ready_to_submit
                                  → submitted
                                  → blocked_captcha
                                  → blocked_auth
                                  → failed_retryable | failed_terminal
```

The full peer-a-codex 15-state model lives at the `ApplicationRun` level. Job
gets the simplified 9-state operator view.

## DB additions

```python
class JobEmbedding(Base):
    __tablename__ = "job_embeddings"
    job_id = Column(String, ForeignKey("jobs.job_id"), primary_key=True)
    embedding_model = Column(String, primary_key=True)   # "all-MiniLM-L6-v2"
    title_vec = Column(LargeBinary)
    requirements_vecs = Column(LargeBinary)              # list[vec] as bytes
    extracted_requirements = Column(JSON)                # explainability
    years_required = Column(Integer, nullable=True)
    title_family = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class ApplicationRun(Base):
    __tablename__ = "application_runs"
    id = Column(Integer, primary_key=True)
    job_id = Column(String, ForeignKey("jobs.job_id"), index=True)
    ats = Column(String)                                 # "easy_apply" | "greenhouse" | ...
    state = Column(String, index=True)
    started_at = Column(DateTime)
    ended_at = Column(DateTime, nullable=True)
    exit_reason = Column(String, nullable=True)
    screenshot_paths = Column(JSON)
    form_log = Column(JSON)                              # [{label, value, source}]
    error_message = Column(Text, nullable=True)
    dedup_key = Column(String, index=True)               # normalized company|title|location
```

Columns added to existing `Job` table:
- `apply_status` (String, default `not_eligible`)
- `match_score` (Float — raw composite)
- `match_score_percentile` (Float — gating signal)
- `match_reasons` (JSON — explainability)

Columns added to existing `UserProfile`:
- `auto_match_enabled` (Bool, default true)
- `auto_apply_enabled` (Bool, default **false** — dry-run kill switch)
- `match_percentile_threshold` (Int 1-99, default 90)
- `daily_apply_cap` (Int, default 15)
- `quiet_hours_start` / `quiet_hours_end` (Int, default 23/7)
- `last_apply_at` (DateTime)
- `circuit_tripped` (Bool) / `circuit_tripped_at` / `circuit_consecutive_failures`
- `apply_browser_mode` (Enum, default `attached_chrome`)
- `attached_chrome_port` (Int, default 9222)
- `chromium_profile_dir_scrape` (Path)
- `chromium_profile_dir_apply` (Path)
- `scrape_account_email` / `apply_account_email` (String — accounts split)

## New modules

```
services/
  embed_matcher.py     # SentenceTransformer load + score()
  jd_parser.py         # extract requirements, years, title family
  pacing.py            # "is NOW ok to apply?" — lognormal gap, quiet hours,
                       #   day-of-week, daily cap
  apply_runner.py      # orchestrates one application end-to-end
  circuit_breaker.py   # 8-tripwire list, halt + persist
  dedup.py             # normalize → hash → check pre-submit
  browser_acquirer.py  # three modes; suppress stealth under attached_chrome
  human_input.py       # typing/hover helpers + session-state realism
  ats/
    base.py            # ATSAdapter ABC: apply(page, job, profile) → ApplyResult
    easyapply.py
    greenhouse.py
    field_map.yaml     # heuristic regex → profile key (user-editable)
    llm_fallback.py    # cached LLM call for unknown free-text questions
```

## New API endpoints

```
GET   /api/apply/queue                # eligible jobs awaiting approval
POST  /api/apply/approve/{job_id}     # one-click approve
POST  /api/apply/reject/{job_id}      # operator skip
GET   /api/apply/runs                 # paginated history
GET   /api/apply/runs/{id}/screenshot/{n}
WS    /ws/apply/{run_id}              # live state + screenshot stream
POST  /api/apply/circuit/reset        # clear a tripped breaker
```

## Dashboard additions

One new sidebar entry: **Apply Queue**, three tabs:
- **Pending** — eligible jobs, score breakdown, Approve / Skip
- **Runs** — past attempts, state badge, screenshot peek
- **Settings** — percentile slider, quiet hours, daily cap, browser mode,
  circuit reset

Existing dashboard untouched.

## Slice sequence

| # | Slice | Days | Ships |
|---|---|---|---|
| 1 | Matcher + JD parser + `JobEmbedding` table + score columns on Job. No apply. | 2-3 | Daily "would have applied to these N jobs" report; one week of observation |
| 2 | Apply Queue UI (Pending tab) + approve/reject endpoints. Still no submit. | 1-2 | Operator can review and rubber-stamp matches |
| 3 | APScheduler `_match_loop` + `_apply_loop` + `ApplicationRun` + state machine + `pacing.py` + `circuit_breaker.py` (all 8 tripwires) + `browser_acquirer.py` (all three modes, stealth-suppressed under attached_chrome). `apply_runner` writes screenshots; still no real submit. | 3 | Full pipeline observable; safe |
| 4 | Greenhouse adapter (lower ToS risk, stable DOM): `ats/base.py` + `ats/greenhouse.py` + `field_map.yaml` + `llm_fallback.py` + `dedup.py`. Behavioral-noise session-state realism layer. Real submits behind `auto_apply_enabled=true`. | 3-4 | First real applies — Greenhouse only |
| 5 | LinkedIn Easy Apply adapter + pacing engine (lognormal spread, quiet hours, weekday/weekend jitter, hard cap 15/day, human warmup). Attached-Chrome mode becomes default; dedicated-profile setup wizard in Settings. JA4 sanity check on fallback modes. | 4 | Easy Apply automation |
| 6 | Workday / Lever / Ashby adapters. browser-use as universal fallback for unknown ATS. Optional: cover-letter generation. | later | Coverage expansion |

**First real apply (slice 4): ~9 days. First LinkedIn apply (slice 5): ~13 days.**

## Working agreements

- `auto_apply_enabled` defaults to **false**. Operator must flip it
  explicitly. No first run can submit by accident.
- Every submission writes: JD snapshot, resume snapshot, screenshots, form
  values sent. Append-only audit log.
- Circuit breaker tripped → halt for ≥24h, operator-only reset.
- Slice 1 ships *no* apply capability. We observe the matcher's output for a
  week before slice 2 even begins.
