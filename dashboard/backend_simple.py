"""
Simple FastAPI server for the dashboard with minimal dependencies
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import json
import os

# Request Models
class SearchRequest(BaseModel):
    keywords: str
    location: str
    jobType: Optional[str] = "full-time"
    experience: Optional[str] = None
    aiMatching: bool = True
    googleSheets: bool = True
    limit: int = 50

# Create FastAPI app
app = FastAPI(
    title="Job Automator AI API",
    description="Backend API for LinkedIn Job Automation Dashboard",
    version="1.0.0"
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
if os.path.exists("css"):
    app.mount("/css", StaticFiles(directory="css"), name="css")
if os.path.exists("js"):
    app.mount("/js", StaticFiles(directory="js"), name="js")

# Serve dashboard
@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    """Serve the main dashboard HTML"""
    with open("index.html", "r") as f:
        return f.read()

# Mock data storage
mock_jobs = []
search_counter = 0

# API Routes
@app.get("/api/dashboard/stats")
async def get_dashboard_stats():
    """Get dashboard statistics"""
    return {
        "totalJobs": len(mock_jobs),
        "activeSearches": 0,
        "averageMatch": 78.5,
        "sheetsSynced": 42,
        "recentActivity": [
            {
                "type": "success",
                "title": "Senior Developer at Tech Corp",
                "description": "95% match",
                "time": "2 hours ago"
            },
            {
                "type": "info",
                "title": "Synced 23 jobs to Google Sheets",
                "description": "",
                "time": "5 hours ago"
            }
        ]
    }

@app.post("/api/jobs/search")
async def search_jobs(request: SearchRequest):
    """Start a new job search"""
    global search_counter
    search_counter += 1
    
    # Generate mock jobs
    companies = ['Google', 'Microsoft', 'Amazon', 'Apple', 'Meta', 'Netflix']
    titles = ['Senior Developer', 'Software Engineer', 'Full Stack Developer']
    
    new_jobs = []
    for i in range(min(request.limit, 10)):
        job = {
            "id": f"job_{datetime.now().timestamp()}_{i}",
            "title": titles[i % len(titles)],
            "company": companies[i % len(companies)],
            "location": request.location,
            "matchScore": 70 + (i * 3),
            "status": "new",
            "postedDate": f"{i + 1} days ago",
            "description": "Amazing job opportunity...",
            "salary": f"${100 + i*10}k - ${150 + i*10}k"
        }
        new_jobs.append(job)
        mock_jobs.append(job)
    
    return {
        "success": True,
        "message": "Search completed",
        "searchId": f"search_{search_counter}",
        "jobsFound": len(new_jobs)
    }

@app.get("/api/jobs/recent")
async def get_recent_jobs(limit: int = 50):
    """Get recent jobs"""
    return {
        "success": True,
        "count": len(mock_jobs),
        "jobs": mock_jobs[-limit:]
    }

@app.get("/api/jobs/{job_id}")
async def get_job_details(job_id: str):
    """Get job details"""
    # Find job in mock data
    job = next((j for j in mock_jobs if j["id"] == job_id), None)
    
    if not job:
        # Return mock job
        job = {
            "id": job_id,
            "title": "Senior Python Developer",
            "company": "Tech Corp",
            "location": "San Francisco, CA",
            "salary": "$150k - $200k",
            "applicants": "45 applicants",
            "description": "We are looking for a talented Senior Python Developer...",
            "skills": ["Python", "Django", "PostgreSQL", "AWS"],
            "matchScore": 92,
            "recommendations": [
                "Strong match with your Python expertise",
                "Consider highlighting your Django projects"
            ],
            "interviewTips": [
                "Prepare examples of scalable Python applications",
                "Review Django best practices"
            ]
        }
    
    return job

@app.post("/api/jobs/{job_id}/save")
async def save_job(job_id: str):
    """Save a job"""
    return {"success": True, "message": "Job saved"}

@app.post("/api/jobs/{job_id}/apply")
async def mark_applied(job_id: str):
    """Mark job as applied"""
    # Update job status in mock data
    for job in mock_jobs:
        if job["id"] == job_id:
            job["status"] = "applied"
            break
    
    return {"success": True, "message": "Marked as applied"}

@app.post("/api/export/sheets")
async def export_to_sheets():
    """Export to Google Sheets"""
    return {
        "success": True,
        "sheetsUrl": "https://docs.google.com/spreadsheets/d/example",
        "jobsExported": len(mock_jobs)
    }

@app.get("/api/sheets/data")
async def get_sheets_data():
    """Get sheets data"""
    return {
        "success": True,
        "data": mock_jobs[:10],
        "rowCount": len(mock_jobs)
    }

@app.post("/api/profile/resume")
async def upload_resume():
    """Upload resume"""
    return {
        "success": True,
        "analysis": {
            "skills": ["Python", "JavaScript", "React", "AWS"],
            "textLength": 2500,
            "matchingKeywords": ["Developer", "Engineer", "Full Stack"]
        }
    }

@app.get("/api/health")
async def health_check():
    """Health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "mockJobs": len(mock_jobs)
    }

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Job Automator API Server (Simple Mode)...")
    print("📊 Dashboard available at: http://localhost:8000")
    print("📝 API docs available at: http://localhost:8000/docs")
    print("\nThis is a simplified version with mock data.")
    print("The dashboard will work but won't connect to real LinkedIn or Google Sheets.\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)