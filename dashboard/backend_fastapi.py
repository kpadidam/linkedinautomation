"""
FastAPI server to connect the HTML dashboard with LinkedIn scraper and Google Sheets
"""

from fastapi import FastAPI, HTTPException, File, UploadFile, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.google_sheets_service import GoogleSheetsService
from services.resume_matcher import ResumeMatcherService
from scrapers.linkedin_scraper_playwright import LinkedInScraperPlaywright
from database.db_manager import DatabaseManager
from models.job_model import JobListing, JobSearchResult
from datetime import datetime
import asyncio
import uvicorn
from contextlib import asynccontextmanager

# Request/Response Models
class SearchRequest(BaseModel):
    keywords: str
    location: str
    jobType: Optional[str] = "full-time"
    experience: Optional[str] = None
    aiMatching: bool = True
    googleSheets: bool = True
    limit: int = 50

class JobStatusUpdate(BaseModel):
    status: str
    notes: Optional[str] = None

class DashboardStats(BaseModel):
    totalJobs: int
    activeSearches: int
    averageMatch: float
    sheetsSynced: int
    recentActivity: List[Dict[str, Any]]

class ExportRequest(BaseModel):
    job_ids: Optional[List[str]] = None
    export_all: bool = False

# Initialize services globally
sheets_service = GoogleSheetsService()
resume_matcher = ResumeMatcherService()
job_db = DatabaseManager()
active_scrapers = {}  # Track active scraping sessions

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Starting Job Automator API Server...")
    print("📊 Dashboard available at: http://localhost:8000")
    print("\n✅ Make sure to:")
    print("1. Set up your Google Sheets credentials")
    print("2. Configure your OpenAI/Groq API keys in config.py")
    print("3. Have Chrome/Chromium installed for web scraping")
    yield
    # Shutdown
    print("Shutting down...")
    # Clean up any active scrapers
    for scraper_id in active_scrapers:
        if active_scrapers[scraper_id]:
            await active_scrapers[scraper_id].close()

# Create FastAPI app
app = FastAPI(
    title="Job Automator AI API",
    description="Backend API for LinkedIn Job Automation Dashboard",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for dashboard
app.mount("/css", StaticFiles(directory="css"), name="css")
app.mount("/js", StaticFiles(directory="js"), name="js")
app.mount("/assets", StaticFiles(directory="assets", check_dir=False), name="assets")

# Serve dashboard
@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    """Serve the main dashboard HTML"""
    with open("index.html", "r") as f:
        return f.read()

# API Routes
@app.get("/api/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats():
    """Get dashboard statistics from database and Google Sheets"""
    try:
        # Get stats from database
        recent_jobs = await asyncio.to_thread(job_db.get_recent_jobs, limit=100)
        
        # Calculate statistics
        total_jobs = len(recent_jobs) if recent_jobs else 0
        avg_match = 0
        if recent_jobs:
            matches = [job.resume_match_score for job in recent_jobs if job.resume_match_score]
            avg_match = sum(matches) / len(matches) if matches else 0
        
        # Count active searches
        active_searches = len(active_scrapers)
        
        # Get sheets sync info
        sheets_info = {}
        if sheets_service.sheets_id:
            sheets_info = await asyncio.to_thread(sheets_service.get_spreadsheet_info)
        sheets_synced = sheets_info.get('total_rows', 0) if sheets_info else 0
        
        return DashboardStats(
            totalJobs=total_jobs,
            activeSearches=active_searches,
            averageMatch=round(avg_match, 1),
            sheetsSynced=sheets_synced,
            recentActivity=await get_recent_activity()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/jobs/search")
async def search_jobs(
    request: SearchRequest,
    background_tasks: BackgroundTasks
):
    """Start a new job search"""
    try:
        search_id = f"search_{datetime.now().timestamp()}"
        
        # Start search in background
        background_tasks.add_task(
            run_job_search,
            search_id,
            request
        )
        
        return {
            "success": True,
            "message": "Search started",
            "searchId": search_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def run_job_search(search_id: str, request: SearchRequest):
    """Background task to run job search"""
    scraper = None
    try:
        # Initialize scraper
        scraper = LinkedInScraperPlaywright(headless=True)
        active_scrapers[search_id] = scraper
        
        # Run the search
        jobs = await scraper.search_jobs(
            keywords=request.keywords,
            location=request.location,
            job_type=request.jobType,
            limit=request.limit
        )
        
        # Process each job
        for job_data in jobs:
            # Create JobListing object
            job = JobListing(**job_data)
            
            # Calculate match score if AI matching enabled
            if request.aiMatching:
                analysis = await asyncio.to_thread(
                    resume_matcher.analyze_job_fit,
                    job_description=job.description,
                    job_requirements=job.requirements
                )
                job.resume_match_score = analysis.overall_match_score
                job.match_reasons = analysis.matching_skills
            
            # Save to database
            await asyncio.to_thread(job_db.save_job, job)
            
            # Sync to Google Sheets if enabled
            if request.googleSheets and sheets_service.sheets_id:
                await asyncio.to_thread(sheets_service.append_job, job)
        
    except Exception as e:
        print(f"Search error: {e}")
    finally:
        # Clean up
        if scraper:
            await scraper.close()
        if search_id in active_scrapers:
            del active_scrapers[search_id]

@app.get("/api/jobs/search/{search_id}/status")
async def get_search_status(search_id: str):
    """Get status of a search job"""
    is_active = search_id in active_scrapers
    return {
        "searchId": search_id,
        "active": is_active,
        "status": "running" if is_active else "completed"
    }

@app.get("/api/jobs/recent")
async def get_recent_jobs(limit: int = 50, offset: int = 0):
    """Get recent jobs from database"""
    try:
        jobs = await asyncio.to_thread(
            job_db.get_recent_jobs,
            limit=limit,
            offset=offset
        )
        
        return {
            "success": True,
            "count": len(jobs) if jobs else 0,
            "jobs": [job.dict() for job in jobs] if jobs else []
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/jobs/{job_id}")
async def get_job_details(job_id: str):
    """Get detailed job information"""
    try:
        job = await asyncio.to_thread(job_db.get_job_by_id, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Get AI analysis if not already done
        if not job.resume_match_score:
            analysis = await asyncio.to_thread(
                resume_matcher.analyze_job_fit,
                job_description=job.description,
                job_requirements=job.requirements
            )
            job.resume_match_score = analysis.overall_match_score
            job.match_reasons = analysis.matching_skills
            job.skills = analysis.technical_skills
            
            # Update in database
            await asyncio.to_thread(job_db.update_job, job)
        
        return job.dict()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/jobs/{job_id}/save")
async def save_job(job_id: str):
    """Save a job for later"""
    try:
        job = await asyncio.to_thread(job_db.get_job_by_id, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        job.status = "saved"
        await asyncio.to_thread(job_db.update_job, job)
        
        return {"success": True, "message": "Job saved"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/jobs/{job_id}/apply")
async def mark_applied(job_id: str, update: Optional[JobStatusUpdate] = None):
    """Mark job as applied"""
    try:
        job = await asyncio.to_thread(job_db.get_job_by_id, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        job.status = update.status if update else "applied"
        job.applied = True
        job.applied_date = datetime.now()
        if update and update.notes:
            job.notes = update.notes
        
        await asyncio.to_thread(job_db.update_job, job)
        
        return {"success": True, "message": "Job status updated"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/export/sheets")
async def export_to_sheets(request: ExportRequest):
    """Export jobs to Google Sheets"""
    try:
        if not sheets_service.sheets_id:
            raise HTTPException(status_code=400, detail="Google Sheets not configured")
        
        # Get jobs to export
        if request.export_all or not request.job_ids:
            jobs = await asyncio.to_thread(job_db.get_recent_jobs, limit=100)
        else:
            jobs = []
            for job_id in request.job_ids:
                job = await asyncio.to_thread(job_db.get_job_by_id, job_id)
                if job:
                    jobs.append(job)
        
        # Export to sheets
        success_count = 0
        for job in jobs:
            success = await asyncio.to_thread(sheets_service.append_job, job)
            if success:
                success_count += 1
        
        sheets_url = f"https://docs.google.com/spreadsheets/d/{sheets_service.sheets_id}"
        
        return {
            "success": True,
            "sheetsUrl": sheets_url,
            "jobsExported": success_count,
            "totalJobs": len(jobs)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sheets/data")
async def get_sheets_data():
    """Get current data from Google Sheets"""
    try:
        if not sheets_service.sheets_id:
            raise HTTPException(status_code=400, detail="Google Sheets not configured")
        
        data = await asyncio.to_thread(sheets_service.get_all_data)
        
        return {
            "success": True,
            "data": data if data else [],
            "rowCount": len(data) if data else 0
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/profile/resume")
async def upload_resume(file: UploadFile = File(...)):
    """Upload and analyze resume"""
    try:
        # Validate file type
        if not file.filename.endswith(('.pdf', '.docx', '.doc')):
            raise HTTPException(status_code=400, detail="Invalid file type. Upload PDF or Word document")
        
        # Save file temporarily
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            content = await file.read()
            tmp.write(content)
            tmp.flush()
            
            # Extract text and analyze
            resume_text = await asyncio.to_thread(
                resume_matcher.extract_text_from_pdf,
                tmp.name
            )
            skills = await asyncio.to_thread(
                resume_matcher.extract_skills,
                resume_text
            )
            
            # Update resume profile
            await asyncio.to_thread(
                resume_matcher.update_profile,
                resume_text=resume_text
            )
            
            os.unlink(tmp.name)  # Delete temp file
        
        return {
            "success": True,
            "filename": file.filename,
            "analysis": {
                "skills": skills,
                "textLength": len(resume_text),
                "matchingKeywords": skills[:10]
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "database": job_db is not None,
            "sheets": sheets_service.sheets_id is not None,
            "ai": resume_matcher is not None,
            "active_searches": len(active_scrapers)
        }
    }

# WebSocket endpoint for real-time updates (optional)
@app.websocket("/ws")
async def websocket_endpoint(websocket):
    """WebSocket for real-time updates"""
    await websocket.accept()
    try:
        while True:
            # Send periodic updates
            await asyncio.sleep(5)
            stats = await get_dashboard_stats()
            await websocket.send_json({
                "type": "stats_update",
                "data": stats.dict()
            })
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        await websocket.close()

# Helper functions
async def get_recent_activity() -> List[Dict[str, Any]]:
    """Get recent activity for dashboard"""
    activities = []
    
    try:
        # Get recent high-match jobs
        recent_jobs = await asyncio.to_thread(job_db.get_recent_jobs, limit=10)
        
        if recent_jobs:
            for job in recent_jobs:
                if job.resume_match_score and job.resume_match_score > 85:
                    activities.append({
                        "type": "success",
                        "title": f"{job.title} at {job.company}",
                        "description": f"{job.resume_match_score}% match",
                        "time": format_time_ago(job.scraped_at)
                    })
        
        # Add sheets sync activity
        if sheets_service.sheets_id:
            activities.append({
                "type": "info",
                "title": "Google Sheets Connected",
                "description": "Ready to sync jobs",
                "time": "Active"
            })
    except Exception as e:
        print(f"Error getting recent activity: {e}")
    
    return activities[:5]

def format_time_ago(dt: datetime) -> str:
    """Format datetime as 'X hours/days ago'"""
    if not dt:
        return "recently"
    
    delta = datetime.now() - dt
    if delta.days > 0:
        return f'{delta.days} day{"s" if delta.days > 1 else ""} ago'
    
    hours = delta.seconds // 3600
    if hours > 0:
        return f'{hours} hour{"s" if hours > 1 else ""} ago'
    
    minutes = delta.seconds // 60
    return f'{minutes} minute{"s" if minutes > 1 else ""} ago'

if __name__ == "__main__":
    # Run with uvicorn for better performance
    uvicorn.run(
        "backend_fastapi:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Auto-reload on code changes
        log_level="info"
    )