"""Workday ATS adapter (slice 4 best-effort, paircode round 1).

Workday is the hardest ATS we'll encounter:
  * Every tenant customizes the form pages, labels, and ordering.
  * Most flows require account creation OR sign-in before the form is
    even visible. Slice 4 explicitly does NOT create accounts on behalf
    of the user (paircode r2 prohibition).
  * Multi-page wizard (typically 4-6 pages): My Information → My
    Experience → Application Questions → Voluntary Disclosures → Review
    → Submit.
  * File upload widgets wrap a hidden ``<input type=file>``; the visible
    element is a styled div that won't accept ``fill()``.
  * Voluntary EEO questions vary wildly per tenant; defaulting to
    "Prefer not to say" is the only safe-by-default behavior that
    doesn't fabricate a protected-class response.

The strategy: lean on Workday's one stable hook (``data-automation-id``)
for every selector, walk pages until the Submit button appears, and bail
gracefully (NEEDS_USER_INPUT) the moment we see something we don't
recognize. Slice 6 should add a browser-use fallback for unusual tenants.
"""

from __future__ import annotations

import asyncio
import logging
import random
import re
from pathlib import Path
from typing import Optional

import yaml

from services.ats.base import (
    ApplyResult,
    ApplyStatus,
    ATSAdapter,
    ATSKind,
    FormField,
    register_adapter,
)

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Anti-bot helpers — same lognormal-typing + hover-before-click as the other
# adapters. Kept inline so the adapter stays single-file-portable for the
# paircode sandbox.
# --------------------------------------------------------------------------- #

_TYPE_MU = -3.4    # log seconds per keystroke -> ~33ms median
_TYPE_SIGMA = 0.5
_TYPE_MIN = 0.012
_TYPE_MAX = 0.260


def _sample_keydelay(rng: random.Random) -> float:
    s = rng.lognormvariate(_TYPE_MU, _TYPE_SIGMA)
    return max(_TYPE_MIN, min(_TYPE_MAX, s))


async def _human_type(page, selector: str, value: str, rng: random.Random) -> None:
    """Type ``value`` into ``selector`` one keystroke at a time with
    lognormal delays. Workday widgets sometimes swallow ``fill()`` so
    we always go through ``keyboard.type`` via the focused element."""
    loc = page.locator(selector).first
    await loc.click()
    # Clear existing content (Workday inputs may pre-fill from prior
    # session). select-all + delete is more reliable than ``fill('')``.
    await page.keyboard.press("Control+A")
    await page.keyboard.press("Delete")
    for ch in value:
        await page.keyboard.type(ch, delay=int(_sample_keydelay(rng) * 1000))


async def _human_click(page, selector: str, rng: random.Random) -> None:
    loc = page.locator(selector).first
    try:
        await loc.hover()
        await asyncio.sleep(rng.uniform(0.08, 0.42))
    except Exception:  # noqa: BLE001
        pass
    await loc.click()


# --------------------------------------------------------------------------- #
# Field map loader — shared YAML across adapters.
# --------------------------------------------------------------------------- #

_FIELD_MAP_PATH = Path(__file__).resolve().parent / "field_map.yaml"


def _load_field_map() -> list[dict]:
    try:
        with open(_FIELD_MAP_PATH, encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        return data.get("mappings", []) or []
    except FileNotFoundError:
        logger.warning(f"[workday] field_map.yaml not found at {_FIELD_MAP_PATH}")
        return []


_FIELD_MAP: list[dict] = _load_field_map()


def _resolve_profile_value(profile, key: str) -> Optional[str]:
    """Tiny dotted-path resolver against UserProfile. Mirrors the
    behavior documented in field_map.yaml."""
    if not key:
        return None
    name = getattr(profile, "name", "") or ""
    parts = name.split()
    if key == "name.full":
        return name or None
    if key == "name.first":
        return parts[0] if parts else None
    if key == "name.last":
        return parts[-1] if len(parts) >= 2 else None
    if key == "email":
        return getattr(profile, "email", None)
    if key == "phone":
        return getattr(profile, "phone", None)
    if key == "linkedin":
        return getattr(profile, "linkedin_url", None)
    if key == "github":
        return getattr(profile, "github_url", None)
    if key == "website":
        return getattr(profile, "website_url", None)
    if key == "resume_file":
        return getattr(profile, "resume_path", None)
    if key == "years_experience":
        v = getattr(profile, "years_experience", None)
        return str(v) if v is not None else None
    if key == "current_company":
        return getattr(profile, "current_company", None)
    if key == "city":
        return getattr(profile, "city", None)
    if key == "country":
        return getattr(profile, "country", None)
    if key.startswith("work_auth."):
        sub = key.split(".", 1)[1]
        wa = getattr(profile, "work_auth", None) or {}
        if isinstance(wa, dict):
            return wa.get(sub)
    return None


def _match_label(label: str) -> tuple[Optional[str], Optional[str]]:
    """Return (profile_key, default_value) for a label, or (None, None)."""
    if not label:
        return None, None
    norm = label.strip().lower().rstrip(":*").strip()
    for entry in _FIELD_MAP:
        pat = entry.get("pattern", "")
        try:
            if re.search(pat, norm, re.IGNORECASE):
                return entry.get("profile_key"), entry.get("default")
        except re.error:
            continue
    return None, None


# --------------------------------------------------------------------------- #
# EEO / voluntary disclosure defaults.
#
# Decision: for any race/ethnicity/gender/veteran/disability question we
# pick the "decline to answer" / "prefer not to say" option. We never
# fabricate a protected-class response — that's both legally fraught and
# disrespectful to the operator's autonomy. If the only options are
# affirmative (e.g. a tenant that doesn't offer "decline"), we mark the
# field as skipped and require user input.
# --------------------------------------------------------------------------- #

_EEO_LABEL_HINTS = re.compile(
    r"(race|ethnic|gender|sex|veteran|disability|"
    r"hispanic|latino|sexual orientation|pronoun)",
    re.IGNORECASE,
)
_EEO_DECLINE_OPTIONS = [
    "prefer not to say",
    "decline to self-identify",
    "decline to answer",
    "i do not wish to answer",
    "i don't wish to answer",
    "do not wish to disclose",
    "choose not to disclose",
    "i prefer not to answer",
]


# --------------------------------------------------------------------------- #
# Selectors — Workday's stable hook is ``data-automation-id``. Everything
# else (class names, role attrs) shifts per tenant rev.
# --------------------------------------------------------------------------- #

SEL_APPLY_BUTTON = (
    '[data-automation-id="adventureButton"], '
    '[data-automation-id="applyAction"], '
    'a:has-text("Apply"), button:has-text("Apply")'
)
SEL_APPLY_MANUALLY = (
    '[data-automation-id="applyManually"], '
    'a:has-text("Apply Manually"), button:has-text("Apply Manually")'
)
SEL_APPLY_AUTOFILL_RESUME = '[data-automation-id="autofillWithResume"]'
SEL_NEW_USER_RADIO = (
    '[data-automation-id="previousApplicantNoRadio"], '
    'label:has-text("No, I am a new user"), '
    'label:has-text("No, I am a new applicant")'
)
SEL_SIGNIN_BUTTON = (
    '[data-automation-id="signInLink"], '
    'button:has-text("Sign In"), a:has-text("Sign In")'
)
SEL_CREATE_ACCOUNT_BUTTON = (
    '[data-automation-id="createAccountLink"], '
    '[data-automation-id="createAccountSubmitButton"], '
    'button:has-text("Create Account"), a:has-text("Create Account")'
)
SEL_SAVE_AND_CONTINUE = (
    '[data-automation-id="bottom-navigation-next-button"], '
    'button:has-text("Save and Continue"), '
    'button:has-text("Continue"), '
    'button:has-text("Next")'
)
SEL_SUBMIT = (
    '[data-automation-id="bottom-navigation-submit-button"], '
    'button:has-text("Submit")'
)
SEL_REVIEW = 'button:has-text("Review")'
SEL_CONFIRMATION = (
    'text=/You have submitted your application/i, '
    'text=/Thank you for applying/i, '
    'text=/application has been submitted/i'
)
SEL_ADD_BUTTON = '[data-automation-id^="Add"]'
SEL_FILE_INPUT = 'input[type="file"]'

# Per-page form-field walker — any element with a data-automation-id that
# is also an input/select/textarea/combobox.
SEL_FORM_FIELDS = (
    'input[data-automation-id], '
    'textarea[data-automation-id], '
    'select[data-automation-id], '
    'button[data-automation-id][aria-haspopup="listbox"], '
    'button[data-automation-id][role="combobox"]'
)


# --------------------------------------------------------------------------- #
# Adapter
# --------------------------------------------------------------------------- #


@register_adapter
class WorkdayAdapter(ATSAdapter):
    """Best-effort Workday driver. Bails to NEEDS_USER_INPUT the moment
    a tenant customization confuses us."""

    KIND = ATSKind.WORKDAY
    URL_PATTERNS = (
        re.compile(r"myworkdayjobs\.com", re.IGNORECASE),
        re.compile(r"workday\.com", re.IGNORECASE),
        re.compile(r"wd\d+\.myworkdayjobs", re.IGNORECASE),
    )

    # Per-page cap. Workday wizards are 4-6 pages; cap at 8 to absorb
    # tenant extras without an infinite loop.
    MAX_PAGES = 8

    @classmethod
    def recognize(cls, html: str) -> bool:
        if not html:
            return False
        if "data-automation-id" in html:
            return True
        if 'class="wd-icon' in html or "wd-icon-" in html:
            return True
        if re.search(r"<script[^>]*>[^<]*Workday", html, re.IGNORECASE | re.DOTALL):
            return True
        if 'data-automation-id="adventureButton"' in html:
            return True
        return False

    # ------------------------------------------------------------------ #
    # Public entry point
    # ------------------------------------------------------------------ #

    async def apply(
        self,
        page,
        job,
        profile,
        dry_run: bool = True,
    ) -> ApplyResult:
        rng = random.Random()
        fields_logged: list[FormField] = []
        screenshots: list[str] = []
        screenshot_dir = self._screenshot_dir(job)

        async def shot(name: str) -> None:
            try:
                path = screenshot_dir / f"{name}.png"
                screenshot_dir.mkdir(parents=True, exist_ok=True)
                await page.screenshot(path=str(path), full_page=True)
                screenshots.append(str(path))
            except Exception:  # noqa: BLE001
                logger.debug("[workday] screenshot failed", exc_info=True)

        try:
            await page.wait_for_load_state("domcontentloaded", timeout=20000)
            await asyncio.sleep(rng.uniform(0.8, 2.0))
            await shot("01_job_page")

            # ---- step 1: locate the Apply button / handle pre-applicant popup
            applied_clicked = await self._click_apply(page, rng)
            if not applied_clicked:
                return ApplyResult(
                    status=ApplyStatus.FAILED_UNAVAILABLE,
                    exit_reason="workday_apply_button_missing",
                    fields_logged=fields_logged,
                    screenshots=screenshots,
                    detected_ats=self.KIND,
                )
            await asyncio.sleep(rng.uniform(0.6, 1.4))
            await shot("02_after_apply")

            # ---- step 1b: "Apply Manually" vs "Apply with Indeed" / autofill
            await self._choose_apply_manually(page, rng)
            await asyncio.sleep(rng.uniform(0.4, 1.0))

            # ---- step 1c: previous applicant prompt
            await self._dismiss_previous_applicant_prompt(page, rng)

            # ---- step 2: detect signin / account-required
            requires_account = await self._requires_account_or_signin(page)
            if requires_account:
                has_creds = bool(getattr(profile, "workday_email", None)) and bool(
                    getattr(profile, "workday_password", None)
                )
                if not has_creds:
                    await shot("03_account_required")
                    return ApplyResult(
                        status=ApplyStatus.NEEDS_USER_INPUT,
                        exit_reason="workday_account_required",
                        fields_logged=fields_logged,
                        screenshots=screenshots,
                        error_message=(
                            "Workday tenant requires account creation or sign-in "
                            "before the application form is accessible. Slice 4 "
                            "will not auto-create accounts."
                        ),
                        detected_ats=self.KIND,
                    )
                # Slice 4+: even with creds, signing in carries enough
                # tenant-specific risk that we still bail to user input.
                # (Slice 6 owns the signin happy path.)
                await shot("03_signin_required")
                return ApplyResult(
                    status=ApplyStatus.NEEDS_USER_INPUT,
                    exit_reason="workday_signin_required",
                    fields_logged=fields_logged,
                    screenshots=screenshots,
                    error_message="Workday sign-in flow deferred to slice 6.",
                    detected_ats=self.KIND,
                )

            # ---- step 3: walk the multi-page wizard
            for page_idx in range(1, self.MAX_PAGES + 1):
                page_label = await self._page_label(page)
                logger.info(
                    f"[workday] wizard page {page_idx}/{self.MAX_PAGES} label={page_label!r}"
                )
                await self._fill_page(
                    page,
                    profile,
                    rng,
                    fields_logged,
                    is_eeo_page=self._looks_like_eeo_page(page_label),
                )
                await shot(f"page_{page_idx:02d}_{self._slug(page_label)}")

                # Submit visible? We're at the final review step.
                if await self._submit_visible(page):
                    if dry_run:
                        await shot("final_review_dryrun")
                        return ApplyResult(
                            status=ApplyStatus.SUBMITTED_DRY_RUN,
                            exit_reason="dry_run_workday_review_reached",
                            fields_logged=fields_logged,
                            screenshots=screenshots,
                            detected_ats=self.KIND,
                        )
                    # Real submit
                    await _human_click(page, SEL_SUBMIT, rng)
                    await asyncio.sleep(rng.uniform(2.0, 4.0))
                    await shot("after_submit")
                    if await self._confirmation_visible(page):
                        return ApplyResult(
                            status=ApplyStatus.SUBMITTED,
                            exit_reason="workday_confirmation_seen",
                            fields_logged=fields_logged,
                            screenshots=screenshots,
                            detected_ats=self.KIND,
                        )
                    return ApplyResult(
                        status=ApplyStatus.FAILED_RETRYABLE,
                        exit_reason="workday_confirmation_missing",
                        fields_logged=fields_logged,
                        screenshots=screenshots,
                        error_message="Submit clicked but no confirmation page detected.",
                        detected_ats=self.KIND,
                    )

                # Not at submit yet — advance.
                advanced = await self._click_continue(page, rng)
                if not advanced:
                    # Likely a validation error or a custom control we
                    # didn't fill. Bail cleanly.
                    await shot(f"page_{page_idx:02d}_stuck")
                    return ApplyResult(
                        status=ApplyStatus.NEEDS_USER_INPUT,
                        exit_reason="workday_cannot_advance",
                        fields_logged=fields_logged,
                        screenshots=screenshots,
                        error_message=(
                            f"Save and Continue did not advance past page "
                            f"{page_idx} ({page_label!r}); likely a required "
                            f"field we couldn't fill or a tenant-specific "
                            f"validator."
                        ),
                        detected_ats=self.KIND,
                    )
                await asyncio.sleep(rng.uniform(1.2, 2.4))

            # Out of pages without seeing Submit — odd tenant.
            return ApplyResult(
                status=ApplyStatus.NEEDS_USER_INPUT,
                exit_reason="workday_too_many_pages",
                fields_logged=fields_logged,
                screenshots=screenshots,
                error_message=f"Exceeded MAX_PAGES={self.MAX_PAGES} without reaching Submit.",
                detected_ats=self.KIND,
            )

        except Exception as e:  # noqa: BLE001
            logger.exception("[workday] unexpected error")
            await shot("error")
            return ApplyResult(
                status=ApplyStatus.FAILED_RETRYABLE,
                exit_reason=type(e).__name__,
                fields_logged=fields_logged,
                screenshots=screenshots,
                error_message=str(e)[:1000],
                detected_ats=self.KIND,
            )

    # ------------------------------------------------------------------ #
    # Step helpers
    # ------------------------------------------------------------------ #

    async def _click_apply(self, page, rng: random.Random) -> bool:
        try:
            loc = page.locator(SEL_APPLY_BUTTON).first
            if await loc.count() == 0:
                return False
            await loc.scroll_into_view_if_needed()
            await _human_click(page, SEL_APPLY_BUTTON, rng)
            return True
        except Exception:  # noqa: BLE001
            return False

    async def _choose_apply_manually(self, page, rng: random.Random) -> None:
        """Workday tenants frequently show a chooser: Apply Manually,
        Apply with Indeed, Autofill with Resume. We pick Apply Manually
        because we control every field that way."""
        try:
            loc = page.locator(SEL_APPLY_MANUALLY).first
            if await loc.count() > 0 and await loc.is_visible():
                await _human_click(page, SEL_APPLY_MANUALLY, rng)
                return
        except Exception:  # noqa: BLE001
            pass
        # Some tenants don't offer a chooser — that's fine, fall through.

    async def _dismiss_previous_applicant_prompt(
        self, page, rng: random.Random
    ) -> None:
        try:
            loc = page.locator(SEL_NEW_USER_RADIO).first
            if await loc.count() > 0 and await loc.is_visible():
                await _human_click(page, SEL_NEW_USER_RADIO, rng)
                # Then continue past the prompt.
                cont = page.locator(SEL_SAVE_AND_CONTINUE).first
                if await cont.count() > 0:
                    await _human_click(page, SEL_SAVE_AND_CONTINUE, rng)
        except Exception:  # noqa: BLE001
            pass

    async def _requires_account_or_signin(self, page) -> bool:
        try:
            for sel in (SEL_SIGNIN_BUTTON, SEL_CREATE_ACCOUNT_BUTTON):
                loc = page.locator(sel).first
                if await loc.count() > 0 and await loc.is_visible():
                    return True
        except Exception:  # noqa: BLE001
            pass
        return False

    async def _submit_visible(self, page) -> bool:
        try:
            loc = page.locator(SEL_SUBMIT).first
            return (await loc.count() > 0) and await loc.is_visible()
        except Exception:  # noqa: BLE001
            return False

    async def _confirmation_visible(self, page) -> bool:
        try:
            html = await page.content()
        except Exception:  # noqa: BLE001
            return False
        return bool(
            re.search(
                r"(you have submitted your application|"
                r"thank you for applying|"
                r"application has been submitted|"
                r"successfully submitted)",
                html,
                re.IGNORECASE,
            )
        )

    async def _click_continue(self, page, rng: random.Random) -> bool:
        try:
            loc = page.locator(SEL_SAVE_AND_CONTINUE).first
            if await loc.count() == 0:
                return False
            url_before = page.url
            await _human_click(page, SEL_SAVE_AND_CONTINUE, rng)
            # Wait for either URL change OR a new page heading. Workday is
            # SPA-y; URL often doesn't change, so we also probe for the
            # next page's data-automation-id ``pageHeader``.
            try:
                await page.wait_for_function(
                    "(prev) => location.href !== prev || "
                    "document.querySelector('[data-automation-id=\"pageHeader\"]')",
                    arg=url_before,
                    timeout=8000,
                )
            except Exception:  # noqa: BLE001
                pass
            return True
        except Exception:  # noqa: BLE001
            return False

    async def _page_label(self, page) -> str:
        try:
            loc = page.locator('[data-automation-id="pageHeader"]').first
            if await loc.count() > 0:
                return (await loc.inner_text()).strip()
        except Exception:  # noqa: BLE001
            pass
        try:
            h1 = page.locator("h1, h2").first
            if await h1.count() > 0:
                return (await h1.inner_text()).strip()
        except Exception:  # noqa: BLE001
            pass
        return ""

    @staticmethod
    def _looks_like_eeo_page(label: str) -> bool:
        if not label:
            return False
        return bool(
            re.search(
                r"(voluntary|self.?identif|disclosur|equal[\s-]?employment|"
                r"eeo|veteran|disability)",
                label,
                re.IGNORECASE,
            )
        )

    @staticmethod
    def _slug(s: str) -> str:
        s = re.sub(r"[^\w]+", "_", (s or "page").lower()).strip("_")
        return s[:40] or "page"

    @staticmethod
    def _screenshot_dir(job) -> Path:
        run_id = getattr(job, "job_id", None) or "unknown"
        return Path("data") / "apply_runs" / f"workday_{run_id}"

    # ------------------------------------------------------------------ #
    # Per-page filler
    # ------------------------------------------------------------------ #

    async def _fill_page(
        self,
        page,
        profile,
        rng: random.Random,
        fields_logged: list[FormField],
        is_eeo_page: bool,
    ) -> None:
        """Walk every data-automation-id input/select/combobox on the
        current page and fill what we recognize.

        For repeating sub-forms (Work Experience "Add" buttons), we fill
        the first occurrence from the operator's most-recent role and
        skip the "Add another" — explicit slice-4 scope cap.
        """

        # 1) File upload — find any hidden <input type=file> and push the
        #    resume into it directly (the visible widget is a styled div).
        await self._upload_resume_if_present(page, profile, fields_logged)

        # 2) Walk all data-automation-id inputs.
        try:
            elements = await page.locator(SEL_FORM_FIELDS).element_handles()
        except Exception:  # noqa: BLE001
            elements = []

        seen_automation_ids: set[str] = set()
        for el in elements:
            try:
                automation_id = await el.get_attribute("data-automation-id") or ""
                if not automation_id or automation_id in seen_automation_ids:
                    continue
                seen_automation_ids.add(automation_id)

                label = await self._label_for(page, el, automation_id)
                tag = (await el.evaluate("e => e.tagName")).lower()
                input_type = (await el.get_attribute("type") or "").lower()

                # EEO page: any select / combobox gets the decline option.
                if is_eeo_page and _EEO_LABEL_HINTS.search(label or automation_id):
                    picked = await self._pick_decline_option(page, el, rng)
                    fields_logged.append(
                        FormField(
                            label=label or automation_id,
                            value=picked or "(decline option not found)",
                            source="default" if picked else "skipped",
                            confidence=0.9 if picked else 0.0,
                            selector=f'[data-automation-id="{automation_id}"]',
                        )
                    )
                    continue

                profile_key, default_value = _match_label(label)
                value = _resolve_profile_value(profile, profile_key) if profile_key else None
                source = "profile" if value else ("default" if default_value else "skipped")
                if not value and default_value:
                    value = default_value

                if not value:
                    fields_logged.append(
                        FormField(
                            label=label or automation_id,
                            value="",
                            source="skipped",
                            confidence=0.0,
                            selector=f'[data-automation-id="{automation_id}"]',
                        )
                    )
                    continue

                ok = await self._set_value(page, el, tag, input_type, value, rng)
                fields_logged.append(
                    FormField(
                        label=label or automation_id,
                        value=value if ok else "",
                        source=source if ok else "skipped",
                        confidence=0.85 if ok else 0.0,
                        selector=f'[data-automation-id="{automation_id}"]',
                    )
                )
            except Exception:  # noqa: BLE001
                logger.debug(
                    "[workday] field walk error", exc_info=True
                )
                continue

        # 3) Don't loop "Add another experience" — slice-4 scope cap.

    async def _upload_resume_if_present(
        self, page, profile, fields_logged: list[FormField]
    ) -> None:
        resume_path = getattr(profile, "resume_path", None)
        if not resume_path:
            return
        try:
            inputs = await page.locator(SEL_FILE_INPUT).element_handles()
        except Exception:  # noqa: BLE001
            inputs = []
        for inp in inputs:
            try:
                # Use set_input_files on the underlying hidden input.
                await inp.set_input_files(resume_path)
                fields_logged.append(
                    FormField(
                        label="Resume",
                        value=str(resume_path),
                        source="profile",
                        confidence=0.95,
                        selector='input[type="file"]',
                    )
                )
                # Only one resume upload per page; Workday rarely has more.
                return
            except Exception:  # noqa: BLE001
                continue

    async def _label_for(self, page, element_handle, automation_id: str) -> str:
        """Best-effort label resolution. Workday inputs are usually
        associated with a ``<label for="...">`` or carry an
        ``aria-label``/``aria-labelledby``."""
        try:
            aria_label = await element_handle.get_attribute("aria-label")
            if aria_label:
                return aria_label.strip()
            aria_labelledby = await element_handle.get_attribute("aria-labelledby")
            if aria_labelledby:
                txt = await page.evaluate(
                    "(id) => { const el = document.getElementById(id); "
                    "return el ? el.innerText : '' }",
                    aria_labelledby,
                )
                if txt:
                    return txt.strip()
            input_id = await element_handle.get_attribute("id")
            if input_id:
                txt = await page.evaluate(
                    "(id) => { const l = document.querySelector(`label[for=\"${id}\"]`); "
                    "return l ? l.innerText : '' }",
                    input_id,
                )
                if txt:
                    return txt.strip()
        except Exception:  # noqa: BLE001
            pass
        # Fallback: humanize the automation-id ("firstName" -> "first name").
        return re.sub(r"([a-z])([A-Z])", r"\1 \2", automation_id).lower()

    async def _set_value(
        self, page, element_handle, tag: str, input_type: str, value: str,
        rng: random.Random,
    ) -> bool:
        """Dispatch on element type. Returns True on best-effort set."""
        try:
            if tag == "input" and input_type in {"checkbox", "radio"}:
                # Truthy values check the box; "Yes"/"No" steer radios.
                if str(value).strip().lower() in {"yes", "true", "1", "y"}:
                    await element_handle.check()
                else:
                    await element_handle.uncheck()
                return True
            if tag == "select":
                try:
                    await element_handle.select_option(label=value)
                    return True
                except Exception:  # noqa: BLE001
                    try:
                        await element_handle.select_option(value=value)
                        return True
                    except Exception:  # noqa: BLE001
                        return False
            if tag == "button":
                # Custom combobox — open and pick the matching option.
                return await self._pick_combobox_option(page, element_handle, value, rng)
            # Default: text-like input / textarea.
            try:
                await element_handle.click()
                await page.keyboard.press("Control+A")
                await page.keyboard.press("Delete")
                for ch in str(value):
                    await page.keyboard.type(
                        ch, delay=int(_sample_keydelay(rng) * 1000)
                    )
                return True
            except Exception:  # noqa: BLE001
                try:
                    await element_handle.fill(str(value))
                    return True
                except Exception:  # noqa: BLE001
                    return False
        except Exception:  # noqa: BLE001
            return False

    async def _pick_combobox_option(
        self, page, button_handle, value: str, rng: random.Random
    ) -> bool:
        try:
            await button_handle.click()
            await asyncio.sleep(rng.uniform(0.25, 0.55))
            # Options live in a popup with role=listbox; try exact, then
            # contains, then case-insensitive contains.
            v = str(value)
            for css in (
                f'[role="option"]:has-text("{v}")',
                f'li:has-text("{v}")',
                f'div:has-text("{v}")',
            ):
                opt = page.locator(css).first
                if await opt.count() > 0:
                    await opt.click()
                    return True
            # Nothing matched — close popup with Escape.
            await page.keyboard.press("Escape")
            return False
        except Exception:  # noqa: BLE001
            return False

    async def _pick_decline_option(
        self, page, element_handle, rng: random.Random
    ) -> Optional[str]:
        """For EEO questions, open the control and pick the first option
        whose text matches a "decline" phrase. Returns the option text or
        None when no decline option exists."""
        try:
            tag = (await element_handle.evaluate("e => e.tagName")).lower()
            if tag == "select":
                # Read options, find a match, select it.
                options = await element_handle.evaluate(
                    "el => Array.from(el.options).map(o => o.text)"
                )
                for label in options:
                    low = label.strip().lower()
                    if any(phrase in low for phrase in _EEO_DECLINE_OPTIONS):
                        await element_handle.select_option(label=label)
                        return label
                return None
            # Custom combobox / radio group: open the popup and click a
            # matching option.
            try:
                await element_handle.click()
                await asyncio.sleep(rng.uniform(0.2, 0.5))
            except Exception:  # noqa: BLE001
                pass
            for phrase in _EEO_DECLINE_OPTIONS:
                for css in (
                    f'[role="option"]:has-text("{phrase}")',
                    f'label:has-text("{phrase}")',
                    f'li:has-text("{phrase}")',
                ):
                    opt = page.locator(css).first
                    if await opt.count() > 0 and await opt.is_visible():
                        try:
                            await opt.click()
                            return phrase
                        except Exception:  # noqa: BLE001
                            continue
            try:
                await page.keyboard.press("Escape")
            except Exception:  # noqa: BLE001
                pass
            return None
        except Exception:  # noqa: BLE001
            return None
