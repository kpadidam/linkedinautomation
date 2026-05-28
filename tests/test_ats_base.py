"""Tests for the ATS framework — registry, dispatch, ABC contract."""

from __future__ import annotations

import re

import pytest

from services.ats.base import (
    ATSAdapter,
    ATSKind,
    ApplyResult,
    ApplyStatus,
    FormField,
    register_adapter,
    _REGISTRY,
)


def test_atskind_values_match_apply_status_strings():
    # Adapter return values must map cleanly into ApplicationRun.state.
    # Mismatches here mean the runner can't persist what the adapter
    # returned without translation.
    assert ATSKind.GREENHOUSE.value == "greenhouse"
    assert ATSKind.EASY_APPLY.value == "easy_apply"
    assert ATSKind.UNKNOWN.value == "unknown"
    assert ApplyStatus.SUBMITTED.value == "submitted"
    assert ApplyStatus.SUBMITTED_DRY_RUN.value == "submitted_dry_run"
    assert ApplyStatus.SKIPPED_REQUIRES_COVER_LETTER.value == "skipped_requires_cover_letter"
    assert ApplyStatus.BLOCKED_AUTH.value == "blocked_auth"


def test_form_field_defaults():
    f = FormField(label="email", value="x@y.com", source="profile")
    assert f.confidence == 1.0
    assert f.selector is None


def test_apply_result_defaults():
    r = ApplyResult(status=ApplyStatus.SUBMITTED_DRY_RUN, exit_reason="ok")
    assert r.fields_logged == []
    assert r.screenshots == []
    assert r.error_message is None
    assert r.detected_ats == ATSKind.UNKNOWN


def test_registry_is_populated_on_import():
    # Importing the package's concrete modules should trigger
    # @register_adapter side effects. We import lazily through detect_ats's
    # helper rather than at module load.
    from services.ats.base import _import_concrete_adapters
    _import_concrete_adapters()
    kinds = {cls.KIND for cls in _REGISTRY}
    expected = {
        ATSKind.GREENHOUSE,
        ATSKind.EASY_APPLY,
        ATSKind.WORKDAY,
        ATSKind.LEVER,
        ATSKind.ASHBY,
    }
    assert expected.issubset(kinds), (
        f"registry missing adapters: {expected - kinds}"
    )


def test_register_adapter_is_idempotent():
    # Registering the same class twice (e.g. via re-import) must not
    # produce a duplicate registry entry — detect_ats() would otherwise
    # double-fire recognize() per page.
    @register_adapter
    class _Dummy(ATSAdapter):
        KIND = ATSKind.UNKNOWN

        @classmethod
        def recognize(cls, html: str) -> bool:
            return False

        async def apply(self, page, job, profile, dry_run=True):
            return ApplyResult(status=ApplyStatus.FAILED_TERMINAL, exit_reason="dummy")

    before = sum(1 for c in _REGISTRY if c is _Dummy)
    register_adapter(_Dummy)
    after = sum(1 for c in _REGISTRY if c is _Dummy)
    assert before == after == 1


@pytest.mark.parametrize(
    "url, expected_kind",
    [
        ("https://boards.greenhouse.io/airbnb/jobs/12345", ATSKind.GREENHOUSE),
        ("https://grnh.se/abc123", ATSKind.GREENHOUSE),
        ("https://job-boards.greenhouse.io/foo/jobs/99", ATSKind.GREENHOUSE),
        ("https://www.linkedin.com/jobs/view/4410759235/", ATSKind.EASY_APPLY),
        ("https://acme.wd1.myworkdayjobs.com/External/job/Foo/SE_R123", ATSKind.WORKDAY),
        ("https://jobs.lever.co/airbnb/abc-def", ATSKind.LEVER),
        ("https://jobs.ashbyhq.com/airbnb/posting-id", ATSKind.ASHBY),
        ("https://acme.ashbyhq.com/jobs/posting-id", ATSKind.ASHBY),
        # Negatives: no adapter should claim these.
        ("https://stackoverflow.com/jobs/12345", None),
        ("https://hired.com/jobs/abc", None),
        ("", None),
    ],
)
def test_url_pattern_dispatch(url, expected_kind):
    """detect_ats's URL-pattern phase must dispatch correctly + not
    over-claim on unknown hosts."""

    from services.ats.base import _import_concrete_adapters
    _import_concrete_adapters()

    matched_kinds = [cls.KIND for cls in _REGISTRY if cls.matches_url(url)]
    if expected_kind is None:
        assert matched_kinds == [], (
            f"expected no match for {url}, got {matched_kinds}"
        )
    else:
        assert expected_kind in matched_kinds, (
            f"expected {expected_kind} to match {url}, got {matched_kinds}"
        )


def test_url_patterns_compiled_case_insensitive():
    # Adapters must tolerate canonical URL casing. boards.GREENHOUSE.IO
    # is the same posting as boards.greenhouse.io — a brittle pattern
    # would silently miss it.
    from services.ats.base import _import_concrete_adapters
    _import_concrete_adapters()
    upper = "https://BOARDS.GREENHOUSE.IO/foo/jobs/1"
    matched = [cls.KIND for cls in _REGISTRY if cls.matches_url(upper)]
    assert ATSKind.GREENHOUSE in matched
