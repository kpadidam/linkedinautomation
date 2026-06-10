"""Dry-run apply orchestrator (slice 3).

One call site: ``run_dry_apply(job, profile, db)``. Acquires a browser,
navigates to ``job.url``, dwells, screenshots, and writes an
``ApplicationRun`` row. Never clicks Apply, never fills a form — that's
slice 4-5.

Why we do this at all in slice 3: it lets us exercise the full pipeline
(pacing → browser acquisition → circuit breaker against real LinkedIn
responses → screenshot capture → state transitions → DB writes) against
production traffic before slice 4 risks a real submit. If the breaker
catches a /checkpoint/ redirect during dry navigation, we know it'll
catch it during a real run too.

State machine for slice 3:
  opened             → terminal: submitted_dry_run     (happy path)
  opened             → terminal: blocked_captcha       (DOM captcha)
  opened             → terminal: blocked_auth          (breaker trip)
  opened             → terminal: failed_retryable      (timeout / network)
  opened             → terminal: failed_terminal       (3 consecutive)
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import random
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from database.models import ApplicationRun, Job
from services.browser_acquirer import acquire
from services.circuit_breaker import (
    CircuitBreaker,
    CircuitObservation,
    CircuitTripped,
    auth_wall_present,
    captcha_iframe_present,
    job_unavailable_present,
)

logger = logging.getLogger(__name__)


# Where screenshots land. Symlink target is data/apply_runs/{run_id}/<n>.png.
# The progress doc mentions data/ as gitignored; this directory inherits
# that. Operator can purge old runs whenever.
SCREENSHOT_ROOT = Path("data") / "apply_runs"


# Lognormal dwell on the JD page. We mostly want the apply runner to look
# like "person opened a job, read it for a beat, moved on" — not a
# clockwork 0-second fetch.
_DWELL_MU = 3.5      # log seconds
_DWELL_SIGMA = 0.4
_DWELL_MIN = 20.0
_DWELL_MAX = 120.0


def _sample_dwell_seconds(rng: random.Random | None = None) -> float:
    rng = rng or random.Random()
    s = rng.lognormvariate(_DWELL_MU, _DWELL_SIGMA)
    return max(_DWELL_MIN, min(_DWELL_MAX, s))


def _dedup_key(job: Job) -> str:
    """Stable identity for a role across ATS sources.

    ``normalize(company) + normalize(title) + normalize(location)``.
    Slice 4 will check this before submit so we don't double-apply via
    LinkedIn Easy Apply + a direct Greenhouse link. Slice 3 just
    populates the column.
    """

    def norm(s: Optional[str]) -> str:
        if not s:
            return ""
        return re.sub(r"\s+", " ", re.sub(r"[^\w]+", " ", s)).strip().lower()

    raw = "|".join([norm(job.company), norm(job.title), norm(job.location)])
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16] + "|" + raw[:120]


async def run_dry_apply(job: Job, profile, db: Session) -> ApplicationRun:
    """Open the job URL, dwell, screenshot, write an ApplicationRun.

    Returns the persisted row. Doesn't raise — failures land as
    ``failed_*`` or ``blocked_*`` rows. The apply loop swallows the
    return value and just trusts the row.
    """

    run = ApplicationRun(
        job_id=job.job_id,
        ats="unknown",   # slice 4 sets this when adapters detect the ATS
        state="opened",
        started_at=datetime.utcnow(),
        dedup_key=_dedup_key(job),
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    run_dir = SCREENSHOT_ROOT / str(run.id)
    run_dir.mkdir(parents=True, exist_ok=True)
    screenshots: list[str] = []
    breaker = CircuitBreaker(profile, db)

    mode = (profile.apply_browser_mode or "chromium_ephemeral").strip()
    acquired = None
    try:
        if not job.url:
            run.state = "failed_terminal"
            run.exit_reason = "no_url"
            run.ended_at = datetime.utcnow()
            db.commit()
            breaker.record_consecutive_failure()
            return run

        acquired = await acquire(mode, headless=True)
        page = acquired.page

        # --- response listener: every wire-level response feeds the breaker
        def on_response(resp):
            try:
                obs = CircuitObservation(
                    url=resp.url,
                    status=resp.status,
                    body_snippet="",  # body fetch is async; we sniff after nav
                    was_authenticated=False,  # ephemeral browser has no li_at
                )
                breaker.observe(obs)
            except CircuitTripped:
                # The exception propagates through the asyncio loop; raise
                # below in the explicit await chain. Swallowing here just
                # avoids noisy Playwright callback errors.
                pass

        page.on("response", on_response)

        # --- navigate ---
        await page.goto(job.url, wait_until="domcontentloaded", timeout=30000)

        # Catch a tripwire that happened during the goto (the listener may
        # have flipped the breaker state without us seeing the exception).
        if breaker.is_tripped:
            raise CircuitTripped(
                profile.circuit_tripped_reason or "tripped_during_nav"
            )

        # Initial screenshot (just-after-load).
        opened_png = run_dir / "01_opened.png"
        await page.screenshot(path=str(opened_png), full_page=False)
        screenshots.append(str(opened_png))

        # --- dwell ---
        dwell = _sample_dwell_seconds()
        logger.info(f"[apply_runner] dwelling {dwell:.1f}s on {job.url}")
        await asyncio.sleep(dwell)

        # --- DOM-level checks: captcha first, then auth-wall ---
        html = await page.content()
        current_url = page.url

        if captcha_iframe_present(html):
            run.state = "blocked_captcha"
            run.exit_reason = "captcha_iframe"
            run.ended_at = datetime.utcnow()
            run.screenshot_paths = screenshots
            db.commit()
            breaker.trip("captcha_iframe")  # raises
            return run  # unreachable; for type-check

        # Removed-job page (LinkedIn 404). Mark unavailable, mark the job
        # itself so it drops out of the apply queue, and exit cleanly. Not
        # a security event — don't touch the breaker.
        page_title = await page.title()
        if job_unavailable_present(html, page_title):
            run.state = "failed_unavailable"
            run.exit_reason = "job_removed_404"
            run.ended_at = datetime.utcnow()
            run.screenshot_paths = screenshots
            job.apply_status = "failed_unavailable"
            profile.last_apply_at = datetime.utcnow()
            db.commit()
            logger.info(
                f"[apply_runner] job {job.job_id} no longer available (404)"
            )
            return run

        # Auth wall on an ephemeral browser is normal (no li_at). Don't trip
        # the breaker — just record it and exit cleanly. Slice 5 ships
        # attached-Chrome mode which carries a real session.
        if auth_wall_present(html, current_url):
            run.state = "blocked_auth"
            run.exit_reason = "auth_wall_no_session"
            run.ended_at = datetime.utcnow()
            run.screenshot_paths = screenshots
            profile.last_apply_at = datetime.utcnow()
            db.commit()
            logger.info(
                f"[apply_runner] auth wall for {job.job_id} "
                f"(expected in {mode} mode without a session)"
            )
            return run

        # Full-page screenshot after dwell.
        rendered_png = run_dir / "02_rendered.png"
        await page.screenshot(path=str(rendered_png), full_page=True)
        screenshots.append(str(rendered_png))

        # --- Cross-source dedup check before handing off to any adapter.
        # Same role across LinkedIn + Greenhouse direct = double-apply.
        from services.dedup import is_duplicate
        is_dup, prior = is_duplicate(db, job.company, job.title, job.location)
        if is_dup:
            run.state = "skipped_duplicate"
            run.exit_reason = (
                f"dup_of_run_{prior.id}" if prior else "dup_of_prior_run"
            )
            run.ended_at = datetime.utcnow()
            run.screenshot_paths = screenshots
            db.commit()
            logger.info(
                f"[apply_runner] dedup skip for {job.job_id}: matches prior run {prior.id if prior else '?'}"
            )
            return run

        # --- Detect ATS and dispatch to the right adapter.
        from services.ats import detect_ats, ApplyStatus
        ats_kind, adapter_cls = await detect_ats(job.url or "", page)
        run.ats = ats_kind.value
        db.commit()

        if adapter_cls is None:
            # Unknown ATS. Slice 6 will fall through to browser-use here
            # if the operator opted in; for slice 4 we surface as a
            # dry-run completion that the operator can review.
            run.state = "submitted_dry_run"
            run.exit_reason = "unknown_ats"
            run.ended_at = datetime.utcnow()
            run.screenshot_paths = screenshots
            job.apply_status = "dry_run_complete"
            profile.last_apply_at = datetime.utcnow()
            db.commit()
            breaker.record_success()
            logger.info(
                f"[apply_runner] unknown ATS for {job.job_id} — recorded as dry-run"
            )
            return run

        adapter = adapter_cls()
        # Operator's auto_apply_enabled toggle gates real submission.
        # When False: adapter parses + screenshots + parks at Submit
        # without clicking (audit-only). When True: adapter is allowed
        # to actually click Submit. Default-False on a fresh DB; the
        # operator must explicitly enable it from Settings.
        adapter_dry_run = not bool(getattr(profile, "auto_apply_enabled", False))
        try:
            result = await adapter.apply(
                page=page,
                job=job,
                profile=profile,
                dry_run=adapter_dry_run,
            )
        except Exception as e:  # noqa: BLE001
            run.state = "failed_retryable"
            run.exit_reason = f"adapter_{ats_kind.value}_raised"
            run.error_message = str(e)[:1000]
            run.ended_at = datetime.utcnow()
            run.screenshot_paths = screenshots
            db.commit()
            breaker.record_consecutive_failure()
            logger.exception(
                f"[apply_runner] {ats_kind.value} adapter raised for {job.job_id}"
            )
            return run

        # Lift adapter screenshots into the run dir + persist form_log.
        for shot in result.screenshots or []:
            # Adapters return relative names; resolve against run_dir or
            # accept absolute paths verbatim.
            if not shot:
                continue
            if shot.startswith("/") or shot.startswith(str(run_dir)):
                screenshots.append(shot)
            else:
                screenshots.append(str(run_dir / shot))
        if result.fields_logged:
            run.form_log = [
                {
                    "label": f.label,
                    "value": f.value,
                    "source": f.source,
                    "confidence": f.confidence,
                    "selector": f.selector,
                }
                for f in result.fields_logged
            ]

        run.state = result.status.value
        run.exit_reason = result.exit_reason or result.status.value
        run.error_message = result.error_message
        run.ended_at = datetime.utcnow()
        run.screenshot_paths = screenshots
        profile.last_apply_at = datetime.utcnow()

        # Mirror adapter outcome into Job.apply_status so the apply queue
        # query stops surfacing this job.
        if result.status in (
            ApplyStatus.SUBMITTED,
            ApplyStatus.SUBMITTED_DRY_RUN,
        ):
            job.apply_status = (
                "applied"
                if result.status == ApplyStatus.SUBMITTED
                else "dry_run_complete"
            )
            if result.status == ApplyStatus.SUBMITTED:
                job.applied = True
                job.applied_date = datetime.utcnow()
        elif result.status == ApplyStatus.SKIPPED_DUPLICATE:
            job.apply_status = "skipped_duplicate"
        elif result.status == ApplyStatus.SKIPPED_REQUIRES_COVER_LETTER:
            job.apply_status = "skipped_requires_cover_letter"
        elif result.status == ApplyStatus.FAILED_UNAVAILABLE:
            job.apply_status = "failed_unavailable"
        # Other outcomes (NEEDS_USER_INPUT / BLOCKED_* / FAILED_*) leave
        # apply_status alone — operator decides what to do next.

        db.commit()
        if result.status in (ApplyStatus.SUBMITTED, ApplyStatus.SUBMITTED_DRY_RUN):
            breaker.record_success()
        elif result.status in (
            ApplyStatus.FAILED_RETRYABLE,
            ApplyStatus.FAILED_TERMINAL,
        ):
            breaker.record_consecutive_failure()
        logger.info(
            f"[apply_runner] {ats_kind.value} -> {result.status.value} "
            f"({result.exit_reason}) for {job.job_id}"
        )
        return run

    except CircuitTripped as e:
        # Honor a pre-set, more-specific state (e.g. blocked_captcha was
        # already written before we called breaker.trip()). Only default
        # to blocked_auth when nothing else claimed the state.
        if run.state == "opened":
            run.state = "blocked_auth"
        run.exit_reason = e.reason[:200]
        run.ended_at = datetime.utcnow()
        run.screenshot_paths = screenshots
        db.commit()
        logger.error(f"[apply_runner] breaker tripped for {job.job_id}: {e.reason}")
        return run

    except asyncio.TimeoutError as e:
        run.state = "failed_retryable"
        run.exit_reason = "timeout"
        run.error_message = str(e)
        run.ended_at = datetime.utcnow()
        run.screenshot_paths = screenshots
        db.commit()
        breaker.record_consecutive_failure()
        return run

    except Exception as e:  # noqa: BLE001
        run.state = "failed_retryable"
        run.exit_reason = type(e).__name__
        run.error_message = str(e)[:1000]
        run.ended_at = datetime.utcnow()
        run.screenshot_paths = screenshots
        db.commit()
        breaker.record_consecutive_failure()
        logger.exception(f"[apply_runner] error on {job.job_id}")
        return run

    finally:
        if acquired is not None:
            try:
                await acquired.cleanup()
            except Exception:  # noqa: BLE001
                logger.warning("[apply_runner] cleanup raised", exc_info=True)
