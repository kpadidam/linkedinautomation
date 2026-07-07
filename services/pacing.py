"""Apply-loop pacing decisions.

Pure function ``should_apply_now(profile, db, now=...)`` returns
``(allowed, reason)``. The apply loop calls this every tick and only
spawns Playwright when ``allowed is True``.

Pacing matters more than volume for LinkedIn anti-detection (paircode
round 2 consensus). The rules in priority order:

  1. Circuit breaker tripped       -> halt until operator reset
  2. ``auto_apply_enabled`` is off -> halt (dry-run kill switch)
  3. Inside quiet hours            -> wait until quiet_hours_end
  4. Daily cap hit                 -> wait until next UTC day
  5. Last apply too recent         -> lognormal gap (mu=mean_gap_min)

The lognormal gap is what gives the bot human-shaped cadence: most
intervals near the mean, occasional long pauses, no equal-spaced
clockwork the way naive ``sleep(N)`` would produce.

Slice 3 only ever runs dry-run navigations, so these gates exist to
exercise the plumbing — the values are tunable in Settings once the
operator has a sense of the noise floor.
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from database.models import ApplicationRun

logger = logging.getLogger(__name__)


# ----- knobs the operator can tune via Settings later --------------------

# Lognormal underlying parameters for the inter-apply gap. mu/sigma are in
# *log-minutes*. The unconditional mean of a lognormal is exp(mu + 0.5*s^2);
# with mu=3.4 and sigma=0.8 that's ~41 min on average, with a heavy tail.
_LOGNORMAL_MU = 3.4
_LOGNORMAL_SIGMA = 0.8

# Minimum hard floor — no matter what the lognormal samples, don't apply
# within 3 minutes of the prior apply. Belt-and-suspenders against a
# random seed picking a tiny value.
_MIN_GAP_MINUTES = 3


def _sample_next_gap_minutes(rng: random.Random | None = None) -> float:
    rng = rng or random.Random()
    sample = rng.lognormvariate(_LOGNORMAL_MU, _LOGNORMAL_SIGMA)
    return max(sample, float(_MIN_GAP_MINUTES))


# ----- public API --------------------------------------------------------


@dataclass
class PacingDecision:
    allowed: bool
    reason: str
    wait_minutes: float | None = None  # informative; loop sleeps its own tick


def in_quiet_hours(
    start_hour: int, end_hour: int, now_local_hour: int
) -> bool:
    """True if ``now_local_hour`` is in the quiet window.

    Handles the typical overnight wrap (e.g. start=23, end=7 means
    "no apply between 11 pm and 7 am"). If start == end the window is
    empty (never quiet).
    """

    if start_hour == end_hour:
        return False
    if start_hour < end_hour:
        # Daytime quiet (uncommon but supported).
        return start_hour <= now_local_hour < end_hour
    # Overnight wrap.
    return now_local_hour >= start_hour or now_local_hour < end_hour


def _local_hour(utc_now: datetime) -> int:
    """Return the operator's local hour. Slice 3 uses the system tz of the
    backend process (good enough for a single-operator local app — the
    backend runs on the operator's laptop). Slice 4 may surface a TZ
    setting in the UI if needed.
    """

    return utc_now.astimezone().hour


def _applies_today(db: Session, since_utc: datetime) -> int:
    """Count successful apply attempts since the start of the local day.

    Counts only ``submitted`` and ``submitted_dry_run`` — failed runs
    don't burn the daily budget. Otherwise a flaky 5-minute period could
    artificially exhaust the cap.
    """

    return (
        db.query(ApplicationRun)
        .filter(ApplicationRun.started_at >= since_utc)
        .filter(ApplicationRun.state.in_(("submitted", "submitted_dry_run")))
        .count()
    )


# Weekday/weekend cap multiplier per paircode r2. Real humans apply less
# on weekends; the bot should too. 1.0 weekday, 0.4 weekend.
_WEEKEND_CAP_MULTIPLIER = 0.4


def _effective_daily_cap(profile, now: datetime) -> int:
    base = int(profile.daily_apply_cap or 15)
    # Monday=0 .. Sunday=6 in datetime.weekday()
    is_weekend = now.replace(tzinfo=timezone.utc).astimezone().weekday() >= 5
    if is_weekend:
        return max(1, int(base * _WEEKEND_CAP_MULTIPLIER))
    return base


def should_apply_now(
    profile,
    db: Session,
    now: datetime | None = None,
    rng: random.Random | None = None,
) -> PacingDecision:
    """Decide whether the apply loop should fire on this tick."""

    now = now or datetime.utcnow()

    if getattr(profile, "circuit_tripped", False):
        return PacingDecision(False, "circuit_tripped", None)

    if not getattr(profile, "auto_apply_enabled", False):
        return PacingDecision(False, "auto_apply_disabled", None)

    qh_start = int(profile.quiet_hours_start or 23)
    qh_end = int(profile.quiet_hours_end or 7)
    local_h = _local_hour(now.replace(tzinfo=timezone.utc))
    if in_quiet_hours(qh_start, qh_end, local_h):
        return PacingDecision(False, f"quiet_hours[{qh_start}-{qh_end}]", None)

    # Local-day start, anchored at midnight in the operator's tz.
    local_now = now.replace(tzinfo=timezone.utc).astimezone()
    local_midnight = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    day_start_utc = local_midnight.astimezone(timezone.utc).replace(tzinfo=None)
    cap = _effective_daily_cap(profile, now)
    applied_today = _applies_today(db, day_start_utc)
    if applied_today >= cap:
        return PacingDecision(False, f"daily_cap_hit[{applied_today}/{cap}]", None)

    last = profile.last_apply_at
    if last is not None:
        gap_min = _sample_next_gap_minutes(rng)
        elapsed = (now - last).total_seconds() / 60.0
        if elapsed < gap_min:
            return PacingDecision(
                False,
                f"too_soon[elapsed={elapsed:.1f}m, needed={gap_min:.1f}m]",
                gap_min - elapsed,
            )

    return PacingDecision(True, "ok", None)
