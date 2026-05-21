"""SQLAlchemy database models for job tracking."""

from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, Text, Boolean, JSON, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from config import settings

Base = declarative_base()


def _utc_iso(dt: Optional[datetime]) -> Optional[str]:
    """Serialize a naive UTC datetime as an ISO string the browser parses
    as UTC. Naive isoformat() output has no offset, so JS ``new Date()``
    silently treats it as local time. Stamp tzinfo=UTC before formatting.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


class Job(Base):
    """Database model for job listings."""
    
    __tablename__ = "jobs"
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(100), unique=True, nullable=False, index=True)
    
    # Basic information
    title = Column(String(200), nullable=False, index=True)
    company = Column(String(200), nullable=False, index=True)
    location = Column(String(200), nullable=False)
    url = Column(Text, nullable=True)
    
    # Job details
    description = Column(Text, nullable=True)
    requirements = Column(JSON, nullable=True)  # Store as JSON array
    qualifications = Column(JSON, nullable=True)  # Store as JSON array
    responsibilities = Column(JSON, nullable=True)  # Store as JSON array
    benefits = Column(JSON, nullable=True)  # Store as JSON array
    
    # Employment information
    job_type = Column(String(50), nullable=True)
    experience_level = Column(String(50), nullable=True)
    salary_range = Column(String(100), nullable=True)
    employment_type = Column(String(100), nullable=True)
    
    # Company information
    industry = Column(String(100), nullable=True)
    company_size = Column(String(50), nullable=True)
    
    # Metadata
    posted_date = Column(String(50), nullable=True)
    application_deadline = Column(String(50), nullable=True)
    applicants_count = Column(String(50), nullable=True)
    
    # Tracking information
    scraped_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    source = Column(String(50), default="LinkedIn", nullable=False)
    status = Column(String(50), default="new", nullable=False, index=True)
    
    # Analysis results
    keywords = Column(JSON, nullable=True)  # Store as JSON array
    skills = Column(JSON, nullable=True)  # Store as JSON array
    resume_match_score = Column(Float, nullable=True, index=True)
    match_reasons = Column(JSON, nullable=True)  # Store as JSON array
    
    # Custom fields
    notes = Column(Text, nullable=True)
    tags = Column(JSON, nullable=True)  # Store as JSON array
    
    # Tracking fields
    viewed = Column(Boolean, default=False)
    applied = Column(Boolean, default=False)
    applied_date = Column(DateTime, nullable=True)
    
    # Create indexes for common queries
    __table_args__ = (
        Index('idx_company_title', 'company', 'title'),
        Index('idx_scraped_date', 'scraped_at'),
        Index('idx_match_score', 'resume_match_score'),
    )
    
    def __repr__(self):
        return f"<Job(id={self.id}, title='{self.title}', company='{self.company}')>"
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            'id': self.id,
            'job_id': self.job_id,
            'title': self.title,
            'company': self.company,
            'location': self.location,
            'url': self.url,
            'description': self.description,
            'requirements': self.requirements,
            'qualifications': self.qualifications,
            'responsibilities': self.responsibilities,
            'benefits': self.benefits,
            'job_type': self.job_type,
            'experience_level': self.experience_level,
            'salary_range': self.salary_range,
            'employment_type': self.employment_type,
            'industry': self.industry,
            'company_size': self.company_size,
            'posted_date': self.posted_date,
            'application_deadline': self.application_deadline,
            'applicants_count': self.applicants_count,
            'scraped_at': _utc_iso(self.scraped_at),
            'last_updated': _utc_iso(self.last_updated),
            'source': self.source,
            'status': self.status,
            'keywords': self.keywords,
            'skills': self.skills,
            'resume_match_score': self.resume_match_score,
            'match_reasons': self.match_reasons,
            'notes': self.notes,
            'tags': self.tags,
            'viewed': self.viewed,
            'applied': self.applied,
            'applied_date': _utc_iso(self.applied_date)
        }


class SearchRun(Base):
    """Database model for search runs."""
    
    __tablename__ = "search_runs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    search_id = Column(String(100), unique=True, nullable=False, index=True)
    
    # Search parameters
    keywords = Column(String(500), nullable=False)
    location = Column(String(200), nullable=False)
    job_type = Column(String(50), nullable=True)
    experience_level = Column(String(50), nullable=True)
    remote = Column(Boolean, nullable=True)
    posted_within = Column(String(20), nullable=True)
    
    # Results
    total_results = Column(Integer, default=0)
    jobs_scraped = Column(Integer, default=0)
    jobs_matched = Column(Integer, default=0)
    
    # Timing
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    
    # Status
    status = Column(String(50), default="running", nullable=False)  # running, completed, failed
    error_message = Column(Text, nullable=True)
    
    def __repr__(self):
        return f"<SearchRun(id={self.id}, keywords='{self.keywords}', status='{self.status}')>"
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            'id': self.id,
            'search_id': self.search_id,
            'keywords': self.keywords,
            'location': self.location,
            'job_type': self.job_type,
            'experience_level': self.experience_level,
            'remote': self.remote,
            'posted_within': self.posted_within,
            'total_results': self.total_results,
            'jobs_scraped': self.jobs_scraped,
            'jobs_matched': self.jobs_matched,
            'started_at': _utc_iso(self.started_at),
            'completed_at': _utc_iso(self.completed_at),
            'duration_seconds': self.duration_seconds,
            'status': self.status,
            'error_message': self.error_message
        }


class UserProfile(Base):
    """Database model for user profile and preferences."""
    
    __tablename__ = "user_profile"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Profile information
    name = Column(String(200), nullable=True)
    email = Column(String(200), nullable=True)
    resume_text = Column(Text, nullable=True)
    resume_file_path = Column(String(500), nullable=True)
    
    # Skills and preferences
    skills = Column(JSON, nullable=True)  # Store as JSON array
    preferred_locations = Column(JSON, nullable=True)  # Store as JSON array
    preferred_job_types = Column(JSON, nullable=True)  # Store as JSON array
    search_roles = Column(JSON, nullable=True)  # Roles to scrape (overrides job_search_config.json)
    minimum_salary = Column(String(50), nullable=True)
    
    # Search preferences. ``search_frequency_minutes`` is the canonical knob;
    # it lets us pick sub-hour cadences (down to single-minute for testing).
    # The legacy ``search_frequency_hours`` column stays as a fallback so old
    # rows / .env-bootstrapped values keep working until we explicitly retire
    # them. Backend resolution: minutes wins when non-null/positive, else
    # hours * 60.
    auto_search_enabled = Column(Boolean, default=False)
    search_frequency_hours = Column(Integer, default=24)
    search_frequency_minutes = Column(Integer, nullable=True)
    last_auto_search = Column(DateTime, nullable=True)
    
    # Notification preferences
    email_notifications = Column(Boolean, default=False)
    min_match_score_alert = Column(Float, default=80.0)

    # Feature flags / scraper toggles (persisted; UI-editable)
    enable_resume_matching = Column(Boolean, default=True)
    headless_browser = Column(Boolean, default=True)
    browser_timeout = Column(Integer, default=30000)

    # Secrets (DB-first, .env fallback). Stored plaintext on the local SQLite
    # file — single-user threat model. UI accepts edits via /api/settings;
    # quick_search.py copies these into os.environ at scrape time.
    openai_api_key = Column(Text, nullable=True)
    groq_api_key = Column(Text, nullable=True)
    linkedin_email = Column(String(200), nullable=True)
    linkedin_password = Column(Text, nullable=True)

    # Resumable scraper progress (Option A: checkpoint per category).
    # last_completed_category_index is -1 when no run is in flight; otherwise
    # the index of the last fully-finished category in the most recent
    # search_roles list. pending_search_started_at marks when this in-flight
    # run began so the UI/scraper can ignore stale checkpoints.
    last_completed_category_index = Column(Integer, default=-1)
    pending_search_started_at = Column(DateTime, nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<UserProfile(id={self.id}, name='{self.name}')>"


class AnalysisCache(Base):
    """Database model for caching analysis results."""
    
    __tablename__ = "analysis_cache"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(100), nullable=False, index=True)
    
    # Analysis data
    analysis_type = Column(String(50), nullable=False)  # resume_match, keyword_extraction, etc.
    analysis_result = Column(JSON, nullable=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    
    # Create compound index
    __table_args__ = (
        Index('idx_job_analysis', 'job_id', 'analysis_type'),
    )
    
    def __repr__(self):
        return f"<AnalysisCache(job_id='{self.job_id}', type='{self.analysis_type}')>"


class Followup(Base):
    """Reminder linked to a job."""
    __tablename__ = "followups"

    id = Column(Integer, primary_key=True)
    job_id = Column(String(100), nullable=False, index=True)
    due_at = Column(DateTime, nullable=False)
    note = Column(Text, nullable=True)
    done = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "job_id": self.job_id,
            "due_at": _utc_iso(self.due_at),
            "note": self.note,
            "done": bool(self.done),
            "created_at": _utc_iso(self.created_at),
        }


class InterviewEvent(Base):
    """Interview scheduled for a job."""
    __tablename__ = "interview_events"

    id = Column(Integer, primary_key=True)
    job_id = Column(String(100), nullable=False, index=True)
    stage = Column(String(50), nullable=False)  # phone, tech, onsite, offer, …
    scheduled_at = Column(DateTime, nullable=False)  # stored as UTC
    location = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    interviewer_tz = Column(String(64), nullable=True)  # IANA tz, e.g. "America/New_York"
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "job_id": self.job_id,
            "stage": self.stage,
            "scheduled_at": _utc_iso(self.scheduled_at),
            "location": self.location,
            "notes": self.notes,
            "interviewer_tz": self.interviewer_tz,
            "created_at": _utc_iso(self.created_at),
        }


# Create engine and session
engine = create_engine(settings.database_url, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully")


def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


if __name__ == "__main__":
    # Initialize database
    init_db()