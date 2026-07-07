"""Ashby ATS adapter.

Ashby (https://ashbyhq.com) is the youngest of the three big modern
ATSes (Greenhouse / Lever / Ashby) and it shows: the apply form is a
React app, the DOM is verbose but very accessible — almost every input
has a proper ``aria-label`` and a real ``<label>`` wired up with
``htmlFor``. That a11y discipline is what we lean on.

Posting URLs:
  * https://jobs.ashbyhq.com/{org}/{posting-id}
  * https://{org}.ashbyhq.com/jobs/{posting-id}  (custom-subdomain variant)

Both render the same component tree. The apply form sometimes lives on
the same page (an expanding panel), sometimes at /application. We
handle both by looking for an "Apply" CTA and following it if present.

Submission flow:
  * One CTA: "Submit application" (sometimes "Submit Application").
  * Confirmation: a modal or full page replacement with
    "Thank you for applying" — we look for both URL change and text.
"""

from __future__ import annotations

import asyncio
import logging
import math
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


# --- humanized typing ---------------------------------------------------------

_TYPE_MU = math.log(0.080)
_TYPE_SIGMA = 0.5
_TYPE_MIN_MS = 25
_TYPE_MAX_MS = 450


def _sample_delay_ms(rng: random.Random | None = None) -> int:
    rng = rng or random.Random()
    s = rng.lognormvariate(_TYPE_MU, _TYPE_SIGMA) * 1000.0
    return int(max(_TYPE_MIN_MS, min(_TYPE_MAX_MS, s)))


async def _human_type(page, selector: str, text: str) -> None:
    loc = page.locator(selector).first
    await loc.scroll_into_view_if_needed()
    await loc.hover()
    await loc.click()
    # React-controlled inputs: select-all + backspace is the safe wipe.
    await page.keyboard.press("Meta+A")
    await page.keyboard.press("Backspace")
    for ch in text:
        await page.keyboard.type(ch, delay=_sample_delay_ms())


# --- field map ---------------------------------------------------------------

_FIELD_MAP_PATH = Path(__file__).resolve().parent / "field_map.yaml"


def _load_field_map() -> list[dict]:
    try:
        with _FIELD_MAP_PATH.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return data.get("mappings", []) or []
    except Exception:  # noqa: BLE001
        logger.warning("[ashby] could not load field_map.yaml", exc_info=True)
        return []


_FIELD_MAP = _load_field_map()


def _match_field(label: str) -> tuple[Optional[str], Optional[str]]:
    cleaned = re.sub(r"[\*\(\):]+", "", label or "").strip().lower()
    for m in _FIELD_MAP:
        pat = m.get("pattern")
        if not pat:
            continue
        try:
            if re.search(pat, cleaned, flags=re.IGNORECASE):
                return m.get("profile_key"), m.get("default")
        except re.error:
            continue
    return None, None


def _resolve_profile_value(profile, key: str) -> Optional[str]:
    if not key:
        return None
    name = (getattr(profile, "name", "") or "").strip()
    parts = name.split() if name else []
    table = {
        "name.first": parts[0] if parts else "",
        "name.last": parts[-1] if len(parts) > 1 else "",
        "name.full": name,
        "email": getattr(profile, "email", "") or "",
        "phone": getattr(profile, "phone", "") or "",
        "linkedin": getattr(profile, "linkedin_url", "") or "",
        "github": getattr(profile, "github_url", "") or "",
        "website": getattr(profile, "website", "") or "",
        "resume_file": getattr(profile, "resume_path", "") or "",
        "years_experience": str(getattr(profile, "years_experience", "") or ""),
        "current_company": getattr(profile, "current_company", "") or "",
        "city": getattr(profile, "city", "") or "",
        "country": getattr(profile, "country", "") or "",
        "work_auth.yes_no": getattr(profile, "work_authorized", "") or "",
        "work_auth.needs_sponsorship": getattr(profile, "needs_sponsorship", "") or "",
    }
    val = table.get(key, "")
    return val if val else None


# --- adapter ------------------------------------------------------------------


@register_adapter
class AshbyAdapter(ATSAdapter):
    """Ashby-hosted job postings."""

    KIND = ATSKind.ASHBY
    URL_PATTERNS = (
        re.compile(r"jobs\.ashbyhq\.com", re.IGNORECASE),
        # Covers both the {org}.ashbyhq.com/jobs/{id} subdomain variant
        # and any /{org}/jobs path layout. The single .* anchor handles
        # the empty-path case (i.e. the canonical subdomain URL where
        # there is no extra path segment before /jobs).
        re.compile(r"ashbyhq\.com[/\w.-]*/?jobs", re.IGNORECASE),
    )

    _DOM_MARKERS = (
        "ashby-job-posting",
        "__ASHBY_PRELOADED_STATE__",
        "ashby-job-posting-right-pane",
        "ashby-application-form",
        "ashbyhq.com",
        "data-testid=\"posting-",
    )

    @classmethod
    def recognize(cls, html: str) -> bool:
        if not html:
            return False
        snippet = html[:200_000]
        return any(marker in snippet for marker in cls._DOM_MARKERS)

    # --- apply ----------------------------------------------------------------

    async def apply(self, page, job, profile, dry_run: bool = True) -> ApplyResult:
        fields_logged: list[FormField] = []
        screenshots: list[str] = []
        screenshot_dir = Path("data") / "apply_runs" / "ashby_scratch"
        screenshot_dir.mkdir(parents=True, exist_ok=True)

        try:
            # 1. If we're on the JD pane, click the "Apply" CTA. Ashby
            #    sometimes expands the form in-place, sometimes routes to
            #    /application.
            cta = page.locator(
                "a:has-text('Apply for this Job'), a:has-text('Apply'), "
                "button:has-text('Apply for this Job'), button:has-text('Apply')"
            ).first
            try:
                if await cta.count() > 0 and "/application" not in (page.url or ""):
                    await cta.hover()
                    await cta.click()
                    await page.wait_for_load_state("domcontentloaded", timeout=10000)
            except Exception:  # noqa: BLE001
                pass

            # 2. Wait for the React form to settle.
            try:
                await page.wait_for_selector(
                    "form, [class*='ashby-application-form'], "
                    "[data-testid*='application-form'], "
                    "input[type='email']",
                    timeout=15000,
                )
            except Exception:  # noqa: BLE001
                return ApplyResult(
                    status=ApplyStatus.FAILED_RETRYABLE,
                    exit_reason="form_not_found",
                    detected_ats=self.KIND,
                    error_message="Ashby apply form did not render within 15s",
                )

            # Quick settle for any post-mount animations / lazy field renders.
            await asyncio.sleep(0.5)

            # 3. Walk fields.
            field_handles = await page.locator(
                "input:not([type='hidden']):not([type='submit']):not([type='button']), "
                "textarea, select, [role='combobox']"
            ).element_handles()

            cover_letter_required_unmet = False
            seen_selectors: set[str] = set()

            for handle in field_handles:
                try:
                    label_text = await self._label_for(page, handle)
                    input_type = (await handle.get_attribute("type") or "").lower()
                    name_attr = (await handle.get_attribute("name") or "").lower()
                    aria_required = (
                        await handle.get_attribute("aria-required")
                    ) == "true"
                    required = aria_required or await handle.evaluate(
                        "el => el.required === true"
                    )

                    # Build a stable selector. Prefer id (Ashby gives them
                    # GUIDs but they're unique within a render), then name,
                    # then aria-label.
                    el_id = await handle.get_attribute("id")
                    if el_id:
                        css = f"#{re.escape(el_id).replace(chr(92),'')}"
                        # Playwright doesn't like backslash escapes on ids
                        # with colons / brackets. Fall back to attribute
                        # selector when we detect special chars.
                        if any(c in el_id for c in ":[]./"):
                            css = f"[id='{el_id}']"
                    elif name_attr:
                        css = f"[name='{name_attr}']"
                    elif label_text:
                        css = f"[aria-label='{label_text}']"
                    else:
                        # Skip — can't build a stable selector.
                        continue

                    if css in seen_selectors:
                        continue
                    seen_selectors.add(css)

                    is_cover_letter = (
                        "cover letter" in label_text.lower()
                        or "coverletter" in name_attr
                    )

                    # File input (resume).
                    if input_type == "file":
                        resume_path = _resolve_profile_value(profile, "resume_file")
                        if resume_path and Path(resume_path).exists():
                            await handle.set_input_files(resume_path)
                            fields_logged.append(
                                FormField(
                                    label=label_text or "resume",
                                    value=resume_path,
                                    source="profile",
                                    selector=css,
                                )
                            )
                        else:
                            fields_logged.append(
                                FormField(
                                    label=label_text or "resume",
                                    value="",
                                    source="skipped",
                                    confidence=0.0,
                                    selector=css,
                                )
                            )
                            if required:
                                return ApplyResult(
                                    status=ApplyStatus.FAILED_RETRYABLE,
                                    exit_reason="missing_resume_file",
                                    fields_logged=fields_logged,
                                    detected_ats=self.KIND,
                                    error_message="Required resume input but profile.resume_path missing",
                                )
                        continue

                    if is_cover_letter:
                        if required:
                            cover_letter_required_unmet = True
                        fields_logged.append(
                            FormField(
                                label=label_text or "cover letter",
                                value="",
                                source="skipped",
                                confidence=0.0,
                                selector=css,
                            )
                        )
                        continue

                    profile_key, default = _match_field(label_text or name_attr)
                    value = _resolve_profile_value(profile, profile_key) if profile_key else None
                    if not value and default:
                        value = default

                    if not value:
                        fields_logged.append(
                            FormField(
                                label=label_text or name_attr or "(unlabeled)",
                                value="",
                                source="skipped",
                                confidence=0.0,
                                selector=css,
                            )
                        )
                        continue

                    tag = await handle.evaluate("el => el.tagName.toLowerCase()")

                    if tag == "select":
                        try:
                            await handle.select_option(label=value)
                        except Exception:  # noqa: BLE001
                            try:
                                await handle.select_option(value=value)
                            except Exception:  # noqa: BLE001
                                fields_logged.append(
                                    FormField(
                                        label=label_text,
                                        value=value,
                                        source="skipped",
                                        confidence=0.3,
                                        selector=css,
                                    )
                                )
                                continue
                        fields_logged.append(
                            FormField(
                                label=label_text,
                                value=value,
                                source="profile" if profile_key else "default",
                                selector=css,
                            )
                        )
                        continue

                    # Ashby custom dropdown (role=combobox): click, then
                    # click the matching option.
                    role = await handle.get_attribute("role")
                    if role == "combobox":
                        try:
                            await handle.hover()
                            await handle.click()
                            opt = page.locator(
                                f"[role='option']:has-text('{value}')"
                            ).first
                            await opt.wait_for(timeout=3000)
                            await opt.hover()
                            await opt.click()
                            fields_logged.append(
                                FormField(
                                    label=label_text,
                                    value=value,
                                    source="profile" if profile_key else "default",
                                    selector=css,
                                )
                            )
                        except Exception:  # noqa: BLE001
                            fields_logged.append(
                                FormField(
                                    label=label_text,
                                    value=value,
                                    source="skipped",
                                    confidence=0.3,
                                    selector=css,
                                )
                            )
                        continue

                    if input_type in {"checkbox", "radio"}:
                        if value.lower() in {"yes", "true", "1", "y"}:
                            await handle.check()
                        fields_logged.append(
                            FormField(
                                label=label_text,
                                value=value,
                                source="profile" if profile_key else "default",
                                selector=css,
                            )
                        )
                        continue

                    # Plain text / email / url / tel / textarea.
                    await _human_type(page, css, value)
                    fields_logged.append(
                        FormField(
                            label=label_text,
                            value=value,
                            source="profile" if profile_key else "default",
                            selector=css,
                        )
                    )

                except Exception as e:  # noqa: BLE001
                    logger.warning(f"[ashby] field walk error: {e}", exc_info=True)
                    continue

            # 4. Parsed-form screenshot.
            parsed_png = screenshot_dir / "form_parsed.png"
            try:
                await page.screenshot(path=str(parsed_png), full_page=True)
                screenshots.append(str(parsed_png))
            except Exception:  # noqa: BLE001
                pass

            if cover_letter_required_unmet:
                return ApplyResult(
                    status=ApplyStatus.SKIPPED_REQUIRES_COVER_LETTER,
                    exit_reason="cover_letter_required",
                    fields_logged=fields_logged,
                    screenshots=screenshots,
                    detected_ats=self.KIND,
                )

            submit_btn = page.locator(
                "button:has-text('Submit application'), "
                "button:has-text('Submit Application'), "
                "button[type='submit']"
            ).first
            try:
                await submit_btn.scroll_into_view_if_needed()
            except Exception:  # noqa: BLE001
                pass

            about_png = screenshot_dir / "about_to_submit.png"
            try:
                await page.screenshot(path=str(about_png), full_page=True)
                screenshots.append(str(about_png))
            except Exception:  # noqa: BLE001
                pass

            if dry_run:
                return ApplyResult(
                    status=ApplyStatus.SUBMITTED_DRY_RUN,
                    exit_reason="dry_run_complete",
                    fields_logged=fields_logged,
                    screenshots=screenshots,
                    detected_ats=self.KIND,
                )

            # 5. Real submit.
            try:
                await submit_btn.hover()
                await submit_btn.click()
            except Exception as e:  # noqa: BLE001
                return ApplyResult(
                    status=ApplyStatus.FAILED_RETRYABLE,
                    exit_reason="submit_click_failed",
                    fields_logged=fields_logged,
                    screenshots=screenshots,
                    detected_ats=self.KIND,
                    error_message=str(e)[:500],
                )

            # 6. Confirmation: modal or page replacement.
            confirmed = False
            try:
                await page.wait_for_selector(
                    "text=/thank you for applying|application (received|submitted)|"
                    "we'?ve received your application/i",
                    timeout=15000,
                )
                confirmed = True
            except Exception:  # noqa: BLE001
                # URL-based fallback: some Ashby orgs redirect to /confirmation.
                try:
                    await page.wait_for_url(
                        re.compile(r"/confirmation|/thanks|/submitted", re.IGNORECASE),
                        timeout=3000,
                    )
                    confirmed = True
                except Exception:  # noqa: BLE001
                    confirmed = False

            confirm_png = screenshot_dir / "confirmation.png"
            try:
                await page.screenshot(path=str(confirm_png), full_page=True)
                screenshots.append(str(confirm_png))
            except Exception:  # noqa: BLE001
                pass

            if confirmed:
                return ApplyResult(
                    status=ApplyStatus.SUBMITTED,
                    exit_reason="confirmation_detected",
                    fields_logged=fields_logged,
                    screenshots=screenshots,
                    detected_ats=self.KIND,
                )

            return ApplyResult(
                status=ApplyStatus.FAILED_RETRYABLE,
                exit_reason="no_confirmation_15s",
                fields_logged=fields_logged,
                screenshots=screenshots,
                detected_ats=self.KIND,
                error_message="Submit clicked but no thank-you DOM/URL seen in 15s",
            )

        except asyncio.TimeoutError as e:
            return ApplyResult(
                status=ApplyStatus.FAILED_RETRYABLE,
                exit_reason="timeout",
                fields_logged=fields_logged,
                screenshots=screenshots,
                detected_ats=self.KIND,
                error_message=str(e)[:500],
            )
        except Exception as e:  # noqa: BLE001
            logger.exception("[ashby] unexpected adapter error")
            return ApplyResult(
                status=ApplyStatus.FAILED_RETRYABLE,
                exit_reason=type(e).__name__,
                fields_logged=fields_logged,
                screenshots=screenshots,
                detected_ats=self.KIND,
                error_message=str(e)[:500],
            )

    async def _label_for(self, page, handle) -> str:
        """Resolve label text for an Ashby form control. Ashby is a11y-
        friendly, so aria-label / aria-labelledby covers ~90% of fields.
        """

        try:
            text = await handle.evaluate(
                """el => {
                    if (el.getAttribute('aria-label')) return el.getAttribute('aria-label');
                    const labelledBy = el.getAttribute('aria-labelledby');
                    if (labelledBy) {
                        const lb = document.getElementById(labelledBy);
                        if (lb && lb.innerText) return lb.innerText;
                    }
                    if (el.id) {
                        const l = document.querySelector(`label[for="${el.id}"]`);
                        if (l && l.innerText) return l.innerText;
                    }
                    let p = el.closest('label');
                    if (p && p.innerText) return p.innerText;
                    // Ashby wraps each question in a div with a sibling label-ish
                    // element. Walk up two levels and look for the first text-bearing
                    // <label> or heading.
                    let q = el.closest('[class*="_fieldEntry"], [class*="_container"], div');
                    if (q) {
                        const al = q.querySelector('label, [class*="_label"], legend');
                        if (al && al.innerText) return al.innerText;
                    }
                    return el.getAttribute('placeholder') || el.getAttribute('name') || '';
                }"""
            )
            return (text or "").strip()
        except Exception:  # noqa: BLE001
            return ""
