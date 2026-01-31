"""LinkedIn job scraper using Browser-Use for AI-powered automation."""

import asyncio
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime
import json
import re
from browser_use import Agent, Controller
from playwright.async_api import Browser, Page
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
        self.llm = ChatOpenAI(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            temperature=0.1
        )
        self.controller = None
        self.agent = None
        self.browser = None
        self.jobs_scraped = []
        
    async def initialize(self):
        """Initialize the browser and agent."""
        try:
            # Create controller for browser automation
            self.controller = Controller()
            
            # Create AI agent with specific instructions for LinkedIn
            self.agent = Agent(
                task="Search for jobs on LinkedIn and extract job details",
                llm=self.llm,
                controller=self.controller,
                use_vision=True,  # Enable vision for better page understanding
                save_conversation_to="linkedin_scrape_log.json"
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
            
            # Build search URL
            search_url = self._build_search_url(params)
            logger.info(f"Searching LinkedIn with URL: {search_url}")
            
            # Navigate to LinkedIn jobs
            search_task = f"""
            1. Go to LinkedIn Jobs: {search_url}
            2. Wait for the job listings to load
            3. Extract the following information for each job listing visible on the page:
               - Job title
               - Company name
               - Location
               - Posted date
               - Job URL (the link to the full job posting)
            4. If there are multiple pages, navigate through them (up to {params.max_results} jobs total)
            5. Return the extracted data as a structured JSON
            """
            
            # Execute the search task
            result = await self.agent.run(search_task)
            
            # Parse the results
            jobs = self._parse_job_results(result)
            
            # Get detailed information for each job
            detailed_jobs = []
            for job in jobs[:params.max_results]:
                try:
                    detailed_job = await self._get_job_details(job)
                    detailed_jobs.append(detailed_job)
                    self.jobs_scraped.append(detailed_job)
                    
                    # Add delay to avoid rate limiting
                    await asyncio.sleep(settings.search_delay_seconds)
                    
                except Exception as e:
                    logger.error(f"Failed to get details for job {job.get('title')}: {e}")
                    continue
            
            logger.info(f"Successfully scraped {len(detailed_jobs)} jobs")
            return detailed_jobs
            
        except Exception as e:
            logger.error(f"Job search failed: {e}")
            raise
        finally:
            await self.cleanup()
    
    async def _get_job_details(self, job_summary: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get detailed information for a specific job.
        
        Args:
            job_summary: Basic job information including URL
            
        Returns:
            Detailed job information
        """
        try:
            job_url = job_summary.get("url")
            if not job_url:
                logger.warning("No URL found for job, skipping details")
                return job_summary
            
            # Task to extract detailed job information
            detail_task = f"""
            1. Navigate to the job posting: {job_url}
            2. Click "Show more" or similar buttons to expand the full job description
            3. Extract the following detailed information:
               - Full job description
               - Required qualifications
               - Preferred qualifications
               - Responsibilities
               - Benefits (if mentioned)
               - Salary range (if mentioned)
               - Application deadline (if mentioned)
               - Number of applicants (if visible)
               - Employment type (Full-time, Part-time, Contract, etc.)
               - Industry
               - Company size
            4. Return all information as structured JSON
            """
            
            # Execute detail extraction
            result = await self.agent.run(detail_task)
            
            # Parse and merge with summary
            details = self._parse_job_details(result)
            job_full = {**job_summary, **details}
            
            # Add metadata
            job_full["scraped_at"] = datetime.now().isoformat()
            job_full["source"] = "LinkedIn"
            
            return job_full
            
        except Exception as e:
            logger.error(f"Failed to get job details for job_id {job_summary.get('job_id')}: {e}")
            return job_summary
    
    def _build_search_url(self, params: JobSearchParams) -> str:
        """Build LinkedIn job search URL from parameters."""
        base_url = "https://www.linkedin.com/jobs/search/"
        
        query_params = []
        
        # Keywords
        if params.keywords:
            query_params.append(f"keywords={params.keywords.replace(' ', '%20')}")
        
        # Location
        if params.location:
            query_params.append(f"location={params.location.replace(' ', '%20')}")
        
        # Job type
        job_type_map = {
            "full-time": "F",
            "part-time": "P",
            "contract": "C",
            "temporary": "T",
            "internship": "I"
        }
        if params.job_type and params.job_type.lower() in job_type_map:
            query_params.append(f"f_JT={job_type_map[params.job_type.lower()]}")
        
        # Experience level
        exp_level_map = {
            "entry": "1",
            "associate": "2",
            "mid-senior": "3",
            "director": "4",
            "executive": "5"
        }
        if params.experience_level and params.experience_level.lower() in exp_level_map:
            query_params.append(f"f_E={exp_level_map[params.experience_level.lower()]}")
        
        # Remote
        if params.remote:
            query_params.append("f_WT=2")  # Remote work type
        
        # Posted within
        time_map = {
            "24h": "r86400",
            "week": "r604800",
            "month": "r2592000"
        }
        if params.posted_within and params.posted_within in time_map:
            query_params.append(f"f_TPR={time_map[params.posted_within]}")
        
        # Build final URL
        if query_params:
            return f"{base_url}?{'&'.join(query_params)}"
        return base_url
    
    def _parse_job_results(self, agent_result: Any) -> List[Dict[str, Any]]:
        """Parse job results from agent response."""
        try:
            # Extract JSON from agent response
            if isinstance(agent_result, str):
                # Try to find JSON in the response
                json_match = re.search(r'\{.*\}|\[.*\]', agent_result, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group())
                else:
                    logger.warning("No JSON found in agent response")
                    return []
            else:
                data = agent_result
            
            # Ensure we have a list of jobs
            if isinstance(data, dict):
                if "jobs" in data:
                    jobs = data["jobs"]
                elif "results" in data:
                    jobs = data["results"]
                else:
                    jobs = [data]
            elif isinstance(data, list):
                jobs = data
            else:
                jobs = []
            
            # Validate and clean job data
            cleaned_jobs = []
            for job in jobs:
                if isinstance(job, dict):
                    cleaned_job = {
                        "title": job.get("title", ""),
                        "company": job.get("company", ""),
                        "location": job.get("location", ""),
                        "posted_date": job.get("posted_date", ""),
                        "url": job.get("url", ""),
                        "job_id": job.get("job_id", "")
                    }
                    cleaned_jobs.append(cleaned_job)
            
            return cleaned_jobs
            
        except Exception as e:
            logger.error(f"Failed to parse job results: {e}")
            return []
    
    def _parse_job_details(self, agent_result: Any) -> Dict[str, Any]:
        """Parse detailed job information from agent response."""
        try:
            # Extract JSON from agent response
            if isinstance(agent_result, str):
                json_match = re.search(r'\{.*\}', agent_result, re.DOTALL)
                if json_match:
                    details = json.loads(json_match.group())
                else:
                    details = {}
            else:
                details = agent_result if isinstance(agent_result, dict) else {}
            
            # Clean and structure the details
            return {
                "description": details.get("description", ""),
                "requirements": details.get("requirements", []),
                "qualifications": details.get("qualifications", []),
                "responsibilities": details.get("responsibilities", []),
                "benefits": details.get("benefits", []),
                "salary_range": details.get("salary_range", ""),
                "application_deadline": details.get("application_deadline", ""),
                "applicants_count": details.get("applicants_count", ""),
                "employment_type": details.get("employment_type", ""),
                "industry": details.get("industry", ""),
                "company_size": details.get("company_size", "")
            }
            
        except Exception as e:
            logger.error(f"Failed to parse job details: {e}")
            return {}
    
    async def cleanup(self):
        """Clean up browser resources."""
        try:
            if self.controller:
                await self.controller.close()
            logger.info("Scraper cleanup completed")
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
    
    def get_scraped_jobs(self) -> List[Dict[str, Any]]:
        """Get all jobs scraped in this session."""
        return self.jobs_scraped


async def test_scraper():
    """Test the LinkedIn scraper."""
    scraper = LinkedInScraper()
    
    params = JobSearchParams(
        keywords="software engineer",
        location="San Francisco, CA",
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
            print(f"  URL: {job.get('url')}")
            print()
    except Exception as e:
        print(f"Test failed: {e}")


if __name__ == "__main__":
    # Run test
    asyncio.run(test_scraper())