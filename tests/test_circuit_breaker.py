"""Tests for the LinkedIn-specific circuit breaker tripwires + helpers."""

from __future__ import annotations

import pytest

from services.circuit_breaker import (
    CircuitBreaker,
    CircuitObservation,
    CircuitTripped,
    auth_wall_present,
    captcha_iframe_present,
    job_unavailable_present,
    reset_breaker,
)


# --- helper functions ----------------------------------------------------


@pytest.mark.parametrize(
    "html, expected",
    [
        ("<iframe src='https://arkoselabs.com/v2/...'></iframe>", True),
        ("<script src='funcaptcha.com/v2.js'></script>", True),
        ("<iframe src='https://hcaptcha.com/captcha/...'></iframe>", True),
        ("<iframe src='https://www.google.com/recaptcha/api'></iframe>", True),
        # Negative cases — these used to false-positive (paircode r2 catch).
        ("<p>This site uses a captcha to prevent bots</p>", False),
        ("<iframe src='https://linkedin.com/tracking'></iframe>", False),
        ("", False),
        ("<p>The word captcha appears here, and there's an iframe.</p>"
         "<iframe src='/other'></iframe>", False),
    ],
)
def test_captcha_iframe_present(html, expected):
    assert captcha_iframe_present(html) is expected


@pytest.mark.parametrize(
    "html, url, expected",
    [
        ("<html>Sign in to view more jobs</html>", None, True),
        ("<html>...</html>", "https://linkedin.com/authwall?x=1", True),
        ("<html>About us</html>", "https://example.com/foo", False),
        ("", None, False),
    ],
)
def test_auth_wall_present(html, url, expected):
    assert auth_wall_present(html, url) is expected


@pytest.mark.parametrize(
    "html, title, expected",
    [
        ("", "Page not found", True),
        ("<html>Page not found. The link you visited may be broken</html>",
         None, True),
        ("<html>Page not found. Go to your feed</html>", None, True),
        # Negative — JD that just mentions "page not found" in body.
        ("<html>If the page not found, contact HR.</html>", "Senior Eng", False),
        ("<html>Senior Engineer</html>", "Senior Engineer", False),
        ("", "", False),
    ],
)
def test_job_unavailable_present(html, title, expected):
    assert job_unavailable_present(html, title) is expected


# --- the breaker itself --------------------------------------------------


def _make_breaker(profile, db):
    """Helper: build a fresh CircuitBreaker bound to profile + db."""
    return CircuitBreaker(profile, db)


def _profile_in_db(temp_db_session, fake_profile):
    """Insert the SimpleNamespace fake_profile-ish into UserProfile so
    the breaker's db.commit() doesn't trip on a detached instance."""
    from database.models import UserProfile
    p = UserProfile(
        name="Test", email="t@x.com",
        auto_apply_enabled=True, daily_apply_cap=15,
        quiet_hours_start=23, quiet_hours_end=7,
        circuit_tripped=False, circuit_consecutive_failures=0,
        apply_browser_mode="chromium_ephemeral",
    )
    temp_db_session.add(p)
    temp_db_session.commit()
    return p


def test_breaker_trips_on_999(temp_db_session, fake_profile):
    p = _profile_in_db(temp_db_session, fake_profile)
    cb = _make_breaker(p, temp_db_session)
    with pytest.raises(CircuitTripped) as ei:
        cb.observe(CircuitObservation(url="https://linkedin.com/x", status=999))
    assert "999" in ei.value.reason
    assert p.circuit_tripped is True


def test_breaker_trips_on_repeated_429(temp_db_session, fake_profile):
    p = _profile_in_db(temp_db_session, fake_profile)
    cb = _make_breaker(p, temp_db_session)
    # First two 429s shouldn't trip.
    cb.observe(CircuitObservation(url="x", status=429))
    cb.observe(CircuitObservation(url="x", status=429))
    assert p.circuit_tripped is False
    with pytest.raises(CircuitTripped):
        cb.observe(CircuitObservation(url="x", status=429))
    assert p.circuit_tripped is True


def test_breaker_trips_on_voyager_403(temp_db_session, fake_profile):
    p = _profile_in_db(temp_db_session, fake_profile)
    cb = _make_breaker(p, temp_db_session)
    with pytest.raises(CircuitTripped) as ei:
        cb.observe(CircuitObservation(
            url="https://www.linkedin.com/voyager/api/foo", status=403,
            was_authenticated=True,
        ))
    assert "voyager" in ei.value.reason


def test_breaker_ignores_403_when_unauthenticated(temp_db_session, fake_profile):
    """403 on a voyager URL while we weren't logged in is just a
    well-behaved auth error, not an automation tripwire."""
    p = _profile_in_db(temp_db_session, fake_profile)
    cb = _make_breaker(p, temp_db_session)
    cb.observe(CircuitObservation(
        url="https://www.linkedin.com/voyager/api/foo", status=403,
        was_authenticated=False,
    ))
    assert p.circuit_tripped is False


def test_breaker_trips_on_checkpoint_redirect(temp_db_session, fake_profile):
    p = _profile_in_db(temp_db_session, fake_profile)
    cb = _make_breaker(p, temp_db_session)
    with pytest.raises(CircuitTripped) as ei:
        cb.observe(CircuitObservation(
            url="https://www.linkedin.com/checkpoint/lg/login-submit",
            status=302,
        ))
    assert "checkpoint" in ei.value.reason


def test_breaker_trips_on_body_signal(temp_db_session, fake_profile):
    p = _profile_in_db(temp_db_session, fake_profile)
    cb = _make_breaker(p, temp_db_session)
    with pytest.raises(CircuitTripped) as ei:
        cb.observe(CircuitObservation(
            url="https://linkedin.com/feed",
            status=200,
            body_snippet="We've detected unusual activity from your account",
        ))
    assert "body_signal" in ei.value.reason


def test_breaker_trips_on_unexpected_login_redirect(temp_db_session, fake_profile):
    p = _profile_in_db(temp_db_session, fake_profile)
    cb = _make_breaker(p, temp_db_session)
    with pytest.raises(CircuitTripped) as ei:
        cb.observe(CircuitObservation(
            url="https://www.linkedin.com/uas/login",
            status=200,
            was_authenticated=True,
        ))
    assert "login" in ei.value.reason


def test_consecutive_failures_hard_trip(temp_db_session, fake_profile):
    p = _profile_in_db(temp_db_session, fake_profile)
    cb = _make_breaker(p, temp_db_session)
    cb.record_consecutive_failure()
    cb.record_consecutive_failure()
    assert p.circuit_tripped is False
    with pytest.raises(CircuitTripped) as ei:
        cb.record_consecutive_failure()
    assert "consecutive_failures" in ei.value.reason


def test_record_success_clears_failure_counter(temp_db_session, fake_profile):
    p = _profile_in_db(temp_db_session, fake_profile)
    cb = _make_breaker(p, temp_db_session)
    cb.record_consecutive_failure()
    cb.record_consecutive_failure()
    assert p.circuit_consecutive_failures == 2
    cb.record_success()
    assert p.circuit_consecutive_failures == 0


def test_reset_breaker_clears_state(temp_db_session, fake_profile):
    p = _profile_in_db(temp_db_session, fake_profile)
    cb = _make_breaker(p, temp_db_session)
    try:
        cb.observe(CircuitObservation(url="x", status=999))
    except CircuitTripped:
        pass
    assert p.circuit_tripped is True
    reset_breaker(p, temp_db_session)
    assert p.circuit_tripped is False
    assert p.circuit_tripped_at is None
    assert p.circuit_tripped_reason is None
    assert p.circuit_consecutive_failures == 0
