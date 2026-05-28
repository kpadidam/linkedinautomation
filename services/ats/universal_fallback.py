"""Universal ATS fallback via browser-use (slice 6).

When ``detect_ats(url, page)`` returns ``ATSKind.UNKNOWN`` and the
operator has explicitly opted in (``profile.apply_unknown_ats_with_llm``,
default False), this module drives the form via the ``browser-use``
agent — an LLM-in-the-loop browser controller.

Trade-offs (per paircode r2 consensus):
  + Handles ATSes we don't have a hardcoded adapter for
  + Adapts to per-tenant form variations Workday is famous for
  - Slow: every form field triggers an LLM call (~$0.05/application)
  - Less deterministic — harder to audit + replay
  - Opt-in only — never the default path

The fallback is wrapped in ``UniversalAdapter`` so the apply runner
treats it identically to a hardcoded adapter (same ``ApplyResult`` shape,
same dry-run semantics). It just costs more and the form_log entries
have ``source='llm_agent'``.

Slice 6 ships this module + an opt-in toggle. Initial ship intentionally
defaults to OFF so the operator can verify each known-ATS adapter
first; opt-in unlocks coverage of the long-tail ATSes.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from services.ats.base import (
    ATSAdapter,
    ATSKind,
    ApplyResult,
    ApplyStatus,
    FormField,
)

if TYPE_CHECKING:
    from playwright.async_api import Page

logger = logging.getLogger(__name__)


class UniversalAdapter(ATSAdapter):
    """browser-use-driven adapter for ATSes without a hardcoded module.

    Not registered with ``@register_adapter`` — the runner instantiates
    this directly only when the standard registry returns UNKNOWN AND
    the operator has opted in. That keeps it out of detect_ats() (which
    iterates the registry) and prevents accidental fallback.
    """

    KIND = ATSKind.UNKNOWN
    URL_PATTERNS = ()  # never matches by URL — we're invoked explicitly

    @classmethod
    def recognize(cls, html: str) -> bool:
        # Universal adapter never claims a page on its own — it's an
        # opt-in last resort, not a registry candidate.
        return False

    async def apply(
        self,
        page: Page,
        job,
        profile,
        dry_run: bool = True,
    ) -> ApplyResult:
        """Drive the form via browser-use.

        NOTE: this is currently a SCAFFOLD. The full browser-use
        integration ships after slices 4-5 prove the hardcoded
        adapters work — there's no point spending LLM cycles on
        universal coverage until the deterministic path is solid.

        Today it returns ``NEEDS_USER_INPUT`` so the operator knows
        the page wasn't auto-recognized and they need to apply
        manually (or wait for slice 6's full implementation).
        """

        # SCAFFOLD-ONLY return. The full implementation will:
        # 1. Spawn browser-use agent with profile context + resume
        # 2. Give it a goal: "fill out the application form using the
        #    operator's profile, stop before final submit"
        # 3. Stream the agent's actions; cap at N steps + M minutes
        # 4. On dry_run=False: let the agent click submit
        # 5. Verify confirmation page or fail with screenshots
        # 6. Cache resulting selectors as a learned adapter pattern
        return ApplyResult(
            status=ApplyStatus.NEEDS_USER_INPUT,
            exit_reason="unknown_ats_universal_fallback_not_yet_implemented",
            fields_logged=[
                FormField(
                    label="(universal-fallback)",
                    value="not implemented in slice 4 — opt-in launches in slice 6",
                    source="default",
                    confidence=0.0,
                )
            ],
            detected_ats=ATSKind.UNKNOWN,
        )
