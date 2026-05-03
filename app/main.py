"""FastAPI application for LinkedIn Job Automation System."""

import logging
import logging.config
import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from config import settings, STATIC_DIR, LOGGING_CONFIG
from database.models import get_db, Job, SearchRun
from database.db_manager import db_manager
from scrapers.linkedin_scraper import LinkedInScraper, JobSearchParams
from services.google_sheets_service import GoogleSheetsService
from services.resume_matcher import ResumeMatcherService, ResumeProfile
from services.session_manager import SessionManager
from models.job_model import JobListing, JobStatus
import os as _os
session_manager = SessionManager(project_root=_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))

# Configure logging
logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Automated LinkedIn job scraping and Google Sheets logging system"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Initialize services
google_sheets_service = None
resume_matcher_service = None


# Request/Response models
class JobSearchRequest(BaseModel):
    """Request model for job search."""
    keywords: str
    location: str = settings.default_location
    job_type: Optional[str] = None
    experience_level: Optional[str] = None
    remote: Optional[bool] = None
    posted_within: Optional[str] = "24h"
    max_results: int = 20
    enable_matching: bool = True
    save_to_sheets: bool = True


class JobSearchResponse(BaseModel):
    """Response model for job search."""
    search_id: str
    status: str
    message: str
    jobs_found: int = 0
    sheet_url: Optional[str] = None


class JobUpdateRequest(BaseModel):
    """Request model for updating job status, notes, and labels."""
    status: Optional[str] = None
    notes: Optional[str] = None
    labels: Optional[List[str]] = None


class ProfileUpdateRequest(BaseModel):
    """Request model for updating user profile."""
    name: Optional[str] = None
    email: Optional[str] = None
    resume_text: Optional[str] = None
    skills: Optional[List[str]] = None
    preferred_locations: Optional[List[str]] = None
    search_roles: Optional[List[str]] = None


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    global google_sheets_service, resume_matcher_service
    
    try:
        # Initialize Google Sheets service
        if settings.google_sheets_id:
            google_sheets_service = GoogleSheetsService()
            logger.info("Google Sheets service initialized")
        
        # Initialize resume matcher
        resume_matcher_service = ResumeMatcherService()
        logger.info("Resume matcher service initialized")
        
        logger.info(f"{settings.app_name} started successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main web interface."""
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return HTMLResponse(content="<h1>LinkedIn Job Automation API</h1><p>Visit /docs for API documentation</p>")


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app_name": settings.app_name,
        "version": settings.app_version,
        "timestamp": datetime.now().isoformat()
    }


@app.post("/api/search", response_model=JobSearchResponse)
async def search_jobs(
    request: JobSearchRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Start a new job search.
    
    This endpoint initiates an asynchronous job search that:
    1. Scrapes LinkedIn for matching jobs
    2. Analyzes jobs with AI for resume matching
    3. Saves results to database and Google Sheets
    """
    try:
        # Create search run record
        search_params = request.dict()
        search_run = db_manager.add_search_run(search_params, db)
        
        # Start async search in background
        background_tasks.add_task(
            perform_job_search,
            search_run.search_id,
            search_params
        )
        
        # Get sheet URL if available
        sheet_url = google_sheets_service.get_spreadsheet_url() if google_sheets_service else None
        
        return JobSearchResponse(
            search_id=search_run.search_id,
            status="started",
            message=f"Job search started for '{request.keywords}' in {request.location}",
            sheet_url=sheet_url
        )
        
    except Exception as e:
        logger.error(f"Failed to start job search: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def perform_job_search(search_id: str, params: Dict[str, Any]):
    """
    Perform the actual job search (runs in background).
    
    Args:
        search_id: Search run ID
        params: Search parameters
    """
    db = next(get_db())
    
    try:
        logger.info(f"Starting job search {search_id}")
        
        # Initialize scraper
        scraper = LinkedInScraper()
        
        # Create search parameters
        search_params = JobSearchParams(**params)
        
        # Perform search
        jobs = await scraper.search_jobs(search_params)
        
        # Update search run
        db_manager.update_search_run(
            search_id, db,
            total_results=len(jobs),
            jobs_scraped=len(jobs)
        )
        
        # Process each job
        matched_jobs = 0
        for job_data in jobs:
            try:
                # Create JobListing object
                job_listing = JobListing(**job_data)
                
                # Perform resume matching if enabled (also requires global feature flag)
                if settings.enable_resume_matching and params.get("enable_matching") and resume_matcher_service:
                    analysis = await resume_matcher_service.analyze_job_fit(job_listing)
                    job_listing.resume_match_score = analysis.overall_match_score
                    job_listing.keywords = analysis.technical_skills + analysis.soft_skills
                    job_listing.skills = analysis.technical_skills
                    
                    if analysis.overall_match_score >= 70:
                        matched_jobs += 1
                
                # Save to database
                db_manager.add_job(job_listing, db)
                
                # Save to Google Sheets if enabled
                if params.get("save_to_sheets") and google_sheets_service:
                    google_sheets_service.add_job(job_listing)
                
            except Exception as e:
                logger.error(f"Failed to process job: {e}")
                continue
        
        # Update search run as completed
        db_manager.update_search_run(
            search_id, db,
            status="completed",
            jobs_matched=matched_jobs
        )
        
        logger.info(f"Search {search_id} completed: {len(jobs)} jobs found, {matched_jobs} matched")
        
    except Exception as e:
        logger.error(f"Job search {search_id} failed: {e}")
        db_manager.update_search_run(
            search_id, db,
            status="failed",
            error_message=str(e)
        )
    finally:
        db.close()


@app.get("/api/search/{search_id}")
async def get_search_status(search_id: str, db: Session = Depends(get_db)):
    """Get the status of a search run."""
    search_run = db.query(SearchRun).filter_by(search_id=search_id).first()
    
    if not search_run:
        raise HTTPException(status_code=404, detail="Search not found")
    
    return search_run.to_dict()


@app.get("/api/jobs")
async def get_jobs(
    db: Session = Depends(get_db),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    status: Optional[str] = None,
    min_score: Optional[float] = None
):
    """Get all jobs with optional filters."""
    jobs = db_manager.get_all_jobs(db, limit, offset, status, min_score)
    return [job.to_dict() for job in jobs]


@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str, db: Session = Depends(get_db)):
    """Get a specific job by ID."""
    job = db_manager.get_job_by_id(job_id, db)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Mark as viewed
    db_manager.mark_job_viewed(job_id, db)
    
    return job.to_dict()


@app.put("/api/jobs/{job_id}")
async def update_job(
    job_id: str,
    request: JobUpdateRequest,
    db: Session = Depends(get_db)
):
    """Update job status, notes, and/or labels (any subset)."""
    job = db_manager.get_job_by_id(job_id, db)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if request.status is not None:
        job.status = request.status
        if request.status == "applied":
            job.applied = True
            job.applied_date = datetime.utcnow()
    if request.notes is not None:
        job.notes = request.notes
    if request.labels is not None:
        job.tags = request.labels

    db.commit()
    db.refresh(job)
    return {"status": "success", "job": job.to_dict()}


@app.get("/api/profile")
async def get_profile(db: Session = Depends(get_db)):
    """Get user profile."""
    profile = db_manager.get_or_create_user_profile(db)
    return {
        "name": profile.name,
        "email": profile.email,
        "skills": profile.skills,
        "preferred_locations": profile.preferred_locations,
        "search_roles": profile.search_roles,
        "auto_search_enabled": profile.auto_search_enabled
    }


@app.put("/api/profile")
async def update_profile(
    request: ProfileUpdateRequest,
    db: Session = Depends(get_db)
):
    """Update user profile."""
    updates = request.dict(exclude_unset=True)
    success = db_manager.update_user_profile(db, **updates)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update profile")
    
    # Update resume matcher if resume changed
    if request.resume_text:
        global resume_matcher_service
        resume_profile = ResumeProfile(
            resume_text=request.resume_text,
            skills=request.skills
        )
        resume_matcher_service = ResumeMatcherService(resume_profile)
    
    return {"status": "success", "message": "Profile updated"}


@app.get("/api/statistics")
async def get_statistics(db: Session = Depends(get_db)):
    """Get application statistics."""
    stats = db_manager.get_statistics(db)
    
    # Add sheet URL if available
    if google_sheets_service:
        stats["sheet_url"] = google_sheets_service.get_spreadsheet_url()
    
    return stats


@app.get("/api/searches")
async def get_recent_searches(
    db: Session = Depends(get_db),
    limit: int = Query(10, le=50)
):
    """Get recent search runs."""
    searches = db_manager.get_recent_searches(db, limit)
    return [search.to_dict() for search in searches]


@app.post("/api/sheets/create")
async def create_new_sheet():
    """Create a new Google Sheet for job tracking."""
    if not google_sheets_service:
        raise HTTPException(status_code=503, detail="Google Sheets service not configured")
    
    try:
        sheet_id = google_sheets_service.create_spreadsheet("LinkedIn Jobs")
        google_sheets_service.spreadsheet_id = sheet_id
        
        return {
            "status": "success",
            "sheet_id": sheet_id,
            "sheet_url": google_sheets_service.get_spreadsheet_url()
        }
    except Exception as e:
        logger.error(f"Failed to create sheet: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/cleanup")
async def cleanup_old_data(
    days: int = Query(30, ge=7, le=365),
    db: Session = Depends(get_db)
):
    """Clean up old data from database."""
    deleted = db_manager.cleanup_old_data(db, days)
    return {
        "status": "success",
        "deleted_records": deleted,
        "message": f"Cleaned up {deleted} records older than {days} days"
    }


# ============================================================
# Session control + log streaming
# ============================================================

@app.get("/api/sessions/status")
async def session_status():
    return session_manager.status()


@app.post("/api/sessions/start")
async def session_start():
    return await session_manager.start()


@app.post("/api/sessions/stop")
async def session_stop():
    return await session_manager.stop()


@app.get("/api/sessions/logs/stream")
async def session_logs_stream():
    async def event_generator():
        async for line in session_manager.stream():
            yield f"data: {line}\n\n"
    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ============================================================
# Followups + Interview events
# ============================================================
from database.models import Followup, InterviewEvent

class FollowupCreate(BaseModel):
    job_id: str
    due_at: datetime
    note: Optional[str] = None

class FollowupUpdate(BaseModel):
    due_at: Optional[datetime] = None
    note: Optional[str] = None
    done: Optional[bool] = None

class InterviewCreate(BaseModel):
    job_id: str
    stage: str
    scheduled_at: datetime
    location: Optional[str] = None
    notes: Optional[str] = None

class InterviewUpdate(BaseModel):
    stage: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    location: Optional[str] = None
    notes: Optional[str] = None


@app.get("/api/followups")
async def list_followups(job_id: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(Followup)
    if job_id:
        q = q.filter(Followup.job_id == job_id)
    return [f.to_dict() for f in q.order_by(Followup.due_at.asc()).all()]


@app.post("/api/followups")
async def create_followup(payload: FollowupCreate, db: Session = Depends(get_db)):
    f = Followup(job_id=payload.job_id, due_at=payload.due_at, note=payload.note, done=False)
    db.add(f); db.commit(); db.refresh(f)
    return f.to_dict()


@app.put("/api/followups/{fid}")
async def update_followup(fid: int, payload: FollowupUpdate, db: Session = Depends(get_db)):
    f = db.query(Followup).filter(Followup.id == fid).first()
    if not f: raise HTTPException(404, "Followup not found")
    for k, v in payload.dict(exclude_unset=True).items():
        setattr(f, k, v)
    db.commit(); db.refresh(f)
    return f.to_dict()


@app.delete("/api/followups/{fid}")
async def delete_followup(fid: int, db: Session = Depends(get_db)):
    f = db.query(Followup).filter(Followup.id == fid).first()
    if not f: raise HTTPException(404, "Followup not found")
    db.delete(f); db.commit()
    return {"status": "deleted"}


@app.get("/api/interviews")
async def list_interviews(job_id: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(InterviewEvent)
    if job_id:
        q = q.filter(InterviewEvent.job_id == job_id)
    return [e.to_dict() for e in q.order_by(InterviewEvent.scheduled_at.asc()).all()]


@app.post("/api/interviews")
async def create_interview(payload: InterviewCreate, db: Session = Depends(get_db)):
    e = InterviewEvent(
        job_id=payload.job_id, stage=payload.stage,
        scheduled_at=payload.scheduled_at, location=payload.location, notes=payload.notes,
    )
    db.add(e); db.commit(); db.refresh(e)
    return e.to_dict()


@app.put("/api/interviews/{eid}")
async def update_interview(eid: int, payload: InterviewUpdate, db: Session = Depends(get_db)):
    e = db.query(InterviewEvent).filter(InterviewEvent.id == eid).first()
    if not e: raise HTTPException(404, "Interview not found")
    for k, v in payload.dict(exclude_unset=True).items():
        setattr(e, k, v)
    db.commit(); db.refresh(e)
    return e.to_dict()


@app.delete("/api/interviews/{eid}")
async def delete_interview(eid: int, db: Session = Depends(get_db)):
    e = db.query(InterviewEvent).filter(InterviewEvent.id == eid).first()
    if not e: raise HTTPException(404, "Interview not found")
    db.delete(e); db.commit()
    return {"status": "deleted"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_config=LOGGING_CONFIG
    )