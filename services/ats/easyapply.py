"""LinkedIn Easy Apply adapter (slice 5).

Drives the in-modal Easy Apply multi-step form. Unlike Greenhouse —
where the page is a vanilla HTML form — Easy Apply renders a React
dialog over the JD page and pumps DOM mutations between 2-5 steps:
contact info → resume → screening questions → review → submit.

Critical constraints (see docs/auto-apply-plan.md + paircode r2):

* Real session REQUIRED. Easy Apply will not even open the modal for
  an unauthenticated viewer — the apply button collapses to a "Sign in
  to apply" auth-wall route. We check ``auth_wall_present`` first and
  bail with ``BLOCKED_AUTH`` so the runner halts without burning a
  retry budget.
* Anti-bot: type via ``page.keyboard.type`` with lognormal delay
  (μ≈80ms); never ``page.fill``. Hover before click. Random dwell
  300-2000ms between step transitions.
* ``dry_run=True`` is the default and MUST NOT click Submit application.
  We screenshot ``about_to_submit.png`` instead.

Result codes:
  SUBMITTED_DRY_RUN  — modal walked to the submit button, did not click
  SUBMITTED          — clicked submit, observed confirmation copy
  BLOCKED_AUTH       — auth wall present (no session)
  BLOCKED_CAPTCHA    — captcha iframe inside modal
  NEEDS_USER_INPUT   — required field unresolved OR only "Save and
                       submit later" available (LinkedIn's tell that
                       required validation is failing)
  FAILED_RETRYABLE   — modal failed to open / step never advanced
"""

from __future__ import annotations

import asyncio
import logging
import random
import re
from pathlib import Path
from typing import Optional, TYPE_CHECKING

import yaml

from services.ats.base import (
    ATSAdapter,
    ATSKind,
    ApplyResult,
    ApplyStatus,
    FormField,
    register_adapter,
)
from services.circuit_breaker import auth_wall_present, captcha_iframe_present

if TYPE_CHECKING:
    from playwright.async_api import Locator, Page

logger = logging.getLogger(__name__)


# ---------- selector inventory ----------------------------------------
# Kept at module scope so a single LinkedIn DOM change can be patched in
# one place. Order matters — first hit wins.

_APPLY_BUTTON_SELECTORS = (
    # LinkedIn shipped a DOM change ca. mid-2026: the Easy Apply
    # affordance is now an <a> with aria-label="Easy Apply to this job",
    # not the old <button>. Match both elements + both attribute paths
    # so we keep working through either shape.
    "a[aria-label*='Easy Apply' i]",
    "button[aria-label*='Easy Apply' i]",
    "a:has-text('Easy Apply')",
    "button:has-text('Easy Apply')",
    "button[data-test='jobs-apply-button']",
    "button.jobs-apply-button",
)

_MODAL_SELECTORS = (
    "div.jobs-easy-apply-modal",
    "div[data-test-modal][role='dialog']",
    "div[role='dialog']",
)

# Buttons that progress to the next step. "Review your application"
# appears one step before the final submit screen; "Submit application"
# is the final commit. "Save and submit later" surfaces when the form
# has unresolved required fields — treat as NEEDS_USER_INPUT.
_NEXT_BUTTON_SELECTORS = (
    "button[aria-label*='Continue to next step' i]",
    "button[data-easy-apply-next-button]",
    "button:has-text('Continue')",
    "button:has-text('Next')",
)
_REVIEW_BUTTON_SELECTORS = (
    "button[aria-label*='Review your application' i]",
    "button:has-text('Review')",
)
_SUBMIT_BUTTON_SELECTORS = (
    "button[aria-label*='Submit application' i]",
    "button:has-text('Submit application')",
)
_SAVE_LATER_BUTTON_SELECTORS = (
    "button[aria-label*='Save and submit later' i]",
    "button:has-text('Save and submit later')",
)
_DISMISS_BUTTON_SELECTORS = (
    "button[aria-label*='Dismiss' i]",
    "button:has-text('Discard')",
)

_CONFIRMATION_PHRASES = (
    "application sent",
    "your application was sent",
    "your application has been submitted",
    "applied",
)

_MAX_STEPS = 8  # belt-and-suspenders — real flows are 2-5


# ---------- anti-bot helpers ------------------------------------------


def _lognormal_delay_ms(rng: random.Random, mean_ms: float = 80.0) -> int:
    """Per-keystroke delay. Lognormal because human typing is bursty —
    a Gaussian flattens the tail and bots-with-Gaussian-delay are now
    a known fingerprint (paircode r2 anti-bot priority list)."""

    mu = 4.0     # log ms; e^4 ≈ 55
    sigma = 0.45
    s = rng.lognormvariate(mu, sigma)
    # Anchor toward `mean_ms` while preserving distribution shape.
    s *= mean_ms / 55.0
    return max(20, min(450, int(s)))


async def _random_dwell(rng: random.Random, lo: float = 0.3, hi: float = 2.0) -> None:
    """Inter-step pause. Real users hesitate; instant transitions look
    scripted to LinkedIn's behavioral model."""

    await asyncio.sleep(rng.uniform(lo, hi))


async def _hover_and_click(locator: Locator, rng: random.Random) -> None:
    """Hover (real mousemove), micro-pause, then click. Cheap deception
    that defeats the "no hover before click" detector."""

    try:
        await locator.hover(timeout=4000)
        await asyncio.sleep(rng.uniform(0.08, 0.35))
    except Exception:  # noqa: BLE001
        pass
    await locator.click(timeout=8000)


async def _human_type(page: Page, locator: Locator, text: str, rng: random.Random) -> None:
    """Focus the field, then ``keyboard.type`` with lognormal delays.

    We *don't* use ``page.fill`` — it sets ``value`` directly and emits
    a single composite ``input`` event, which both stealth audits and
    LinkedIn's own telemetry flag."""

    if text is None:
        return
    text = str(text)
    if not text:
        return
    try:
        await locator.click(timeout=4000)
    except Exception:  # noqa: BLE001
        await locator.focus()
    # Clear any pre-fill: select-all + delete is more "human" than
    # locator.fill('').
    try:
        await page.keyboard.press("Meta+A")
    except Exception:  # noqa: BLE001
        await page.keyboard.press("Control+A")
    await page.keyboard.press("Backspace")
    for ch in text:
        await page.keyboard.type(ch, delay=_lognormal_delay_ms(rng))


# ---------- field-map loader ------------------------------------------


def _load_field_map() -> list[dict]:
    """Read ``services/ats/field_map.yaml`` once. Cached in module scope
    on first call. Tolerates the file being absent in sandbox runs."""

    try:
        path = Path(__file__).resolve().parent.parent / "services" / "ats" / "field_map.yaml"
        if not path.exists():
            # Sandbox layout: search upward.
            for parent in Path(__file__).resolve().parents:
                cand = parent / "services" / "ats" / "field_map.yaml"
                if cand.exists():
                    path = cand
                    break
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return data.get("mappings", []) or []
    except Exception:  # noqa: BLE001
        logger.warning("[easyapply] field_map.yaml not loadable; running with empty map")
        return []


_FIELD_MAP: list[dict] = []


def _get_field_map() -> list[dict]:
    global _FIELD_MAP
    if not _FIELD_MAP:
        _FIELD_MAP = _load_field_map()
    return _FIELD_MAP


def _match_label(label: str) -> Optional[dict]:
    """Return the field-map entry whose regex matches ``label`` (case-
    insensitive). First match wins per field_map.yaml convention."""

    if not label:
        return None
    cleaned = label.strip().lower()
    cleaned = re.sub(r"[*\?\:]+$", "", cleaned).strip()
    for entry in _get_field_map():
        pat = entry.get("pattern")
        if not pat:
            continue
        try:
            if re.search(pat, cleaned, re.IGNORECASE):
                return entry
        except re.error:
            continue
    return None


def _resolve_profile_value(profile, key: str) -> Optional[str]:
    """Dot-path lookup against ``UserProfile``. Handles the two
    composite paths called out in field_map.yaml:
    ``name.first`` / ``name.last`` / ``name.full``."""

    if not key:
        return None
    if key.startswith("name."):
        full = getattr(profile, "name", None) or ""
        parts = full.strip().split()
        if key == "name.first":
            return parts[0] if parts else None
        if key == "name.last":
            return parts[-1] if len(parts) > 1 else None
        if key == "name.full":
            return full or None
    # Flat attr lookup (with one-level dotted fallback for work_auth.*).
    if "." in key:
        head, tail = key.split(".", 1)
        sub = getattr(profile, head, None)
        if sub is None:
            return None
        if isinstance(sub, dict):
            return sub.get(tail)
        return getattr(sub, tail, None)
    val = getattr(profile, key, None)
    return val if val is not None else None


# ---------- adapter ----------------------------------------------------


@register_adapter
class EasyApplyAdapter(ATSAdapter):
    KIND = ATSKind.EASY_APPLY
    URL_PATTERNS = (
        re.compile(r"linkedin\.com/jobs/view/", re.IGNORECASE),
        re.compile(r"linkedin\.com/jobs/collections/.*currentJobId=", re.IGNORECASE),
    )

    @classmethod
    def recognize(cls, html: str) -> bool:
        if not html:
            return False
        lo = html.lower()
        return (
            "jobs-apply-button" in lo
            or "jobs-easy-apply" in lo
            or "easy apply" in lo
        )

    # ------------------------------------------------------------------

    async def apply(
        self,
        page: Page,
        job,
        profile,
        dry_run: bool = True,
    ) -> ApplyResult:
        rng = random.Random()
        screenshots: list[str] = []
        fields_logged: list[FormField] = []

        # Screenshot directory. Mirrors apply_runner's convention but
        # tolerates being called outside the runner (tests).
        run_id = getattr(job, "job_id", "adhoc")
        shot_dir = Path("data") / "apply_runs" / f"easyapply_{run_id}"
        try:
            shot_dir.mkdir(parents=True, exist_ok=True)
        except Exception:  # noqa: BLE001
            shot_dir = Path(".")

        async def shot(name: str) -> str:
            p = shot_dir / name
            try:
                await page.screenshot(path=str(p), full_page=False)
                screenshots.append(str(p))
                return str(p)
            except Exception:  # noqa: BLE001
                logger.warning("[easyapply] screenshot failed: %s", name)
                return ""

        # --- 1. Auth wall preflight -----------------------------------
        try:
            html = await page.content()
        except Exception:  # noqa: BLE001
            html = ""
        current_url = page.url or ""

        if auth_wall_present(html, current_url):
            await shot("00_authwall.png")
            return ApplyResult(
                status=ApplyStatus.BLOCKED_AUTH,
                exit_reason="auth_wall_no_session",
                screenshots=screenshots,
                detected_ats=self.KIND,
                error_message="LinkedIn auth wall — Easy Apply requires a real session",
            )

        # --- 2. Locate + click Easy Apply button ----------------------
        # CSS-selector pass first (cheapest + most precise via aria-label).
        # If selectors miss, fall through to Playwright's accessible-name
        # search across BOTH roles (button + link, since LinkedIn ships
        # the affordance as an <a> now).
        apply_btn = await self._first_visible(page, _APPLY_BUTTON_SELECTORS)
        if apply_btn is None:
            for role in ("link", "button"):
                try:
                    loc = page.get_by_role(
                        role, name=re.compile(r"easy\s*apply", re.IGNORECASE)
                    ).first
                    if await loc.count() > 0:
                        try:
                            if await loc.is_visible(timeout=1500):
                                apply_btn = loc
                                break
                        except Exception:  # noqa: BLE001
                            apply_btn = loc
                            break
                except Exception:  # noqa: BLE001
                    continue

        if apply_btn is None:
            await shot("00_no_apply_button.png")
            return ApplyResult(
                status=ApplyStatus.FAILED_UNAVAILABLE,
                exit_reason="no_easy_apply_button",
                screenshots=screenshots,
                detected_ats=self.KIND,
                error_message="Easy Apply button not found on JD page",
            )

        await _random_dwell(rng, 0.5, 1.6)
        await _hover_and_click(apply_btn, rng)

        # --- 3. Wait for modal ----------------------------------------
        modal = await self._wait_for_modal(page)
        if modal is None:
            await shot("00_modal_did_not_open.png")
            return ApplyResult(
                status=ApplyStatus.FAILED_RETRYABLE,
                exit_reason="modal_open_timeout",
                screenshots=screenshots,
                detected_ats=self.KIND,
                error_message="Easy Apply modal failed to render after click",
            )

        await shot("modal_opened.png")

        # Captcha sniff inside the modal scope.
        try:
            modal_html = await page.content()
        except Exception:  # noqa: BLE001
            modal_html = ""
        if captcha_iframe_present(modal_html):
            await shot("captcha_in_modal.png")
            return ApplyResult(
                status=ApplyStatus.BLOCKED_CAPTCHA,
                exit_reason="captcha_in_easyapply_modal",
                screenshots=screenshots,
                detected_ats=self.KIND,
            )

        # --- 4-6. Walk the multi-step flow ----------------------------
        for step_idx in range(1, _MAX_STEPS + 1):
            await _random_dwell(rng, 0.4, 1.4)

            # Fill any visible fields in the modal scope.
            step_fields = await self._fill_modal_step(page, modal, profile, job, rng)
            fields_logged.extend(step_fields)

            await shot(f"step_{step_idx}.png")

            # Look for the terminal "Save and submit later" signal —
            # if it's the ONLY action, LinkedIn is telling us required
            # validation failed and the operator must intervene.
            if await self._only_save_later_visible(page):
                await shot(f"step_{step_idx}_save_later.png")
                return ApplyResult(
                    status=ApplyStatus.NEEDS_USER_INPUT,
                    exit_reason="only_save_and_submit_later_available",
                    fields_logged=fields_logged,
                    screenshots=screenshots,
                    detected_ats=self.KIND,
                    error_message=(
                        "LinkedIn replaced Submit with 'Save and submit later' "
                        "— a required field is unresolved"
                    ),
                )

            # Are we at the final submit?
            submit_btn = await self._first_visible(page, _SUBMIT_BUTTON_SELECTORS)
            if submit_btn is not None:
                await shot("about_to_submit.png")
                if dry_run:
                    return ApplyResult(
                        status=ApplyStatus.SUBMITTED_DRY_RUN,
                        exit_reason="dry_run_at_submit",
                        fields_logged=fields_logged,
                        screenshots=screenshots,
                        detected_ats=self.KIND,
                    )
                # Real submit path.
                await _random_dwell(rng, 0.6, 1.8)
                await _hover_and_click(submit_btn, rng)
                confirmed = await self._wait_for_confirmation(page)
                await shot("post_submit.png")
                if confirmed:
                    return ApplyResult(
                        status=ApplyStatus.SUBMITTED,
                        exit_reason="confirmation_observed",
                        fields_logged=fields_logged,
                        screenshots=screenshots,
                        detected_ats=self.KIND,
                    )
                return ApplyResult(
                    status=ApplyStatus.FAILED_RETRYABLE,
                    exit_reason="no_confirmation_after_submit",
                    fields_logged=fields_logged,
                    screenshots=screenshots,
                    detected_ats=self.KIND,
                    error_message="Submit clicked but no confirmation copy appeared",
                )

            # Otherwise: progress via Review → Next → Continue (in that
            # priority). Review usually appears one step before Submit.
            advance = (
                await self._first_visible(page, _REVIEW_BUTTON_SELECTORS)
                or await self._first_visible(page, _NEXT_BUTTON_SELECTORS)
            )
            if advance is None:
                # Stalemate — no progress button. Probably an unhandled
                # required field; surface for the operator.
                await shot(f"step_{step_idx}_stuck.png")
                return ApplyResult(
                    status=ApplyStatus.NEEDS_USER_INPUT,
                    exit_reason="no_advance_button_visible",
                    fields_logged=fields_logged,
                    screenshots=screenshots,
                    detected_ats=self.KIND,
                    error_message=f"Stuck at step {step_idx} — no Next/Review/Submit",
                )

            # Capture DOM hash before click so we can detect mutation.
            before_sig = await self._modal_signature(page, modal)
            await _hover_and_click(advance, rng)
            await self._wait_for_step_mutation(page, modal, before_sig)

        # If we exhausted _MAX_STEPS without seeing Submit, treat as
        # NEEDS_USER_INPUT — better to surface than to spin forever.
        await shot("max_steps_exhausted.png")
        return ApplyResult(
            status=ApplyStatus.NEEDS_USER_INPUT,
            exit_reason="max_steps_exhausted",
            fields_logged=fields_logged,
            screenshots=screenshots,
            detected_ats=self.KIND,
            error_message=f"Walked {_MAX_STEPS} steps without reaching submit",
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    async def _first_visible(
        self, page: Page, selectors: tuple[str, ...]
    ) -> Optional[Locator]:
        """Return the first locator across ``selectors`` that has at
        least one visible match. Visibility check guards against
        Easy Apply rendering both the closed-modal stub and the open
        modal in the DOM at once."""

        for sel in selectors:
            try:
                loc = page.locator(sel).first
                if await loc.count() == 0:
                    continue
                # ``is_visible`` is best-effort — some buttons report
                # hidden during the React mount. Fall back to ``count``.
                try:
                    if await loc.is_visible(timeout=1500):
                        return loc
                except Exception:  # noqa: BLE001
                    return loc
            except Exception:  # noqa: BLE001
                continue
        return None

    async def _wait_for_modal(
        self, page: Page, timeout_ms: int = 12000
    ) -> Optional[Locator]:
        """Poll the modal selectors until one renders or timeout."""

        deadline = asyncio.get_event_loop().time() + (timeout_ms / 1000.0)
        while asyncio.get_event_loop().time() < deadline:
            for sel in _MODAL_SELECTORS:
                try:
                    loc = page.locator(sel).first
                    if await loc.count() > 0:
                        try:
                            await loc.wait_for(state="visible", timeout=1500)
                        except Exception:  # noqa: BLE001
                            pass
                        return loc
                except Exception:  # noqa: BLE001
                    continue
            await asyncio.sleep(0.25)
        return None

    async def _only_save_later_visible(self, page: Page) -> bool:
        """True iff a Save-and-submit-later button is visible AND no
        Submit / Review / Next button is."""

        save = await self._first_visible(page, _SAVE_LATER_BUTTON_SELECTORS)
        if save is None:
            return False
        for group in (_SUBMIT_BUTTON_SELECTORS, _REVIEW_BUTTON_SELECTORS, _NEXT_BUTTON_SELECTORS):
            if await self._first_visible(page, group) is not None:
                return False
        return True

    async def _wait_for_confirmation(
        self, page: Page, timeout_ms: int = 12000
    ) -> bool:
        """After Submit, LinkedIn replaces the modal with a "Your
        application was sent to {company}" panel. Wait for that copy."""

        deadline = asyncio.get_event_loop().time() + (timeout_ms / 1000.0)
        while asyncio.get_event_loop().time() < deadline:
            try:
                html_lo = (await page.content()).lower()
            except Exception:  # noqa: BLE001
                html_lo = ""
            for phrase in _CONFIRMATION_PHRASES:
                if phrase in html_lo:
                    return True
            await asyncio.sleep(0.5)
        return False

    async def _modal_signature(self, page: Page, modal: Locator) -> str:
        """Cheap fingerprint of the modal content — used to detect a
        step transition. Inner-text hash is good enough; we don't need
        cryptographic strength, just "did it change"."""

        try:
            txt = await modal.inner_text(timeout=2000)
        except Exception:  # noqa: BLE001
            return ""
        return str(hash(txt[:4000]))

    async def _wait_for_step_mutation(
        self,
        page: Page,
        modal: Locator,
        before_sig: str,
        timeout_ms: int = 8000,
    ) -> None:
        """Poll until the modal text content changes (next step
        rendered) or timeout. Falls back to a fixed sleep on error."""

        deadline = asyncio.get_event_loop().time() + (timeout_ms / 1000.0)
        while asyncio.get_event_loop().time() < deadline:
            await asyncio.sleep(0.25)
            sig = await self._modal_signature(page, modal)
            if sig and sig != before_sig:
                return
        # No mutation observed — defensive sleep, let the caller decide.
        await asyncio.sleep(0.5)

    # ---- per-step field filling --------------------------------------

    async def _fill_modal_step(
        self,
        page: Page,
        modal: Locator,
        profile,
        job,
        rng: random.Random,
    ) -> list[FormField]:
        """Enumerate inputs / textareas / selects inside the modal,
        match against the heuristic map, fill known fields.

        Returns a ``FormField`` per encountered field (including those
        marked ``source='skipped'``) for the audit log."""

        logs: list[FormField] = []
        # We scope the locator to the modal so we don't fill JD-page
        # search inputs or footer subscribe forms by accident.
        field_locators = modal.locator("input, textarea, select")
        try:
            count = await field_locators.count()
        except Exception:  # noqa: BLE001
            count = 0

        for i in range(count):
            f = field_locators.nth(i)
            try:
                tag = (await f.evaluate("el => el.tagName")).lower()
                input_type = (await f.get_attribute("type") or "").lower()
            except Exception:  # noqa: BLE001
                continue

            # Skip hidden / non-interactive types.
            if input_type in ("hidden", "submit", "button", "image"):
                continue
            try:
                if not await f.is_visible(timeout=500):
                    continue
            except Exception:  # noqa: BLE001
                pass

            label = await self._field_label(page, f)

            # Resume re-selection: radio with a filename-shaped label.
            if input_type == "radio":
                handled = await self._handle_resume_radio(f, label, profile, rng)
                if handled is not None:
                    logs.append(handled)
                continue

            entry = _match_label(label or "")
            value: Optional[str] = None
            source = "skipped"

            if entry:
                key = entry.get("profile_key")
                resolved = _resolve_profile_value(profile, key)
                if resolved:
                    value = str(resolved)
                    source = "profile"
                elif entry.get("default") is not None:
                    value = str(entry["default"])
                    source = "default"

            # Common required-numeric heuristics that the regex map
            # doesn't catch precisely enough (LinkedIn phrasing varies).
            if value is None and label:
                ll = label.lower()
                if "years" in ll and "experience" in ll:
                    yrs = getattr(profile, "years_experience", None)
                    if yrs is not None:
                        value = str(yrs)
                        source = "heuristic"
                elif ("salary" in ll or "compensation" in ll) and (
                    "expect" in ll or "desired" in ll or "minimum" in ll
                ):
                    sal = self._extract_salary_target(job)
                    if sal:
                        value = sal
                        source = "heuristic"

            if value is None:
                logs.append(FormField(
                    label=label or f"<unlabeled {tag}#{i}>",
                    value="",
                    source="skipped",
                    confidence=0.0,
                ))
                continue

            # Fill / select / check based on tag/type.
            try:
                if tag == "select":
                    # ``select`` is the one case where keyboard typing
                    # doesn't apply — use select_option with the label
                    # match. If that fails, log skip.
                    try:
                        await f.select_option(label=value)
                    except Exception:  # noqa: BLE001
                        try:
                            await f.select_option(value=value)
                        except Exception:  # noqa: BLE001
                            logs.append(FormField(
                                label=label or "",
                                value=value,
                                source="skipped",
                                confidence=0.3,
                            ))
                            continue
                elif input_type in ("checkbox",):
                    truthy = value.strip().lower() in ("yes", "true", "1", "on")
                    if truthy:
                        try:
                            if not await f.is_checked():
                                await _hover_and_click(f, rng)
                        except Exception:  # noqa: BLE001
                            await _hover_and_click(f, rng)
                else:
                    await _human_type(page, f, value, rng)
            except Exception as e:  # noqa: BLE001
                logger.warning("[easyapply] fill failed for %r: %s", label, e)
                logs.append(FormField(
                    label=label or "",
                    value=value,
                    source="skipped",
                    confidence=0.0,
                ))
                continue

            logs.append(FormField(
                label=label or "",
                value=value,
                source=source,
                confidence=1.0 if source == "profile" else 0.7,
            ))
            # Inter-field micro-pause to avoid the "filled 12 inputs in
            # 200ms" fingerprint.
            await asyncio.sleep(rng.uniform(0.12, 0.45))

        return logs

    async def _field_label(self, page: Page, field_loc: Locator) -> str:
        """Best-effort label resolution. LinkedIn forms generally pair
        ``<label for=id>`` with the input; falls back to aria-label,
        placeholder, and parent text."""

        for fn in (
            lambda: field_loc.get_attribute("aria-label"),
            lambda: field_loc.get_attribute("placeholder"),
            lambda: field_loc.get_attribute("name"),
        ):
            try:
                v = await fn()
                if v:
                    return v.strip()
            except Exception:  # noqa: BLE001
                continue
        # <label for=id>
        try:
            fid = await field_loc.get_attribute("id")
            if fid:
                lbl = page.locator(f"label[for='{fid}']").first
                if await lbl.count() > 0:
                    txt = (await lbl.inner_text()).strip()
                    if txt:
                        return txt
        except Exception:  # noqa: BLE001
            pass
        # Nearest ancestor label.
        try:
            txt = await field_loc.evaluate(
                "el => { const l = el.closest('label'); return l ? l.innerText : ''; }"
            )
            if txt:
                return str(txt).strip()
        except Exception:  # noqa: BLE001
            pass
        return ""

    async def _handle_resume_radio(
        self,
        radio: Locator,
        label: str,
        profile,
        rng: random.Random,
    ) -> Optional[FormField]:
        """Easy Apply often pre-loads previously-uploaded resumes as a
        radio group. We match by filename prefix against the operator's
        configured resume; if no prefix match, default to the first
        option (already-checked is fine)."""

        try:
            already_checked = await radio.is_checked()
        except Exception:  # noqa: BLE001
            already_checked = False

        target_name = ""
        resume_path = getattr(profile, "resume_file", None) or getattr(profile, "resume_path", None)
        if resume_path:
            target_name = Path(str(resume_path)).stem.lower()

        label_lo = (label or "").lower()
        match = bool(target_name) and target_name in label_lo

        if match or (not already_checked and target_name == ""):
            try:
                await _hover_and_click(radio, rng)
                return FormField(
                    label=f"resume_radio:{label}",
                    value=target_name or "<first>",
                    source="heuristic" if match else "default",
                    confidence=0.9 if match else 0.5,
                )
            except Exception as e:  # noqa: BLE001
                logger.warning("[easyapply] resume radio click failed: %s", e)
        if already_checked:
            return FormField(
                label=f"resume_radio:{label}",
                value="<pre-selected>",
                source="default",
                confidence=0.6,
            )
        return None

    # ---- jd-derived heuristics ---------------------------------------

    def _extract_salary_target(self, job) -> Optional[str]:
        """Pull a salary number from ``job.salary_range`` if present.

        We aim for the midpoint of any "$X - $Y" string; falling back
        to the first number we see. This is intentionally conservative —
        an over-eager salary fill is worse than skipping the field."""

        raw = getattr(job, "salary_range", None) or getattr(job, "salary", None)
        if not raw:
            return None
        s = str(raw)
        nums = re.findall(r"(\d{2,3}(?:[,_.]\d{3})*(?:\.\d+)?)", s.replace("$", ""))
        if not nums:
            return None
        try:
            ints = [int(re.sub(r"[,_.]", "", n).split(".")[0]) for n in nums]
        except Exception:  # noqa: BLE001
            return None
        if not ints:
            return None
        # If two numbers, return midpoint; otherwise the first.
        if len(ints) >= 2:
            mid = (ints[0] + ints[1]) // 2
            return str(mid)
        return str(ints[0])
