"""LinkedIn job scraper using Browser-Use for AI-powered automation - Fixed version."""

import asyncio
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime
import json
import re
from browser_use import Agent
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from config import settings

logger = logging.getLogger(__name__)


class JobSearchParams(BaseModel):
    """Parameters for LinkedIn job search."""
    keywords: str
    location: str = settings.default_location
    job_type: Optional[str] = settings.default_job_type
    experience_level: Optional[str] = None
    remote: Optional[bool] = None
    posted_within: Optional[str] = "24h"  # 24h, week, month
    company_size: Optional[str] = None
    max_results: int = settings.max_results_per_search


class LinkedInScraper:
    """LinkedIn job scraper using Browser-Use AI agent."""
    
    def __init__(self):
        """Initialize the LinkedIn scraper."""
        self.agent = None
        self.jobs_scraped = []
        
    async def initialize(self):
        """Initialize the browser and agent."""
        try:
            # Create AI agent with specific instructions for LinkedIn
            # Using the correct Browser-Use API
            self.agent = Agent(
                task="Search for jobs on LinkedIn and extract job details",
                llm=ChatOpenAI(
                    api_key=settings.openai_api_key,
                    model=settings.openai_model,
                    temperature=0.1
                )
            )
            
            logger.info("LinkedIn scraper initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize scraper: {e}")
            raise
    
    async def search_jobs(self, params: JobSearchParams) -> List[Dict[str, Any]]:
        """
        Search for jobs on LinkedIn based on parameters.
        
        Args:
            params: Search parameters
            
        Returns:
            List of job dictionaries
        """
        try:
            await self.initialize()
            
            # For now, return mock data to test the pipeline
            # In production, this would use the browser to search LinkedIn
            logger.info(f"Searching for {params.keywords} in {params.location}")
            
            # Mock job data for testing
            mock_jobs = [
                {
                    "job_id": f"mock_{params.keywords.replace(' ', '_')}_{i}",
                    "title": f"{params.keywords} - Position {i+1}",
                    "company": f"Tech Company {i+1}",
                    "location": params.location,
                    "url": f"https://linkedin.com/jobs/mock_{i}",
                    "description": f"We are looking for a {params.keywords} to join our team. "
                                  f"Requirements include Java, Spring Boot, AWS, and {3+i} years of experience.",
                    "requirements": ["Java", "Spring Boot", "AWS", "REST APIs"],
                    "qualifications": ["Bachelor's degree", "Strong communication skills"],
                    "posted_date": "2 days ago",
                    "job_type": params.job_type,
                    "experience_level": params.experience_level,
                    "scraped_at": datetime.now().isoformat(),
                    "source": "LinkedIn"
                }
                for i in range(min(3, params.max_results))  # Return 3 mock jobs per search
            ]
            
            self.jobs_scraped.extend(mock_jobs)
            logger.info(f"Found {len(mock_jobs)} jobs (mock data)")
            
            return mock_jobs
            
        except Exception as e:
            logger.error(f"Job search failed: {e}")
            return []
        finally:
            await self.cleanup()
    
    async def cleanup(self):
        """Clean up browser resources."""
        try:
            # Cleanup if needed
            logger.info("Scraper cleanup completed")
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
    
    def get_scraped_jobs(self) -> List[Dict[str, Any]]:
        """Get all jobs scraped in this session."""
        return self.jobs_scraped


# Alternative implementation using direct browser automation
async def search_linkedin_direct(keywords: str, location: str = "United States") -> List[Dict[str, Any]]:
    """
    Direct LinkedIn search without Browser-Use complexity.
    Returns mock data for testing the pipeline.
    """
    logger.info(f"Direct search for: {keywords} in {location}")
    
    # This is where you would implement actual LinkedIn scraping
    # For now, returning structured mock data
    jobs = []
    
    # Mock job templates based on keywords
    if "Java" in keywords or "Backend" in keywords:
        jobs.append({
            "job_id": "java_backend_001",
            "title": "Senior Java Backend Developer",
            "company": "Tech Solutions Inc",
            "location": location,
            "description": "Looking for experienced Java developer with Spring Boot expertise",
            "requirements": ["Java", "Spring Boot", "Microservices", "AWS"],
            "salary_range": "$120,000 - $160,000",
            "posted_date": "1 day ago"
        })
    
    if "React" in keywords or "Frontend" in keywords:
        jobs.append({
            "job_id": "react_frontend_001",
            "title": "React Frontend Developer",
            "company": "Digital Innovations",
            "location": location,
            "description": "React developer needed for modern web applications",
            "requirements": ["React", "Redux", "JavaScript", "CSS"],
            "salary_range": "$100,000 - $140,000",
            "posted_date": "3 days ago"
        })
    
    if "Full Stack" in keywords:
        jobs.append({
            "job_id": "fullstack_001",
            "title": "Full Stack Developer (Java + React)",
            "company": "Enterprise Systems",
            "location": location,
            "description": "Full stack developer with Java backend and React frontend skills",
            "requirements": ["Java", "Spring Boot", "React", "AWS", "Docker"],
            "salary_range": "$130,000 - $170,000",
            "posted_date": "2 days ago"
        })
    
    return jobs


async def test_scraper():
    """Test the LinkedIn scraper."""
    scraper = LinkedInScraper()
    
    params = JobSearchParams(
        keywords="Java Developer",
        location="Remote",
        job_type="full-time",
        posted_within="week",
        max_results=5
    )
    
    try:
        jobs = await scraper.search_jobs(params)
        print(f"Found {len(jobs)} jobs:")
        for job in jobs:
            print(f"- {job.get('title')} at {job.get('company')}")
            print(f"  Location: {job.get('location')}")
            print()
    except Exception as e:
        print(f"Test failed: {e}")


if __name__ == "__main__":
    # Run test
    asyncio.run(test_scraper())