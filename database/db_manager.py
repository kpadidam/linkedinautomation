"""Database manager for job tracking operations."""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
import uuid

from database.models import Job, SearchRun, UserProfile, AnalysisCache, get_db, init_db
from models.job_model import JobListing

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manager for database operations."""
    
    def __init__(self):
        """Initialize database manager."""
        init_db()
        logger.info("Database manager initialized")
    
    def add_job(self, job_listing: JobListing, db: Session) -> Optional[Job]:
        """
        Add a job to the database.
        
        Args:
            job_listing: JobListing object
            db: Database session
            
        Returns:
            Created Job object or None if duplicate
        """
        try:
            # Check for duplicate
            existing = db.query(Job).filter_by(job_id=job_listing.job_id).first()
            if existing:
                logger.info(f"Job {job_listing.job_id} already exists, updating")
                # Update existing job
                self._update_job(existing, job_listing)
                db.commit()
                return existing
            
            # Create new job
            job = Job(
                job_id=job_listing.job_id,
                title=job_listing.title,
                company=job_listing.company,
                location=job_listing.location,
                url=str(job_listing.url) if job_listing.url else None,
                description=job_listing.description,
                requirements=job_listing.requirements,
                qualifications=job_listing.qualifications,
                responsibilities=job_listing.responsibilities,
                benefits=job_listing.benefits,
                job_type=job_listing.job_type.value if job_listing.job_type else None,
                experience_level=job_listing.experience_level.value if job_listing.experience_level else None,
                salary_range=job_listing.salary_range,
                employment_type=job_listing.employment_type,
                industry=job_listing.industry,
                company_size=job_listing.company_size,
                posted_date=job_listing.posted_date,
                application_deadline=job_listing.application_deadline,
                applicants_count=job_listing.applicants_count,
                scraped_at=job_listing.scraped_at,
                source=job_listing.source,
                status=job_listing.status.value,
                keywords=job_listing.keywords,
                skills=job_listing.skills,
                resume_match_score=job_listing.resume_match_score,
                match_reasons=job_listing.match_reasons,
                notes=job_listing.notes,
                tags=job_listing.tags
            )
            
            db.add(job)
            db.commit()
            db.refresh(job)
            
            logger.info(f"Added job: {job.title} at {job.company}")
            return job
            
        except Exception as e:
            logger.error(f"Failed to add job: {e}")
            db.rollback()
            return None
    
    def _update_job(self, job: Job, job_listing: JobListing):
        """Update existing job with new data."""
        job.title = job_listing.title
        job.company = job_listing.company
        job.location = job_listing.location
        job.description = job_listing.description or job.description
        job.requirements = job_listing.requirements or job.requirements
        job.qualifications = job_listing.qualifications or job.qualifications
        job.salary_range = job_listing.salary_range or job.salary_range
        job.applicants_count = job_listing.applicants_count or job.applicants_count
        job.resume_match_score = job_listing.resume_match_score or job.resume_match_score
        job.keywords = job_listing.keywords or job.keywords
        job.skills = job_listing.skills or job.skills
        job.last_updated = datetime.utcnow()
    
    def get_job_by_id(self, job_id: str, db: Session) -> Optional[Job]:
        """Get job by ID."""
        return db.query(Job).filter_by(job_id=job_id).first()
    
    def get_all_jobs(self, db: Session, 
                     limit: int = 100, 
                     offset: int = 0,
                     status: Optional[str] = None,
                     min_score: Optional[float] = None) -> List[Job]:
        """
        Get all jobs with optional filters.
        
        Args:
            db: Database session
            limit: Maximum number of results
            offset: Offset for pagination
            status: Filter by status
            min_score: Minimum resume match score
            
        Returns:
            List of jobs
        """
        query = db.query(Job)
        
        if status:
            query = query.filter_by(status=status)
        
        if min_score is not None:
            query = query.filter(Job.resume_match_score >= min_score)
        
        return query.order_by(desc(Job.scraped_at)).limit(limit).offset(offset).all()
    
    def search_jobs(self, db: Session,
                   keywords: Optional[str] = None,
                   company: Optional[str] = None,
                   location: Optional[str] = None,
                   job_type: Optional[str] = None,
                   min_score: Optional[float] = None) -> List[Job]:
        """
        Search jobs with filters.
        
        Args:
            db: Database session
            keywords: Search in title and description
            company: Company name filter
            location: Location filter
            job_type: Job type filter
            min_score: Minimum match score
            
        Returns:
            List of matching jobs
        """
        query = db.query(Job)
        
        if keywords:
            search_term = f"%{keywords}%"
            query = query.filter(
                or_(
                    Job.title.ilike(search_term),
                    Job.description.ilike(search_term)
                )
            )
        
        if company:
            query = query.filter(Job.company.ilike(f"%{company}%"))
        
        if location:
            query = query.filter(Job.location.ilike(f"%{location}%"))
        
        if job_type:
            query = query.filter_by(job_type=job_type)
        
        if min_score is not None:
            query = query.filter(Job.resume_match_score >= min_score)
        
        return query.order_by(desc(Job.resume_match_score)).all()
    
    def update_job_status(self, job_id: str, status: str, db: Session) -> bool:
        """
        Update job application status.
        
        Args:
            job_id: Job ID
            status: New status
            db: Database session
            
        Returns:
            Success boolean
        """
        try:
            job = self.get_job_by_id(job_id, db)
            if job:
                job.status = status
                if status == "applied":
                    job.applied = True
                    job.applied_date = datetime.utcnow()
                db.commit()
                logger.info(f"Updated job {job_id} status to {status}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to update job status: {e}")
            db.rollback()
            return False
    
    def mark_job_viewed(self, job_id: str, db: Session) -> bool:
        """Mark job as viewed."""
        try:
            job = self.get_job_by_id(job_id, db)
            if job:
                job.viewed = True
                db.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to mark job as viewed: {e}")
            db.rollback()
            return False
    
    def add_search_run(self, search_params: Dict[str, Any], db: Session) -> SearchRun:
        """
        Create a new search run record.
        
        Args:
            search_params: Search parameters
            db: Database session
            
        Returns:
            SearchRun object
        """
        try:
            search_run = SearchRun(
                search_id=str(uuid.uuid4()),
                keywords=search_params.get("keywords", ""),
                location=search_params.get("location", ""),
                job_type=search_params.get("job_type"),
                experience_level=search_params.get("experience_level"),
                remote=search_params.get("remote"),
                posted_within=search_params.get("posted_within"),
                status="running"
            )
            
            db.add(search_run)
            db.commit()
            db.refresh(search_run)
            
            logger.info(f"Created search run: {search_run.search_id}")
            return search_run
            
        except Exception as e:
            logger.error(f"Failed to create search run: {e}")
            db.rollback()
            raise
    
    def update_search_run(self, search_id: str, db: Session, **kwargs) -> bool:
        """
        Update search run with results.
        
        Args:
            search_id: Search ID
            db: Database session
            **kwargs: Fields to update
            
        Returns:
            Success boolean
        """
        try:
            search_run = db.query(SearchRun).filter_by(search_id=search_id).first()
            if search_run:
                for key, value in kwargs.items():
                    if hasattr(search_run, key):
                        setattr(search_run, key, value)
                
                if "status" in kwargs and kwargs["status"] == "completed":
                    search_run.completed_at = datetime.utcnow()
                    if search_run.started_at:
                        duration = (search_run.completed_at - search_run.started_at).total_seconds()
                        search_run.duration_seconds = duration
                
                db.commit()
                logger.info(f"Updated search run {search_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to update search run: {e}")
            db.rollback()
            return False
    
    def get_recent_searches(self, db: Session, limit: int = 10) -> List[SearchRun]:
        """Get recent search runs."""
        return db.query(SearchRun).order_by(desc(SearchRun.started_at)).limit(limit).all()
    
    def get_or_create_user_profile(self, db: Session) -> UserProfile:
        """Get or create user profile."""
        profile = db.query(UserProfile).first()
        if not profile:
            profile = UserProfile()
            db.add(profile)
            db.commit()
            db.refresh(profile)
        return profile
    
    def update_user_profile(self, db: Session, **kwargs) -> bool:
        """Update user profile."""
        try:
            profile = self.get_or_create_user_profile(db)
            for key, value in kwargs.items():
                if hasattr(profile, key):
                    setattr(profile, key, value)
            profile.updated_at = datetime.utcnow()
            db.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to update user profile: {e}")
            db.rollback()
            return False
    
    def cache_analysis(self, job_id: str, analysis_type: str, 
                      result: Dict[str, Any], db: Session, 
                      expires_hours: int = 24) -> bool:
        """
        Cache analysis results.
        
        Args:
            job_id: Job ID
            analysis_type: Type of analysis
            result: Analysis result
            db: Database session
            expires_hours: Cache expiration in hours
            
        Returns:
            Success boolean
        """
        try:
            # Check for existing cache
            existing = db.query(AnalysisCache).filter_by(
                job_id=job_id,
                analysis_type=analysis_type
            ).first()
            
            expires_at = datetime.utcnow() + timedelta(hours=expires_hours)
            
            if existing:
                existing.analysis_result = result
                existing.expires_at = expires_at
                existing.created_at = datetime.utcnow()
            else:
                cache = AnalysisCache(
                    job_id=job_id,
                    analysis_type=analysis_type,
                    analysis_result=result,
                    expires_at=expires_at
                )
                db.add(cache)
            
            db.commit()
            return True
            
        except Exception as e:
            logger.error(f"Failed to cache analysis: {e}")
            db.rollback()
            return False
    
    def get_cached_analysis(self, job_id: str, analysis_type: str, 
                           db: Session) -> Optional[Dict[str, Any]]:
        """
        Get cached analysis if not expired.
        
        Args:
            job_id: Job ID
            analysis_type: Type of analysis
            db: Database session
            
        Returns:
            Cached result or None
        """
        cache = db.query(AnalysisCache).filter_by(
            job_id=job_id,
            analysis_type=analysis_type
        ).first()
        
        if cache and cache.expires_at > datetime.utcnow():
            return cache.analysis_result
        
        return None
    
    def get_statistics(self, db: Session) -> Dict[str, Any]:
        """Get database statistics."""
        total_jobs = db.query(func.count(Job.id)).scalar()
        applied_jobs = db.query(func.count(Job.id)).filter_by(applied=True).scalar()
        high_match_jobs = db.query(func.count(Job.id)).filter(Job.resume_match_score >= 80).scalar()
        recent_searches = db.query(func.count(SearchRun.id)).scalar()
        
        avg_match_score = db.query(func.avg(Job.resume_match_score)).scalar()
        
        return {
            "total_jobs": total_jobs,
            "applied_jobs": applied_jobs,
            "high_match_jobs": high_match_jobs,
            "recent_searches": recent_searches,
            "average_match_score": round(avg_match_score, 2) if avg_match_score else 0
        }
    
    def cleanup_old_data(self, db: Session, days: int = 30) -> int:
        """
        Clean up old data from database.
        
        Args:
            db: Database session
            days: Remove data older than this many days
            
        Returns:
            Number of records deleted
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Delete old jobs that weren't applied to
            deleted = db.query(Job).filter(
                and_(
                    Job.scraped_at < cutoff_date,
                    Job.applied == False,
                    Job.status != "saved"
                )
            ).delete()
            
            # Delete expired cache
            db.query(AnalysisCache).filter(
                AnalysisCache.expires_at < datetime.utcnow()
            ).delete()
            
            db.commit()
            logger.info(f"Cleaned up {deleted} old records")
            return deleted
            
        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")
            db.rollback()
            return 0


# Global database manager instance
db_manager = DatabaseManager()


if __name__ == "__main__":
    # Test database operations
    from sqlalchemy.orm import Session
    
    db = next(get_db())
    
    # Get statistics
    stats = db_manager.get_statistics(db)
    print(f"Database Statistics: {stats}")
    
    db.close()