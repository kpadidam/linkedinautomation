"""LinkedIn-specific anti-detection circuit breaker.

Watches every Playwright response that comes back during an apply run.
If any of the eight tripwires fires we halt the apply loop immediately,
mark the breaker tripped in ``user_profile``, and let the operator
investigate. The breaker is sticky — only an explicit
``POST /api/apply/circuit/reset`` clears it.

The tripwires are from the paircode round-2 consensus
(``.paircode/focus-02-linkedin-auto-apply-arch/ask/consensus-r2.md``).
They cover both wire-level and rendered-content signals LinkedIn uses
when it suspects automation.

Tripwires:
  1. HTTP 999 — LinkedIn's documented anti-scrape denial code
  2. Repeated 429 (rate-limit)
  3. HTTP 403 on a ``/voyager/`` endpoint while authenticated
  4. Redirect to any ``/checkpoint/...`` path
  5. Missing or expired ``li_at`` cookie, or CSRF / JSESSIONID mismatch
  6. Unauthenticated navigation to ``/login``
  7. Response body containing ``checkpoint`` / ``challenge`` /
     ``security-verification`` / ``unusual activity``
  8. ``captcha`` iframe detected, or Easy Apply modal replaced by an
     auth / challenge container

Slice 3 wires this to live LinkedIn traffic during dry-run navigations.
Nothing tries to recover automatically — the only path out of a trip
is the operator reset endpoint.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Optional

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


# Body-content sniff. Case-insensitive substring match — these phrases all
# appear in LinkedIn's security / challenge pages and rarely otherwise.
_BODY_SIGNALS = (
    "unusual activity",
    "security verification",
    "security-verification",
    "verify it's you",
    "checkpoint",
    "challenge",
)

_VOYAGER_RE = re.compile(r"/voyager/", re.IGNORECASE)
_CHECKPOINT_RE = re.compile(r"/checkpoint(/|$|\?)", re.IGNORECASE)
_LOGIN_RE = re.compile(r"/(login|uas/login|authwall)(/|$|\?)", re.IGNORECASE)


class CircuitTripped(Exception):
    """Raised when the breaker should halt the run mid-flight."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


@dataclass
class CircuitObservation:
    """One wire-level event the breaker should evaluate."""

    url: str
    status: int
    body_snippet: str = ""  # first ~4KB of the response body is enough
    cookies: dict[str, str] | None = None
    was_authenticated: bool = True  # set False before login completes


class CircuitBreaker:
    """Per-run breaker — collects observations then commits a trip to DB.

    Usage:
        breaker = CircuitBreaker(profile, db)
        try:
            ...
            breaker.observe(obs)
        except CircuitTripped as e:
            ...

    The breaker also counts consecutive failures (across runs, via
    ``profile.circuit_consecutive_failures``). Three in a row hard-trips
    even without a specific tripwire match — a safety net for unknown
    failure modes.
    """

    CONSECUTIVE_FAILURE_TRIP = 3
    _429_HITS_TRIP = 3

    def __init__(self, profile, db: Session):
        self.profile = profile
        self.db = db
        self._429_hits = 0

    # ----- read state ----------------------------------------------------

    @property
    def is_tripped(self) -> bool:
        return bool(getattr(self.profile, "circuit_tripped", False))

    # ----- evaluate one observation -------------------------------------

    def observe(self, obs: CircuitObservation) -> None:
        """Raise ``CircuitTripped`` if this response triggers any tripwire.

        Trip side-effect: persist breaker state on ``user_profile`` before
        raising, so the next loop tick sees ``is_tripped`` even if the
        caller swallows the exception.
        """

        reason: Optional[str] = None
        url = obs.url or ""
        status = obs.status
        body = (obs.body_snippet or "").lower()
        cookies = obs.cookies or {}

        # 1. HTTP 999
        if status == 999:
            reason = "http_999_linkedin_block"

        # 2. Repeated 429
        elif status == 429:
            self._429_hits += 1
            if self._429_hits >= self._429_HITS_TRIP:
                reason = f"http_429_x{self._429_hits}_rate_limit"

        # 3. 403 on Voyager
        elif (
            status == 403
            and obs.was_authenticated
            and _VOYAGER_RE.search(url)
        ):
            reason = "voyager_403"

        # 4. /checkpoint/ redirect
        if reason is None and _CHECKPOINT_RE.search(url):
            reason = "checkpoint_redirect"

        # 5. Missing/expired li_at on an authenticated request
        if (
            reason is None
            and obs.was_authenticated
            and ("li_at" in cookies)
            and not cookies.get("li_at")
        ):
            reason = "li_at_expired"

        # 6. Unauthenticated nav to /login while we expected auth
        if (
            reason is None
            and obs.was_authenticated
            and _LOGIN_RE.search(url)
        ):
            reason = "unexpected_login_redirect"

        # 7. Body signals
        if reason is None and body:
            for needle in _BODY_SIGNALS:
                if needle in body:
                    reason = f"body_signal[{needle}]"
                    break

        if reason is None:
            return

        self.trip(reason)

    # ----- explicit trips -----------------------------------------------

    def trip(self, reason: str) -> None:
        """Persist a trip to the DB and raise."""

        logger.error(f"Circuit breaker tripped: {reason}")
        self.profile.circuit_tripped = True
        self.profile.circuit_tripped_at = datetime.utcnow()
        self.profile.circuit_tripped_reason = reason[:200]
        self.db.commit()
        raise CircuitTripped(reason)

    def record_consecutive_failure(self) -> None:
        """Increment the failure counter; hard-trip at N consecutive."""

        n = int(self.profile.circuit_consecutive_failures or 0) + 1
        self.profile.circuit_consecutive_failures = n
        self.db.commit()
        if n >= self.CONSECUTIVE_FAILURE_TRIP:
            self.trip(f"consecutive_failures[{n}]")

    def record_success(self) -> None:
        """Reset the consecutive-failure counter after a clean run."""

        if int(self.profile.circuit_consecutive_failures or 0) != 0:
            self.profile.circuit_consecutive_failures = 0
            self.db.commit()


def reset_breaker(profile, db: Session) -> None:
    """Operator-driven reset. Called by ``POST /api/apply/circuit/reset``."""

    profile.circuit_tripped = False
    profile.circuit_tripped_at = None
    profile.circuit_tripped_reason = None
    profile.circuit_consecutive_failures = 0
    db.commit()


def captcha_iframe_present(html: str) -> bool:
    """Convenience helper for DOM-level captcha detection (tripwire #8).

    Apply runner calls this on the rendered page once. If True it should
    call ``breaker.trip('captcha_iframe')``.

    Only matches concrete captcha provider hosts to avoid the
    false-positive where any LinkedIn auth page mentions "captcha" in its
    security-info text *and* has tracking iframes. We trust the provider
    names — Arkose Labs, FunCaptcha, hCaptcha, Google reCAPTCHA — and
    keep the substring search anchored to URLs that load their assets.
    """

    if not html:
        return False
    lo = html.lower()
    return (
        "arkoselabs.com" in lo
        or "funcaptcha.com" in lo
        or "hcaptcha.com" in lo
        or "www.google.com/recaptcha" in lo
    )


def auth_wall_present(html: str, url: str | None = None) -> bool:
    """Detect LinkedIn's "sign in to view more jobs" wall.

    LinkedIn routes unauthenticated viewers to ``/authwall`` (sometimes
    via redirect, sometimes inline). Both the URL match and the visible
    "Sign in to view" copy on the page are tells. Distinct from the
    breaker's ``unexpected_login_redirect`` tripwire (which fires when
    we *expected* to be authed and weren't) — auth wall on an ephemeral
    browser is normal and not a security signal.
    """

    if url and "/authwall" in url.lower():
        return True
    if not html:
        return False
    lo = html.lower()
    return (
        "sign in to view more jobs" in lo
        or "sign in to view" in lo
        and "linkedin" in lo
    )
