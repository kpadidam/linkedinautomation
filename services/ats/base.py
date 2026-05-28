"""ATS adapter ABC + detection.

Every concrete adapter (Greenhouse, LinkedIn Easy Apply, Workday, Lever,
Ashby, ...) inherits ``ATSAdapter`` and implements ``apply()``. The
apply runner calls ``detect_ats(url, html)`` to pick the right one,
then dispatches.

Why an ABC at all: slice 4 ships Greenhouse, slice 5 ships Easy Apply,
slice 6 ships three more. Without a shared contract the runner would
fork into a switch statement that's hostile to extend. The contract is
small on purpose — adapters are free to do their own DOM dance internally
as long as they return a normalized ``ApplyResult``.
"""

from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.async_api import Page

logger = logging.getLogger(__name__)


class ATSKind(str, Enum):
    """Known ATS providers. ``UNKNOWN`` triggers the browser-use
    fallback (slice 6) if the operator opted in."""

    EASY_APPLY = "easy_apply"
    GREENHOUSE = "greenhouse"
    WORKDAY = "workday"
    LEVER = "lever"
    ASHBY = "ashby"
    UNKNOWN = "unknown"


class ApplyStatus(str, Enum):
    """Outcome of a single ``apply()`` call. Maps 1:1 to
    ``ApplicationRun.state`` values in ``database/models.py``."""

    SUBMITTED = "submitted"
    SUBMITTED_DRY_RUN = "submitted_dry_run"
    SKIPPED_DUPLICATE = "skipped_duplicate"
    SKIPPED_REQUIRES_COVER_LETTER = "skipped_requires_cover_letter"
    NEEDS_USER_INPUT = "needs_user_input"
    BLOCKED_CAPTCHA = "blocked_captcha"
    BLOCKED_AUTH = "blocked_auth"
    FAILED_UNAVAILABLE = "failed_unavailable"
    FAILED_RETRYABLE = "failed_retryable"
    FAILED_TERMINAL = "failed_terminal"


@dataclass
class FormField:
    """One field the adapter encountered while parsing the form.

    The runner persists this into ``ApplicationRun.form_log`` so the
    operator can see exactly what was filled — required for the audit
    trail. ``source`` tells you whether the value came from a heuristic
    map, a profile lookup, an LLM call, or a hard-coded default.
    """

    label: str
    value: str
    source: str  # "heuristic" | "profile" | "llm" | "default" | "skipped"
    confidence: float = 1.0  # adapters set lower when guessing
    selector: Optional[str] = None  # CSS / role selector for debugging


@dataclass
class ApplyResult:
    """Return value of ``ATSAdapter.apply()``. The runner translates
    this into an ``ApplicationRun`` row."""

    status: ApplyStatus
    exit_reason: str  # short slug for the DB column
    fields_logged: list[FormField] = field(default_factory=list)
    screenshots: list[str] = field(default_factory=list)  # paths
    error_message: Optional[str] = None  # set on failed_* paths
    detected_ats: ATSKind = ATSKind.UNKNOWN


class UnknownATS(Exception):
    """Raised when no adapter recognizes the page."""


class ATSAdapter(ABC):
    """Per-ATS implementation. Adapters must be stateless beyond the
    constructor — the runner instantiates a new one per apply attempt.

    Subclass contract:
      * ``KIND`` — the ``ATSKind`` value this adapter handles.
      * ``URL_PATTERNS`` — regex list matched against ``job.url``. Empty
        means URL alone never identifies this ATS; rely on DOM detection.
      * ``recognize(html)`` — return True if the rendered HTML matches.
      * ``apply(page, job, profile, dry_run)`` — the actual flow.

    ``apply()`` MUST NOT raise on expected failure modes (form
    validation, missing fields, captcha) — it should set the right
    ``ApplyStatus`` and return. Raising is for genuinely unexpected
    errors that the runner should treat as ``failed_retryable``.
    """

    KIND: ATSKind = ATSKind.UNKNOWN
    URL_PATTERNS: tuple[re.Pattern, ...] = ()

    @classmethod
    def matches_url(cls, url: str) -> bool:
        if not url:
            return False
        return any(p.search(url) for p in cls.URL_PATTERNS)

    @classmethod
    @abstractmethod
    def recognize(cls, html: str) -> bool:
        """Return True if the rendered DOM looks like this ATS. Cheap
        substring/regex check — runs after navigate, before apply."""

    @abstractmethod
    async def apply(
        self,
        page: Page,
        job,  # database.models.Job (avoiding circular import)
        profile,  # database.models.UserProfile
        dry_run: bool = True,
    ) -> ApplyResult:
        """Drive the page through the apply flow.

        ``dry_run=True`` (default — safety):
          * Parse the form, fill heuristically, identify unknowns
          * Take screenshots at key points
          * DO NOT click the final submit button
          * Return ``SUBMITTED_DRY_RUN`` with ``fields_logged`` populated

        ``dry_run=False``:
          * Same as above, but actually click submit
          * Verify confirmation page / success state before returning
            ``SUBMITTED``
          * On confirmation-not-found, return ``FAILED_RETRYABLE`` with
            screenshots so the operator can see what happened
        """


# Adapter registry. Populated by ``register_adapter`` (called inside
# each concrete module so importing it has the side effect).
_REGISTRY: list[type[ATSAdapter]] = []


def register_adapter(cls: type[ATSAdapter]) -> type[ATSAdapter]:
    """Class decorator. Each concrete adapter ends with ``@register_adapter``
    above its class definition. Keeps the registry honest — no one can
    import an adapter without it being discoverable."""

    if cls in _REGISTRY:
        return cls
    _REGISTRY.append(cls)
    logger.debug(f"Registered ATS adapter: {cls.__name__} -> {cls.KIND}")
    return cls


async def detect_ats(url: str, page: Page) -> tuple[ATSKind, Optional[type[ATSAdapter]]]:
    """Identify which ATS a page is. URL first, then DOM probe.

    Returns ``(kind, adapter_cls)``. ``kind`` is ``UNKNOWN`` when no
    adapter recognizes the page; the runner then either gives up or
    falls through to ``browser-use`` (slice 6).
    """

    # Import concrete adapters lazily so this module has no hard deps
    # on the implementations (which might import playwright at module
    # level and slow startup).
    _import_concrete_adapters()

    # URL pattern pass — cheapest. Most ATS-hosted URLs are unambiguous.
    for cls in _REGISTRY:
        if cls.matches_url(url):
            return cls.KIND, cls

    # DOM probe — sometimes URLs are vanity-redirected or shortened.
    try:
        html = await page.content()
    except Exception:  # noqa: BLE001
        return ATSKind.UNKNOWN, None

    for cls in _REGISTRY:
        try:
            if cls.recognize(html):
                return cls.KIND, cls
        except Exception:  # noqa: BLE001
            logger.warning(f"Adapter {cls.__name__}.recognize raised", exc_info=True)
            continue

    return ATSKind.UNKNOWN, None


def _import_concrete_adapters() -> None:
    """Trigger module imports so ``@register_adapter`` runs.

    Wrapped in a function so the registration only happens when
    ``detect_ats`` is actually called — keeps test imports cheap.
    """

    try:
        from services.ats import greenhouse  # noqa: F401
    except ImportError:
        pass
    try:
        from services.ats import easyapply  # noqa: F401
    except ImportError:
        pass
    try:
        from services.ats import workday  # noqa: F401
    except ImportError:
        pass
    try:
        from services.ats import lever  # noqa: F401
    except ImportError:
        pass
    try:
        from services.ats import ashby  # noqa: F401
    except ImportError:
        pass
