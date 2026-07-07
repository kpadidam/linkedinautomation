"""Tests for cross-source application dedup."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from services import dedup
from services.dedup import (
    DEDUP_WINDOW_DAYS,
    compute_key,
    find_blocking_run,
    is_duplicate,
)


# --- key shape ------------------------------------------------------------


def test_compute_key_format():
    k = compute_key("Acme Corp", "Senior Engineer", "United States")
    # Format: "{sha1[:16]}|{normalized}"
    parts = k.split("|", 1)
    assert len(parts) == 2
    sha, body = parts
    assert len(sha) == 16
    assert all(c in "0123456789abcdef" for c in sha)
    assert "acme" in body
    assert "senior engineer" in body


def test_compute_key_is_deterministic():
    k1 = compute_key("Acme", "Engineer", "USA")
    k2 = compute_key("Acme", "Engineer", "USA")
    assert k1 == k2


def test_compute_key_normalizes_whitespace_and_punctuation():
    # "Acme, Inc." and "Acme  Inc"  should hash to the same key —
    # otherwise a JD with a stray comma evades dedup.
    a = compute_key("Acme, Inc.", "Senior Engineer", "United States")
    b = compute_key("Acme  Inc", "Senior  Engineer", "United States")
    assert a == b


def test_compute_key_lowercases():
    a = compute_key("Acme", "Senior Engineer", "USA")
    b = compute_key("ACME", "SENIOR ENGINEER", "usa")
    assert a == b


def test_compute_key_handles_none_and_empty():
    # Real Job rows can have null fields — must not crash.
    k = compute_key(None, "Engineer", None)
    # Sha1 prefix + pipe + normalized body containing "engineer".
    sha, body = k.split("|", 1)
    assert len(sha) == 16
    assert "engineer" in body


# --- blocking-state query -------------------------------------------------


@pytest.fixture
def db_with_runs(temp_db_session):
    """Seed the temp DB with a small set of ApplicationRuns spanning
    the blocking-states matrix + windows."""

    from database.models import ApplicationRun

    now = datetime.utcnow()
    rows = [
        # Blocking: recent + in submitted state.
        ApplicationRun(
            job_id="j1", ats="greenhouse", state="submitted",
            started_at=now - timedelta(days=2),
            dedup_key=compute_key("Acme", "Engineer", "USA"),
        ),
        # Not blocking: same key but failed_retryable (operator may want to retry).
        ApplicationRun(
            job_id="j2", ats="greenhouse", state="failed_retryable",
            started_at=now - timedelta(days=1),
            dedup_key=compute_key("Beta", "Engineer", "USA"),
        ),
        # Not blocking: too old (outside window).
        ApplicationRun(
            job_id="j3", ats="greenhouse", state="submitted",
            started_at=now - timedelta(days=DEDUP_WINDOW_DAYS + 5),
            dedup_key=compute_key("Gamma", "Engineer", "USA"),
        ),
        # Blocking: dry-run-complete counts as "we already showed up there".
        ApplicationRun(
            job_id="j4", ats="lever", state="submitted_dry_run",
            started_at=now - timedelta(hours=1),
            dedup_key=compute_key("Delta", "Engineer", "USA"),
        ),
    ]
    for r in rows:
        temp_db_session.add(r)
    temp_db_session.commit()
    return temp_db_session


def test_find_blocking_run_hits_recent_submission(db_with_runs):
    hit = find_blocking_run(db_with_runs, compute_key("Acme", "Engineer", "USA"))
    assert hit is not None
    assert hit.state == "submitted"


def test_find_blocking_run_ignores_retryable_failures(db_with_runs):
    # Failed runs don't burn the dedup slot. Operator retries should
    # always be allowed.
    hit = find_blocking_run(db_with_runs, compute_key("Beta", "Engineer", "USA"))
    assert hit is None


def test_find_blocking_run_respects_window(db_with_runs):
    # Submissions older than DEDUP_WINDOW_DAYS don't block — companies
    # legitimately re-post stale roles.
    hit = find_blocking_run(db_with_runs, compute_key("Gamma", "Engineer", "USA"))
    assert hit is None


def test_find_blocking_run_treats_dry_run_as_blocking(db_with_runs):
    # A dry-run attempt counts as "we already showed up there" — a real
    # submit on top of it would still look like a double-apply to the
    # recruiter.
    hit = find_blocking_run(db_with_runs, compute_key("Delta", "Engineer", "USA"))
    assert hit is not None


def test_find_blocking_run_handles_unknown_key(db_with_runs):
    hit = find_blocking_run(db_with_runs, compute_key("Nobody", "Job", "Nowhere"))
    assert hit is None


def test_find_blocking_run_handles_empty_key(db_with_runs):
    assert find_blocking_run(db_with_runs, "") is None


def test_is_duplicate_wrapper(db_with_runs):
    dup, run = is_duplicate(db_with_runs, "Acme", "Engineer", "USA")
    assert dup is True
    assert run is not None
    no_dup, no_run = is_duplicate(db_with_runs, "Nobody", "Job", "Nowhere")
    assert no_dup is False
    assert no_run is None
