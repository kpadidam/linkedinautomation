"""Cross-source application dedup.

A single role can appear via LinkedIn Easy Apply, the company's direct
Greenhouse posting, AND a job board scrape. Without dedup the bot would
happily apply three times and look like a script to the recruiter —
exactly the failure mode paircode r2 flagged.

The key is a normalized hash of company + title + location, computed
identically wherever it's used (matcher, apply_runner, here). Apply runs
write it to ``ApplicationRun.dedup_key`` at the start of every attempt;
this module checks for prior runs with the same key before submit.

Window: 90 days. A role re-posted after that is treated as a fresh
opportunity — sometimes companies legitimately re-post if no one bit.
"""

from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from database.models import ApplicationRun

logger = logging.getLogger(__name__)

DEDUP_WINDOW_DAYS = 90

# Adapter status values that count as a "real or intended" submit for
# dedup purposes. Failed runs DON'T burn a dedup slot — if we crashed
# mid-form, the operator should be able to retry the same job. Skipped
# runs likewise (operator-initiated skip vs duplicate skip — different
# semantics).
_BLOCKING_STATES = (
    "submitted",
    "submitted_dry_run",
    "applying",
    "ready_to_submit",
    "needs_user_input",
)


def _normalize(s: Optional[str]) -> str:
    """Collapse whitespace, strip punctuation, lowercase. Same function
    used by apply_runner._dedup_key — extracted here for reuse."""

    if not s:
        return ""
    cleaned = re.sub(r"[^\w]+", " ", s)
    return re.sub(r"\s+", " ", cleaned).strip().lower()


def compute_key(company: Optional[str], title: Optional[str], location: Optional[str]) -> str:
    """Build the dedup key used across the codebase.

    Format: ``{sha1_prefix}|{normalized_id}``. The sha1 prefix gives O(1)
    DB index lookups; the normalized suffix is for human debugging when
    you `SELECT * FROM application_runs WHERE dedup_key LIKE '...'`.
    """

    raw = "|".join([_normalize(company), _normalize(title), _normalize(location)])
    h = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]
    return f"{h}|{raw[:120]}"


def find_blocking_run(
    db: Session,
    dedup_key: str,
    now: Optional[datetime] = None,
) -> Optional[ApplicationRun]:
    """Return any prior ApplicationRun that should block re-submitting.

    "Blocking" means: same dedup_key, in a state we'd interpret as
    already-applied-or-in-flight, within the last DEDUP_WINDOW_DAYS.
    Returns ``None`` when it's safe to proceed.
    """

    if not dedup_key:
        return None
    now = now or datetime.utcnow()
    horizon = now - timedelta(days=DEDUP_WINDOW_DAYS)

    return (
        db.query(ApplicationRun)
        .filter(ApplicationRun.dedup_key == dedup_key)
        .filter(ApplicationRun.state.in_(_BLOCKING_STATES))
        .filter(ApplicationRun.started_at >= horizon)
        .order_by(ApplicationRun.started_at.desc())
        .first()
    )


def is_duplicate(
    db: Session,
    company: Optional[str],
    title: Optional[str],
    location: Optional[str],
) -> tuple[bool, Optional[ApplicationRun]]:
    """Convenience wrapper: compute key + check. Used by apply_runner
    immediately before handing off to an adapter."""

    key = compute_key(company, title, location)
    prior = find_blocking_run(db, key)
    return prior is not None, prior
