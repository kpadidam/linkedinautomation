"""Pytest config + shared fixtures.

We use a temp SQLite DB per test so the production ``linkedin_jobs.db``
never gets touched. The patching has to happen BEFORE database.models is
imported, hence the module-level ``os.environ`` flip.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest

# Make sure tests run against a temp DB, not the operator's live one.
_TMP_DB = Path(tempfile.gettempdir()) / "linkedin_jobs_test.db"
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_TMP_DB}")

# Ensure the project root is on sys.path so 'from services.ats import ...'
# works regardless of how pytest is invoked.
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


@pytest.fixture
def temp_db_session():
    """Yield a session bound to a fresh in-memory SQLite. Each test
    gets a clean slate — no fixture cross-contamination."""

    # Import inside the fixture so the temp DATABASE_URL env wins.
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from database.models import Base

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def fake_profile():
    """Lightweight stand-in for ``UserProfile`` — adapters/services
    only ever read attributes, so a SimpleNamespace works."""

    from types import SimpleNamespace

    return SimpleNamespace(
        # Standard fields used by adapters via getattr.
        name="Karthik Reddy Padidam",
        email="karthik@example.com",
        phone="+15551234567",
        linkedin_url="https://linkedin.com/in/karthik",
        years_experience=5,
        resume_text="Backend engineer with Python + AWS",
        resume_file_path=None,
        # Auto-apply gates.
        auto_apply_enabled=True,
        daily_apply_cap=15,
        quiet_hours_start=23,
        quiet_hours_end=7,
        last_apply_at=None,
        circuit_tripped=False,
        circuit_tripped_at=None,
        circuit_tripped_reason=None,
        circuit_consecutive_failures=0,
        apply_browser_mode="chromium_ephemeral",
    )


@pytest.fixture
def fake_job():
    """Lightweight stand-in for ``Job``."""

    from types import SimpleNamespace

    return SimpleNamespace(
        job_id="test-123",
        title="Senior Backend Engineer",
        company="Acme Corp",
        location="United States (Remote)",
        url="https://example.com/jobs/123",
        description="We need a backend engineer.",
        salary_range="$160,000 - $200,000",
        applied=False,
    )
