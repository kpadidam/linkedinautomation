"""Greenhouse ATS adapter.

This sandbox adapter follows the shared ``services.ats.base`` contract but
keeps Greenhouse-specific DOM handling local to this module.
"""

from __future__ import annotations

import logging
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - only used in lean sandboxes.
    yaml = None

from config import settings
from services.ats.base import (
    ATSAdapter,
    ATSKind,
    ApplyResult,
    ApplyStatus,
    FormField,
    register_adapter,
)

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
FIELD_MAP_PATH = Path(__file__).resolve().parent / "field_map.yaml"
FORM_SCREENSHOT = "form_parsed.png"
CONFIRMATION_SCREENSHOT = "confirmation.png"

GREENHOUSE_MARKERS = (
    'id="application_form"',
    "id='application_form'",
    "id=application_form",
    "boards.greenhouse.io",
    'id="job_application"',
    "id='job_application'",
    "id=job_application",
    "greenhouse-application",
)

KNOWN_NO_FILL_TYPES = {
    "button",
    "checkbox",
    "hidden",
    "image",
    "radio",
    "reset",
    "submit",
}


@lru_cache(maxsize=1)
def _field_map() -> list[dict[str, Any]]:
    """Load and compile the user-editable heuristic field map once."""

    with FIELD_MAP_PATH.open("r", encoding="utf-8") as fh:
        if yaml is not None:
            raw = yaml.safe_load(fh) or {}
        else:
            raw = _parse_simple_field_map(fh.read())

    mappings: list[dict[str, Any]] = []
    for row in raw.get("mappings", []):
        pattern = row.get("pattern")
        profile_key = row.get("profile_key")
        if not pattern or not profile_key:
            continue
        mappings.append(
            {
                **row,
                "compiled": re.compile(str(pattern), re.IGNORECASE),
            }
        )
    return mappings


def _parse_simple_field_map(text: str) -> dict[str, list[dict[str, str]]]:
    """Minimal fallback for ``services/ats/field_map.yaml``.

    The real runtime should use PyYAML. This parser intentionally supports only
    the current list-of-mappings shape so local import checks do not require an
    installed dependency.
    """

    mappings: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line == "mappings:":
            continue
        if line.startswith("- "):
            if current:
                mappings.append(current)
            current = {}
            line = line[2:].strip()
        if ":" not in line or current is None:
            continue
        key, value = line.split(":", 1)
        value = value.split("  #", 1)[0].strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        current[key.strip()] = value
    if current:
        mappings.append(current)
    return {"mappings": mappings}


def _normalize_label(label: str) -> str:
    cleaned = re.sub(r"\b(required)\b", " ", label or "", flags=re.IGNORECASE)
    cleaned = cleaned.replace("*", " ").strip(" :")
    return re.sub(r"\s+", " ", cleaned).strip()


def _value_to_log(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _name_parts(profile: Any) -> tuple[str, str, str]:
    full = _value_to_log(getattr(profile, "name", "")).strip()
    parts = full.split()
    first = parts[0] if parts else ""
    last = parts[-1] if len(parts) > 1 else ""
    return full, first, last


def _profile_value(profile: Any, profile_key: str, default: Any = None) -> Any:
    full_name, first_name, last_name = _name_parts(profile)

    derived = {
        "name.full": full_name,
        "name.first": first_name,
        "name.last": last_name,
        "email": getattr(profile, "email", None),
        "phone": getattr(profile, "phone", None),
        "linkedin": getattr(profile, "linkedin_url", None),
        "website": getattr(profile, "website", None),
        "years_experience": getattr(profile, "years_experience", None),
        "current_company": getattr(profile, "current_company", None),
        "city": getattr(profile, "city", None),
        "country": getattr(profile, "country", None),
        "resume_file": _resume_path(profile),
        "work_auth.yes_no": getattr(profile, "work_authorized", None),
        "work_auth.needs_sponsorship": getattr(profile, "needs_sponsorship", None),
    }

    value = derived.get(profile_key)
    if profile_key == "github" and not value:
        value = _extract_url(getattr(profile, "resume_text", None), "github.com")
    if not value and default is not None:
        value = default
    return value


def _extract_url(text: Optional[str], host: str) -> Optional[str]:
    if not text:
        return None
    match = re.search(rf"https?://[^\s)>\"]*{re.escape(host)}[^\s)>\"]*", text)
    return match.group(0) if match else None


def _resume_path(profile: Any) -> Optional[str]:
    candidates = [
        getattr(profile, "resume_file_path", None),
        settings.resume_file_path,
    ]
    candidates.extend(str(p) for p in REPO_ROOT.glob("*.pdf"))

    for candidate in candidates:
        if not candidate:
            continue
        path = Path(str(candidate)).expanduser()
        if not path.is_absolute():
            path = REPO_ROOT / path
        if path.exists() and path.is_file():
            return str(path)
    return None


def _mapping_for_label(label: str) -> Optional[dict[str, Any]]:
    normalized = _normalize_label(label)
    for row in _field_map():
        if row["compiled"].search(normalized):
            return row
    return None


@register_adapter
class GreenhouseAdapter(ATSAdapter):
    KIND = ATSKind.GREENHOUSE
    URL_PATTERNS = (
        re.compile(r"https?://(?:www\.)?boards\.greenhouse\.io/", re.IGNORECASE),
        re.compile(r"https?://(?:www\.)?grnh\.se/", re.IGNORECASE),
        re.compile(r"https?://(?:www\.)?job-boards\.greenhouse\.io/", re.IGNORECASE),
    )

    @classmethod
    def recognize(cls, html: str) -> bool:
        haystack = (html or "").lower()
        return any(marker in haystack for marker in GREENHOUSE_MARKERS)

    async def apply(
        self,
        page: Page,
        job,
        profile,
        dry_run: bool = True,
    ) -> ApplyResult:
        fields_logged: list[FormField] = []
        screenshots: list[str] = []

        try:
            await self._open_form_if_needed(page)
            await page.wait_for_load_state("domcontentloaded", timeout=10000)

            if await self._has_required_cover_letter(page):
                await self._screenshot(page, FORM_SCREENSHOT, screenshots)
                return ApplyResult(
                    status=ApplyStatus.SKIPPED_REQUIRES_COVER_LETTER,
                    exit_reason="cover_letter_required",
                    fields_logged=fields_logged,
                    screenshots=screenshots,
                    detected_ats=self.KIND,
                )

            field_count = await page.locator("input, textarea, select").count()
            for index in range(field_count):
                field = page.locator("input, textarea, select").nth(index)
                try:
                    if not await field.is_visible(timeout=1000):
                        continue
                    tag = await field.evaluate("el => el.tagName.toLowerCase()")
                    field_type = (
                        await field.get_attribute("type")
                        if tag == "input"
                        else None
                    ) or ""
                    field_type = field_type.lower()
                    if field_type in KNOWN_NO_FILL_TYPES:
                        continue

                    label = await self._label_for_field(field)
                    selector = await self._selector_for_field(field)
                    mapping = _mapping_for_label(label)

                    if not mapping:
                        fields_logged.append(
                            FormField(
                                label=label,
                                value="",
                                source="skipped",
                                confidence=0.0,
                                selector=selector,
                            )
                        )
                        continue

                    value = _profile_value(
                        profile,
                        str(mapping["profile_key"]),
                        mapping.get("default"),
                    )
                    if not value:
                        fields_logged.append(
                            FormField(
                                label=label,
                                value="",
                                source="skipped",
                                confidence=0.35,
                                selector=selector,
                            )
                        )
                        continue

                    filled = await self._fill_field(page, field, tag, field_type, value)
                    fields_logged.append(
                        FormField(
                            label=label,
                            value=_value_to_log(value),
                            source="heuristic" if filled else "skipped",
                            confidence=0.9 if filled else 0.45,
                            selector=selector,
                        )
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.info("[greenhouse] skipped field %s: %s", index, exc)
                    continue

            await self._screenshot(page, FORM_SCREENSHOT, screenshots)

            if dry_run:
                return ApplyResult(
                    status=ApplyStatus.SUBMITTED_DRY_RUN,
                    exit_reason="dry_run_complete",
                    fields_logged=fields_logged,
                    screenshots=screenshots,
                    detected_ats=self.KIND,
                )

            await self._click_submit(page)

            if await self._wait_for_confirmation(page):
                await self._screenshot(page, CONFIRMATION_SCREENSHOT, screenshots)
                return ApplyResult(
                    status=ApplyStatus.SUBMITTED,
                    exit_reason="confirmation_detected",
                    fields_logged=fields_logged,
                    screenshots=screenshots,
                    detected_ats=self.KIND,
                )

            await self._screenshot(page, CONFIRMATION_SCREENSHOT, screenshots)
            return ApplyResult(
                status=ApplyStatus.FAILED_RETRYABLE,
                exit_reason="confirmation_not_detected",
                fields_logged=fields_logged,
                screenshots=screenshots,
                error_message="Submit clicked, but no Greenhouse confirmation appeared within 15s.",
                detected_ats=self.KIND,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("[greenhouse] apply failed", exc_info=True)
            return ApplyResult(
                status=ApplyStatus.FAILED_RETRYABLE,
                exit_reason="greenhouse_apply_error",
                fields_logged=fields_logged,
                screenshots=screenshots,
                error_message=str(exc),
                detected_ats=self.KIND,
            )

    async def _open_form_if_needed(self, page: Page) -> None:
        if await self._form_present(page):
            return

        apply_button = page.get_by_role(
            "link", name=re.compile(r"^\s*apply\s*$", re.IGNORECASE)
        ).or_(
            page.get_by_role(
                "button", name=re.compile(r"^\s*apply\s*$", re.IGNORECASE)
            )
        )
        try:
            clicked = await self._click_first_visible(apply_button)
            if clicked:
                await page.wait_for_timeout(1000)
        except PlaywrightTimeoutError:
            logger.info("[greenhouse] apply button was present but not clickable")

        try:
            await page.locator(
                "#application_form, #job_application, .greenhouse-application, "
                "form:has(input), form:has(textarea), form:has(select)"
            ).first.wait_for(state="visible", timeout=10000)
        except PlaywrightTimeoutError:
            logger.info("[greenhouse] form did not become visible after apply click")

    async def _form_present(self, page: Page) -> bool:
        return (
            await page.locator(
                "#application_form, #job_application, .greenhouse-application, "
                "form:has(input), form:has(textarea), form:has(select)"
            ).count()
            > 0
        )

    async def _has_required_cover_letter(self, page: Page) -> bool:
        textareas = page.locator("textarea")
        count = await textareas.count()
        for index in range(count):
            field = textareas.nth(index)
            if not await field.is_visible(timeout=1000):
                continue
            label = await self._label_for_field(field)
            if not re.search(r"cover[\s_-]?letter", label, re.IGNORECASE):
                continue
            required = await field.evaluate(
                """el => {
                    if (el.required || el.getAttribute('aria-required') === 'true') return true;
                    const id = el.id;
                    const label = id ? document.querySelector(`label[for="${CSS.escape(id)}"]`) : null;
                    const text = `${label?.innerText || ''} ${el.closest('div, li, fieldset')?.innerText || ''}`;
                    return /\\*/.test(text) || /required/i.test(text);
                }"""
            )
            if required:
                return True
        return False

    async def _label_for_field(self, field) -> str:
        label = await field.evaluate(
            """el => {
                const clean = (value) => (value || '').replace(/\\s+/g, ' ').trim();
                if (el.id) {
                    const explicit = document.querySelector(`label[for="${CSS.escape(el.id)}"]`);
                    if (explicit) return clean(explicit.innerText || explicit.textContent);
                }
                if (el.getAttribute('aria-label')) return clean(el.getAttribute('aria-label'));
                if (el.getAttribute('placeholder')) return clean(el.getAttribute('placeholder'));
                const wrapping = el.closest('label');
                if (wrapping) return clean(wrapping.innerText || wrapping.textContent);
                let node = el.previousElementSibling;
                for (let i = 0; node && i < 4; i += 1, node = node.previousElementSibling) {
                    if (node.matches('label')) return clean(node.innerText || node.textContent);
                    const nested = node.querySelector?.('label');
                    if (nested) return clean(nested.innerText || nested.textContent);
                    const text = clean(node.innerText || node.textContent);
                    if (text && text.length <= 120) return text;
                }
                const group = el.closest('.field, .field-row, .application-field, li, div');
                if (group) {
                    const groupLabel = group.querySelector('label');
                    if (groupLabel) return clean(groupLabel.innerText || groupLabel.textContent);
                }
                return clean(el.name || el.id || el.getAttribute('data-testid'));
            }"""
        )
        return _normalize_label(label)

    async def _selector_for_field(self, field) -> str:
        selector = await field.evaluate(
            """el => {
                if (el.id) return `#${CSS.escape(el.id)}`;
                if (el.name) return `${el.tagName.toLowerCase()}[name="${CSS.escape(el.name)}"]`;
                return el.tagName.toLowerCase();
            }"""
        )
        return selector or ""

    async def _fill_field(
        self,
        page: Page,
        field,
        tag: str,
        field_type: str,
        value: Any,
    ) -> bool:
        value_text = _value_to_log(value)
        if tag == "select":
            try:
                await field.select_option(label=value_text)
            except Exception:  # noqa: BLE001
                await field.select_option(value=value_text)
            return True

        if field_type == "file":
            path = Path(value_text)
            if not path.exists():
                return False
            await field.set_input_files(str(path))
            return True

        selector = await self._selector_for_field(field)
        if selector:
            try:
                await page.fill(selector, value_text)
                return True
            except Exception:  # noqa: BLE001
                pass
        await field.fill(value_text)
        return True

    async def _click_submit(self, page: Page) -> None:
        submit_role = page.get_by_role(
            "button", name=re.compile(r"submit|apply", re.IGNORECASE)
        )
        if await self._click_first_visible(submit_role):
            return

        submit = page.locator(
            "button[type='submit'], input[type='submit'], "
            "#submit_app, .submit, [data-source='submit']"
        )
        if await self._click_first_visible(submit):
            return
        await submit.first().click(timeout=5000)

    async def _click_first_visible(self, locator) -> bool:
        count = await locator.count()
        for index in range(count):
            candidate = locator.nth(index)
            if await candidate.is_visible(timeout=500):
                await candidate.click(timeout=5000)
                return True
        return False

    async def _wait_for_confirmation(self, page: Page) -> bool:
        success_text = page.get_by_text(
            re.compile(r"thank you|application received|application submitted", re.IGNORECASE)
        )
        try:
            await success_text.first().wait_for(state="visible", timeout=15000)
            return True
        except PlaywrightTimeoutError:
            pass

        return bool(
            re.search(
                r"(greenhouse\.io/.*/confirmation|/confirmation|application_submitted|application-received)",
                page.url,
                re.IGNORECASE,
            )
        )

    async def _screenshot(self, page: Page, filename: str, screenshots: list[str]) -> None:
        await page.screenshot(path=filename, full_page=True)
        screenshots.append(filename)
