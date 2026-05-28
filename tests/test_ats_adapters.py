"""Tests for each concrete ATS adapter — URL patterns + recognize().

These are pure-Python tests against the adapter classes, no Playwright
required. They prove:
  * URL_PATTERNS match the documented host shapes (and don't over-claim)
  * recognize() against fixture HTML returns the right adapter
  * @register_adapter side-effect put each adapter in the global registry
"""

from __future__ import annotations

import pytest

from services.ats.base import ATSKind, _REGISTRY, _import_concrete_adapters


@pytest.fixture(scope="module", autouse=True)
def _ensure_adapters_imported():
    _import_concrete_adapters()


def _adapter_by_kind(kind: ATSKind):
    for cls in _REGISTRY:
        if cls.KIND == kind:
            return cls
    pytest.fail(f"adapter not registered for {kind}")


# --- Greenhouse ----------------------------------------------------------


@pytest.mark.parametrize(
    "url, expected",
    [
        ("https://boards.greenhouse.io/foo/jobs/123", True),
        ("https://www.boards.greenhouse.io/foo/jobs/123", True),
        ("https://grnh.se/abc", True),
        ("https://job-boards.greenhouse.io/foo/jobs/123", True),
        ("https://example.com/jobs/123", False),
        ("https://linkedin.com/jobs/view/123", False),
    ],
)
def test_greenhouse_url_patterns(url, expected):
    cls = _adapter_by_kind(ATSKind.GREENHOUSE)
    assert cls.matches_url(url) is expected


@pytest.mark.parametrize(
    "html, expected",
    [
        ('<form id="application_form">…</form>', True),
        ("<div class='greenhouse-application'>…</div>", True),
        ('<script src="https://boards.greenhouse.io/embed.js"></script>', True),
        ("<p>Some random page</p>", False),
        ("", False),
    ],
)
def test_greenhouse_recognize(html, expected):
    cls = _adapter_by_kind(ATSKind.GREENHOUSE)
    assert cls.recognize(html) is expected


# --- LinkedIn Easy Apply -------------------------------------------------


@pytest.mark.parametrize(
    "url, expected",
    [
        ("https://www.linkedin.com/jobs/view/4410759235/", True),
        ("https://linkedin.com/jobs/view/4410/", True),
        ("https://www.linkedin.com/jobs/collections/recommended/?currentJobId=4410", True),
        ("https://boards.greenhouse.io/foo/jobs/123", False),
        ("https://linkedin.com/feed/", False),
    ],
)
def test_easyapply_url_patterns(url, expected):
    cls = _adapter_by_kind(ATSKind.EASY_APPLY)
    assert cls.matches_url(url) is expected


@pytest.mark.parametrize(
    "html, expected",
    [
        ("<button class='jobs-apply-button'>Easy Apply</button>", True),
        ("<div class='jobs-easy-apply-modal'>…</div>", True),
        ("<p>Easy Apply</p>", True),
        ("<p>Apply now</p>", False),
        ("", False),
    ],
)
def test_easyapply_recognize(html, expected):
    cls = _adapter_by_kind(ATSKind.EASY_APPLY)
    assert cls.recognize(html) is expected


# --- Workday -------------------------------------------------------------


@pytest.mark.parametrize(
    "url, expected",
    [
        ("https://acme.wd1.myworkdayjobs.com/External/job/Foo/SE", True),
        ("https://acme.wd5.myworkdayjobs.com/CareerSite/job/X/Y", True),
        ("https://workday.com/foo", True),
        ("https://example.com/jobs/123", False),
    ],
)
def test_workday_url_patterns(url, expected):
    cls = _adapter_by_kind(ATSKind.WORKDAY)
    assert cls.matches_url(url) is expected


@pytest.mark.parametrize(
    "html, expected",
    [
        ('<button data-automation-id="adventureButton">Apply</button>', True),
        ("<svg class='wd-icon-foo'></svg>", True),
        # Note: a bare <script src="/workday.js"> isn't enough — the
        # adapter needs the literal word "Workday" inside script
        # contents (case-insensitive). That avoids false positives on
        # any site that happens to load a third-party workday-themed
        # asset.
        ('<script>var x = "Workday";</script>', True),
        ("<p>Other ATS</p>", False),
    ],
)
def test_workday_recognize(html, expected):
    cls = _adapter_by_kind(ATSKind.WORKDAY)
    assert cls.recognize(html) is expected


# --- Lever ---------------------------------------------------------------


@pytest.mark.parametrize(
    "url, expected",
    [
        ("https://jobs.lever.co/acme/abc-123", True),
        ("https://jobs.lever.co/acme/abc/apply", True),
        ("https://example.com/jobs/123", False),
        ("https://linkedin.com/jobs/view/123", False),
    ],
)
def test_lever_url_patterns(url, expected):
    cls = _adapter_by_kind(ATSKind.LEVER)
    assert cls.matches_url(url) is expected


@pytest.mark.parametrize(
    "html, expected",
    [
        ("<div class='lever-jobs'>…</div>", True),
        ("<form class='lever-apply-form'>…</form>", True),
        ('<link rel="canonical" href="https://jobs.lever.co/acme/abc"/>', True),
        ("<p>Other ATS</p>", False),
    ],
)
def test_lever_recognize(html, expected):
    cls = _adapter_by_kind(ATSKind.LEVER)
    assert cls.recognize(html) is expected


# --- Ashby ---------------------------------------------------------------


@pytest.mark.parametrize(
    "url, expected",
    [
        ("https://jobs.ashbyhq.com/acme/posting-id", True),
        ("https://acme.ashbyhq.com/jobs/posting-id", True),
        ("https://example.com/jobs/123", False),
    ],
)
def test_ashby_url_patterns(url, expected):
    cls = _adapter_by_kind(ATSKind.ASHBY)
    assert cls.matches_url(url) is expected


@pytest.mark.parametrize(
    "html, expected",
    [
        ("<div class='ashby-job-posting'>…</div>", True),
        ('<script>window.__ASHBY_PRELOADED_STATE__ = {}</script>', True),
        ("<p>https://ashbyhq.com/about</p>", True),
        ("<p>Other ATS</p>", False),
    ],
)
def test_ashby_recognize(html, expected):
    cls = _adapter_by_kind(ATSKind.ASHBY)
    assert cls.recognize(html) is expected


# --- No cross-talk: each adapter claims only its own pages ---------------


@pytest.mark.parametrize(
    "kind, html",
    [
        (ATSKind.GREENHOUSE, "<form id='application_form'>…</form>"),
        (ATSKind.EASY_APPLY, "<div class='jobs-easy-apply-modal'>…</div>"),
        # Note: the WORKDAY recognize is intentionally generous on
        # data-automation-id — we don't assert cross-exclusivity for
        # markers that legitimately appear on multiple platforms.
        (ATSKind.LEVER, "<form class='lever-apply-form'>…</form>"),
        (ATSKind.ASHBY, "<div class='ashby-job-posting'>…</div>"),
    ],
)
def test_recognize_is_specific(kind, html):
    """Each adapter's positive fixture should be recognized by ITS
    adapter only — no other adapter should claim it."""
    matched = {cls.KIND for cls in _REGISTRY if cls.recognize(html)}
    # We allow the target plus UNKNOWN (registry doesn't include it),
    # but no OTHER concrete adapter should also match.
    others = matched - {kind}
    assert not others, f"{kind} fixture also matched by {others}"
