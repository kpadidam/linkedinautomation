"""Lever ATS adapter.

Lever job postings live at https://jobs.lever.co/{company}/{posting-id}.
The apply form is at /apply on the same URL and is *almost always* a
single-page form: text inputs at the top (name, email, phone, etc.),
followed by a resume drop-zone, an optional cover-letter textarea, then
custom posting-specific questions, then a "Submit application" button.

Lever's DOM is server-rendered and relatively stable:
  * Required fields carry the ``application-question required`` class
    (or just ``required`` on the wrapping div).
  * Labels live inside ``.application-label`` siblings or are
    ``<label for="...">`` linked to the input.
  * The resume input is ``input[name="resume"]`` (file).
  * Custom questions appear in ``.application-question`` blocks; the
    label text is what the operator wrote when they built the posting.

We try to be conservative: any field we don't recognize is *logged* as a
skipped FormField (in dry-run) so the operator can decide what to do
with it before flipping to a real submit.
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


# --- typing humanizer ---------------------------------------------------------
# Lognormal per-keystroke delay. Mean ~80ms, with a wide tail so the occasional
# 300ms gap shows up. page.fill() would dump the whole string in one IPC call,
# which looks robotic on a behavior fingerprint. page.keyboard.type with a per-
# char delay reads as a person.

_TYPE_MU = math.log(0.080)   # ~80ms
_TYPE_SIGMA = 0.5
_TYPE_MIN_MS = 25
_TYPE_MAX_MS = 450


def _sample_delay_ms(rng: random.Random | None = None) -> int:
    rng = rng or random.Random()
    s = rng.lognormvariate(_TYPE_MU, _TYPE_SIGMA) * 1000.0
    return int(max(_TYPE_MIN_MS, min(_TYPE_MAX_MS, s)))


async def _human_type(page, selector: str, text: str) -> None:
    """Focus an element and type with a per-keystroke lognormal delay.

    Uses ``page.keyboard.type`` against the focused element rather than
    ``locator.fill`` so each character takes its own time. We do a quick
    ``locator.click()`` first to focus and clear the field via select-all.
    """

    loc = page.locator(selector).first
    await loc.scroll_into_view_if_needed()
    await loc.hover()
    await loc.click()
    # Wipe any pre-filled value (LinkedIn-imported phone, etc.).
    await page.keyboard.press("Meta+A")
    await page.keyboard.press("Backspace")
    for ch in text:
        await page.keyboard.type(ch, delay=_sample_delay_ms())


# --- field map loader ---------------------------------------------------------

_FIELD_MAP_PATH = Path(__file__).resolve().parent / "field_map.yaml"


def _load_field_map() -> list[dict]:
    try:
        with _FIELD_MAP_PATH.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return data.get("mappings", []) or []
    except Exception:  # noqa: BLE001
        logger.warning("[lever] could not load field_map.yaml", exc_info=True)
        return []


_FIELD_MAP = _load_field_map()


def _match_field(label: str) -> tuple[Optional[str], Optional[str]]:
    """Return (profile_key, default) for a label, or (None, None)."""

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
    """Resolve a dotted profile path. Mirrors the conventions in
    field_map.yaml. Returns None if the value is missing/empty."""

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
class LeverAdapter(ATSAdapter):
    """Lever-hosted job postings."""

    KIND = ATSKind.LEVER
    URL_PATTERNS = (re.compile(r"jobs\.lever\.co", re.IGNORECASE),)

    # Markers we look for in the rendered HTML. Any single one is enough
    # — Lever embeds at least two of these on every posting page.
    _DOM_MARKERS = (
        "lever-jobs",
        "lever-apply-form",
        "jobs.lever.co",
        "data-qa=\"posting-name\"",
        "application-form",
    )

    @classmethod
    def recognize(cls, html: str) -> bool:
        if not html:
            return False
        snippet = html[:200_000]  # bounded scan; pages are usually < 200KB anyway
        return any(marker in snippet for marker in cls._DOM_MARKERS)

    # --- apply ----------------------------------------------------------------

    async def apply(self, page, job, profile, dry_run: bool = True) -> ApplyResult:
        fields_logged: list[FormField] = []
        screenshots: list[str] = []
        screenshot_dir = Path("data") / "apply_runs" / "lever_scratch"
        screenshot_dir.mkdir(parents=True, exist_ok=True)

        try:
            # 1. Navigate to the apply page. Some Lever postings include
            #    an explicit "Apply for this job" CTA on the JD page; others
            #    land you straight at /apply. We handle both.
            current_url = page.url or ""
            if "/apply" not in current_url:
                # Try clicking the CTA first (preserves any tracking params
                # Lever attaches to the apply URL).
                cta = page.locator(
                    "a[href*='/apply'], a.postings-btn, a.template-btn-submit"
                ).first
                try:
                    if await cta.count() > 0:
                        await cta.hover()
                        await cta.click()
                        await page.wait_for_load_state("domcontentloaded", timeout=15000)
                    else:
                        await page.goto(
                            current_url.rstrip("/") + "/apply",
                            wait_until="domcontentloaded",
                            timeout=20000,
                        )
                except Exception:  # noqa: BLE001
                    # Fall through; maybe we're already on the form.
                    pass

            # 2. Wait for the form to render.
            try:
                await page.wait_for_selector(
                    "form, .application-form, [data-qa='application-form']",
                    timeout=15000,
                )
            except Exception:  # noqa: BLE001
                return ApplyResult(
                    status=ApplyStatus.FAILED_RETRYABLE,
                    exit_reason="form_not_found",
                    detected_ats=self.KIND,
                    error_message="Lever apply form did not render within 15s",
                )

            # 3. Walk the visible fields. We grab every input/select/textarea
            #    inside the application form, then resolve each by its
            #    associated <label>.
            field_handles = await page.locator(
                "form input:not([type='hidden']):not([type='submit']):not([type='button']), "
                "form textarea, form select"
            ).element_handles()

            cover_letter_required_unmet = False

            for handle in field_handles:
                try:
                    label_text = await self._label_for(page, handle)
                    input_type = (await handle.get_attribute("type") or "").lower()
                    name_attr = (await handle.get_attribute("name") or "").lower()
                    required = await handle.evaluate(
                        "el => el.required || el.getAttribute('aria-required') === 'true' "
                        "|| el.closest('.application-question.required, .required') !== null"
                    )

                    selector_hint = f"[name='{name_attr}']" if name_attr else label_text

                    # Cover letter detection: Lever's textarea is named
                    # "comments" by convention; the label is something like
                    # "Additional information" or "Cover letter".
                    is_cover_letter = (
                        "cover" in label_text.lower()
                        or name_attr in {"comments", "coverletter", "cover_letter"}
                    )

                    # File inputs (resume).
                    if input_type == "file":
                        resume_path = _resolve_profile_value(profile, "resume_file")
                        if resume_path and Path(resume_path).exists():
                            await handle.set_input_files(resume_path)
                            fields_logged.append(
                                FormField(
                                    label=label_text or name_attr or "resume",
                                    value=resume_path,
                                    source="profile",
                                    selector=selector_hint,
                                )
                            )
                        else:
                            fields_logged.append(
                                FormField(
                                    label=label_text or "resume",
                                    value="",
                                    source="skipped",
                                    confidence=0.0,
                                    selector=selector_hint,
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

                    # Cover letter textarea.
                    if is_cover_letter:
                        # No profile-side cover letter store yet. If it's
                        # required, bail with the dedicated status.
                        if required:
                            cover_letter_required_unmet = True
                        fields_logged.append(
                            FormField(
                                label=label_text or "cover letter",
                                value="",
                                source="skipped",
                                confidence=0.0,
                                selector=selector_hint,
                            )
                        )
                        continue

                    # Heuristic match.
                    profile_key, default = _match_field(label_text or name_attr)
                    value = _resolve_profile_value(profile, profile_key) if profile_key else None
                    if not value and default:
                        value = default

                    if not value:
                        # Unknown field — log skip, do not fill. The LLM
                        # fallback module (services/ats/llm_fallback.py) is
                        # the long-term fix; for slice 6 we just record.
                        fields_logged.append(
                            FormField(
                                label=label_text or name_attr or "(unlabeled)",
                                value="",
                                source="skipped",
                                confidence=0.0,
                                selector=selector_hint,
                            )
                        )
                        continue

                    # Select dropdown.
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
                                        selector=selector_hint,
                                    )
                                )
                                continue
                        fields_logged.append(
                            FormField(
                                label=label_text,
                                value=value,
                                source="profile" if profile_key else "default",
                                selector=selector_hint,
                            )
                        )
                        continue

                    # Checkbox / radio.
                    if input_type in {"checkbox", "radio"}:
                        if value.lower() in {"yes", "true", "1", "y"}:
                            await handle.check()
                        fields_logged.append(
                            FormField(
                                label=label_text,
                                value=value,
                                source="profile" if profile_key else "default",
                                selector=selector_hint,
                            )
                        )
                        continue

                    # Plain text / textarea / email / tel / url.
                    # Build a stable selector for _human_type.
                    if name_attr:
                        css = f"form [name='{name_attr}']"
                    else:
                        # Last-resort: use the handle's evaluated unique attribute.
                        css = await handle.evaluate(
                            "el => el.id ? '#' + el.id : null"
                        )
                        if not css:
                            # Skip rather than risk a wrong selector.
                            fields_logged.append(
                                FormField(
                                    label=label_text,
                                    value=value,
                                    source="skipped",
                                    confidence=0.2,
                                    selector="(no stable selector)",
                                )
                            )
                            continue
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
                    logger.warning(f"[lever] field walk error: {e}", exc_info=True)
                    continue

            # 4. Screenshot the parsed form.
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

            # 5. Screenshot the "about to submit" state.
            submit_btn = page.locator(
                "button[type='submit'], input[type='submit'], "
                "button:has-text('Submit application'), button:has-text('Submit Application')"
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

            # 6. Real submit.
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

            # 7. Confirmation detection — 15s window. Lever redirects to
            #    .../thanks (or shows a "Thank you" element on the page).
            confirmed = False
            try:
                await page.wait_for_url(re.compile(r"/thanks", re.IGNORECASE), timeout=15000)
                confirmed = True
            except Exception:  # noqa: BLE001
                try:
                    await page.wait_for_selector(
                        "text=/thank you for applying|application received|we'?ve received/i",
                        timeout=5000,
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
                error_message="Submit clicked but no /thanks URL or thank-you DOM seen in 15s",
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
            logger.exception("[lever] unexpected adapter error")
            return ApplyResult(
                status=ApplyStatus.FAILED_RETRYABLE,
                exit_reason=type(e).__name__,
                fields_logged=fields_logged,
                screenshots=screenshots,
                detected_ats=self.KIND,
                error_message=str(e)[:500],
            )

    # --- helpers --------------------------------------------------------------

    async def _label_for(self, page, handle) -> str:
        """Best-effort label text for a form control.

        Priority:
          1. aria-label
          2. <label for=ID>
          3. closest <label> ancestor
          4. closest .application-label / .posting-application-label sibling
          5. placeholder / name attribute
        """

        try:
            text = await handle.evaluate(
                """el => {
                    if (el.getAttribute('aria-label')) return el.getAttribute('aria-label');
                    if (el.id) {
                        const l = document.querySelector(`label[for="${el.id}"]`);
                        if (l && l.innerText) return l.innerText;
                    }
                    let p = el.closest('label');
                    if (p && p.innerText) return p.innerText;
                    let q = el.closest('.application-question, li');
                    if (q) {
                        const al = q.querySelector('.application-label, .posting-application-label, label');
                        if (al && al.innerText) return al.innerText;
                    }
                    return el.getAttribute('placeholder') || el.getAttribute('name') || '';
                }"""
            )
            return (text or "").strip()
        except Exception:  # noqa: BLE001
            return ""
