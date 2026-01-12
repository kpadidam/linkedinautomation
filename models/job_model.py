"""Pydantic models for job data."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, HttpUrl, validator
from enum import Enum


class JobType(str, Enum):
    """Job type enumeration."""
    FULL_TIME = "full-time"
    PART_TIME = "part-time"
    CONTRACT = "contract"
    TEMPORARY = "temporary"
    INTERNSHIP = "internship"
    VOLUNTEER = "volunteer"
    OTHER = "other"


class ExperienceLevel(str, Enum):
    """Experience level enumeration."""
    ENTRY = "entry"
    ASSOCIATE = "associate"
    MID_SENIOR = "mid-senior"
    DIRECTOR = "director"
    EXECUTIVE = "executive"


class JobStatus(str, Enum):
    """Job application status."""
    NEW = "new"
    VIEWED = "viewed"
    SAVED = "saved"
    APPLIED = "applied"
    INTERVIEWING = "interviewing"
    REJECTED = "rejected"
    OFFER = "offer"


class JobListing(BaseModel):
    """Model for a job listing."""
    
    # Basic Information
    job_id: str = Field(..., description="Unique job identifier")
    title: str = Field(..., description="Job title")
    company: str = Field(..., description="Company name")
    location: str = Field(..., description="Job location")
    url: Optional[HttpUrl] = Field(None, description="Job posting URL")
    
    # Job Details
    description: str = Field(default="", description="Full job description")
    requirements: List[str] = Field(default_factory=list, description="Job requirements")
    qualifications: List[str] = Field(default_factory=list, description="Required qualifications")
    responsibilities: List[str] = Field(default_factory=list, description="Job responsibilities")
    benefits: List[str] = Field(default_factory=list, description="Job benefits")
    
    # Employment Information
    job_type: Optional[JobType] = Field(None, description="Type of employment")
    experience_level: Optional[ExperienceLevel] = Field(None, description="Required experience level")
    level: Optional[int] = Field(None, description="Years of experience as numeric value")
    salary_range: Optional[str] = Field(None, description="Salary range if provided")
    employment_type: Optional[str] = Field(None, description="Employment type details")
    
    # Company Information
    industry: Optional[str] = Field(None, description="Industry sector")
    company_size: Optional[str] = Field(None, description="Company size")
    
    # Metadata
    posted_date: Optional[str] = Field(None, description="When job was posted")
    application_deadline: Optional[str] = Field(None, description="Application deadline")
    applicants_count: Optional[str] = Field(None, description="Number of applicants")
    
    # Tracking Information
    scraped_at: datetime = Field(default_factory=datetime.now, description="When job was scraped")
    source: str = Field(default="LinkedIn", description="Source of the job listing")
    status: JobStatus = Field(default=JobStatus.NEW, description="Application status")
    
    # Analysis Results
    keywords: List[str] = Field(default_factory=list, description="Extracted keywords")
    skills: List[str] = Field(default_factory=list, description="Required skills")
    resume_match_score: Optional[float] = Field(None, ge=0, le=100, description="Resume match percentage")
    match_reasons: List[str] = Field(default_factory=list, description="Reasons for match score")
    
    # Custom fields
    notes: Optional[str] = Field(None, description="Personal notes about the job")
    tags: List[str] = Field(default_factory=list, description="Custom tags")
    
    @validator("resume_match_score")
    def validate_match_score(cls, v):
        """Ensure match score is between 0 and 100."""
        if v is not None and (v < 0 or v > 100):
            raise ValueError("Resume match score must be between 0 and 100")
        return v
    
    @validator("scraped_at", pre=True)
    def parse_datetime(cls, v):
        """Parse datetime from string if necessary."""
        if isinstance(v, str):
            return datetime.fromisoformat(v)
        return v
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            HttpUrl: lambda v: str(v)
        }
        schema_extra = {
            "example": {
                "job_id": "12345",
                "title": "Senior Software Engineer",
                "company": "Tech Corp",
                "location": "San Francisco, CA",
                "url": "https://linkedin.com/jobs/12345",
                "job_type": "full-time",
                "experience_level": "mid-senior",
                "salary_range": "$150,000 - $200,000",
                "keywords": ["Python", "AWS", "Docker"],
                "resume_match_score": 85.5
            }
        }


class JobSearchResult(BaseModel):
    """Model for job search results."""
    
    search_id: str = Field(..., description="Unique search identifier")
    query: str = Field(..., description="Search query used")
    location: str = Field(..., description="Location searched")
    total_results: int = Field(..., description="Total number of results found")
    jobs: List[JobListing] = Field(default_factory=list, description="List of job listings")
    search_timestamp: datetime = Field(default_factory=datetime.now, description="When search was performed")
    search_duration_seconds: Optional[float] = Field(None, description="How long the search took")
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class JobAnalysis(BaseModel):
    """Model for job analysis results."""
    
    job_id: str = Field(..., description="Job identifier")
    
    # Keyword Analysis
    technical_skills: List[str] = Field(default_factory=list, description="Technical skills required")
    soft_skills: List[str] = Field(default_factory=list, description="Soft skills required")
    tools_technologies: List[str] = Field(default_factory=list, description="Tools and technologies mentioned")
    certifications: List[str] = Field(default_factory=list, description="Required certifications")
    
    # Match Analysis
    overall_match_score: float = Field(..., ge=0, le=100, description="Overall match percentage")
    skills_match_score: float = Field(..., ge=0, le=100, description="Skills match percentage")
    experience_match_score: float = Field(..., ge=0, le=100, description="Experience match percentage")
    
    # Recommendations
    missing_skills: List[str] = Field(default_factory=list, description="Skills you're missing")
    matching_skills: List[str] = Field(default_factory=list, description="Skills you have")
    recommendations: List[str] = Field(default_factory=list, description="Application recommendations")
    
    # AI Insights
    ai_summary: str = Field(..., description="AI-generated summary of the job")
    ai_fit_assessment: str = Field(..., description="AI assessment of job fit")
    interview_tips: List[str] = Field(default_factory=list, description="Interview preparation tips")
    
    analysis_timestamp: datetime = Field(default_factory=datetime.now, description="When analysis was performed")
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class GoogleSheetRow(BaseModel):
    """Model for Google Sheets row data."""
    
    date: str = Field(..., description="Date scraped (YYYY-MM-DD)")
    time: str = Field(..., description="Time scraped (HH:MM:SS)")
    role: str = Field(..., description="Job title/role")
    company: str = Field(..., description="Company name")
    location: str = Field(..., description="Job location")
    job_type: str = Field(default="", description="Type of job")
    level: int = Field(default=0, description="Years of experience as number")
    link: str = Field(..., description="Link to job posting")
    job_responsibilities: str = Field(..., description="Job responsibilities")
    preferred_skills: str = Field(default="", description="Preferred/required skills")
    matching_skills: str = Field(default="", description="Skills matching resume")
    role_match: float = Field(default=0, description="Role match percentage")
    salary: str = Field(default="Not specified", description="Salary range")
    posted: str = Field(default="", description="When job was posted")
    number_of_applicants: str = Field(default="", description="Number of applicants")
    
    @classmethod
    def from_job_listing(cls, job: JobListing) -> "GoogleSheetRow":
        """Create Google Sheet row from job listing."""
        scraped_dt = job.scraped_at
        
        # Format responsibilities for spreadsheet
        if job.responsibilities and isinstance(job.responsibilities, list) and len(job.responsibilities) > 0:
            # Join responsibilities with bullet points
            job_responsibilities = "\n• ".join(job.responsibilities[:5])  # Limit to 5
        else:
            job_responsibilities = job.description[:500] + "..." if len(job.description) > 500 else job.description
        
        # Handle job_type properly
        job_type_str = ""
        if job.job_type:
            if hasattr(job.job_type, 'value'):
                job_type_str = job.job_type.value
            else:
                job_type_str = str(job.job_type)
        
        # Extract preferred skills from requirements or use skills
        preferred_skills = ""
        if job.requirements and isinstance(job.requirements, list):
            # Filter for skill-related requirements
            skill_reqs = [req for req in job.requirements if any(word in req.lower() for word in ['skill', 'experience', 'knowledge', 'proficient'])]
            if skill_reqs:
                preferred_skills = ", ".join(skill_reqs[:3])
        if not preferred_skills and job.skills:
            preferred_skills = ", ".join(job.skills) if isinstance(job.skills, list) else str(job.skills)
        
        # Matching skills - skills that match the resume
        matching_skills = ""
        if job.match_reasons and isinstance(job.match_reasons, list):
            matching_skills = ", ".join(job.match_reasons[:5])
        elif job.skills and isinstance(job.skills, list):
            # For now, use extracted skills as matching skills
            matching_skills = ", ".join(job.skills[:5])
        
        return cls(
            date=scraped_dt.strftime("%Y-%m-%d"),
            time=scraped_dt.strftime("%H:%M:%S"),
            role=job.title,
            company=job.company,
            location=job.location,
            job_type=job_type_str,
            level=job.level if job.level is not None else 0,
            link=str(job.url) if job.url else "",
            job_responsibilities=job_responsibilities,
            preferred_skills=preferred_skills,
            matching_skills=matching_skills,
            role_match=job.resume_match_score or 0,
            salary=job.salary_range or "Not specified",
            posted=job.posted_date or "",
            number_of_applicants=job.applicants_count or ""
        )
    
    def to_list(self) -> List[Any]:
        """Convert to list for Google Sheets API."""
        return [
            self.date,
            self.time,
            self.role,
            self.company,
            self.location,
            self.job_type,
            self.level,
            self.link,
            self.job_responsibilities,
            self.preferred_skills,
            self.matching_skills,
            self.role_match,
            self.salary,
            self.posted,
            self.number_of_applicants
        ]
    
    @classmethod
    def get_headers(cls) -> List[str]:
        """Get headers for Google Sheets."""
        return [
            "Date",
            "Time",
            "Role",
            "Company",
            "Location",
            "Job Type",
            "Level",
            "Link",
            "Job Responsibilities:",
            "Preferred Skills",
            "Matching Skills",
            "Role Match %",
            "Salary",
            "Posted",
            "Number of Applicants"
        ]