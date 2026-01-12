"""Simplified LinkedIn job scraper - Working version with realistic mock data."""

import logging
from typing import List, Dict, Optional, Any
from datetime import datetime
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
    posted_within: Optional[str] = "24h"
    company_size: Optional[str] = None
    max_results: int = settings.max_results_per_search


class LinkedInScraper:
    """Simplified LinkedIn job scraper with realistic mock data."""
    
    def __init__(self):
        """Initialize the LinkedIn scraper."""
        self.jobs_scraped = []
        
    async def initialize(self):
        """Initialize the scraper."""
        logger.info("LinkedIn scraper initialized (simplified version with mock data)")
    
    async def search_jobs(self, params: JobSearchParams) -> List[Dict[str, Any]]:
        """
        Search for jobs - returns realistic mock data for demonstration.
        
        In production, this would use Selenium/Playwright to scrape LinkedIn.
        For now, returns structured mock data based on search parameters.
        """
        try:
            await self.initialize()
            
            logger.info(f"Searching for {params.keywords} in {params.location}")
            
            # Generate realistic mock jobs based on keywords
            jobs = []
            
            # Java Backend Jobs
            if any(kw in params.keywords.lower() for kw in ['java', 'backend', 'spring']):
                jobs.extend([
                    {
                        "job_id": f"java_{datetime.now().timestamp()}_1",
                        "title": "Senior Java Backend Developer",
                        "company": "Wells Fargo",
                        "location": "Charlotte, NC (Remote)",
                        "url": "https://linkedin.com/jobs/view/3847291045",
                        "description": """
                            Wells Fargo is seeking a Senior Java Developer to join our technology team.
                            
                            What you'll do:
                            • Design and develop scalable microservices using Java and Spring Boot
                            • Build RESTful APIs and integrate with various backend services
                            • Work with Oracle and MySQL databases
                            • Implement OAuth2 and JWT for secure authentication
                            • Deploy applications to AWS cloud infrastructure
                            
                            Required Skills:
                            • 5+ years of Java development experience
                            • Expert knowledge of Spring Boot, Spring Security, Spring Data JPA
                            • Experience with AWS services (EC2, S3, RDS, Lambda)
                            • Strong understanding of microservices architecture
                            • Experience with Docker and Kubernetes
                            • Proficiency with Git, Jenkins, Maven
                        """,
                        "requirements": [
                            "5+ years Java experience",
                            "Spring Boot expertise",
                            "AWS cloud services",
                            "Microservices architecture",
                            "REST API development"
                        ],
                        "qualifications": [
                            "Bachelor's degree in Computer Science",
                            "Experience with Agile/Scrum",
                            "Strong problem-solving skills"
                        ],
                        "job_type": "full-time",
                        "experience_level": "mid-senior",
                        "salary_range": "$130,000 - $170,000",
                        "posted_date": "2 days ago",
                        "applicants_count": "47 applicants"
                    },
                    {
                        "job_id": f"java_{datetime.now().timestamp()}_2",
                        "title": "Java Developer - Cloud Services",
                        "company": "Capital One",
                        "location": "McLean, VA (Hybrid)",
                        "url": "https://linkedin.com/jobs/view/3847291046",
                        "description": """
                            Join Capital One's cloud engineering team building next-generation banking platforms.
                            
                            Responsibilities:
                            • Develop cloud-native applications using Java and Spring Boot
                            • Implement microservices on AWS
                            • Work with Docker, Kubernetes for containerization
                            • Build CI/CD pipelines using Jenkins
                            • Collaborate with cross-functional teams in Agile environment
                            
                            Requirements:
                            • Strong Java and Spring Boot experience
                            • AWS cloud platform knowledge
                            • Experience with RESTful APIs
                            • Knowledge of OAuth2, JWT authentication
                        """,
                        "requirements": [
                            "Java", "Spring Boot", "AWS", "Docker", "Kubernetes", "REST APIs", "OAuth2"
                        ],
                        "job_type": "full-time",
                        "experience_level": "mid-senior",
                        "salary_range": "$120,000 - $160,000",
                        "posted_date": "1 day ago"
                    }
                ])
            
            # Full Stack Jobs
            if any(kw in params.keywords.lower() for kw in ['full stack', 'fullstack']):
                jobs.extend([
                    {
                        "job_id": f"fullstack_{datetime.now().timestamp()}_1",
                        "title": "Full Stack Developer (Java/React)",
                        "company": "JPMorgan Chase",
                        "location": "New York, NY (Hybrid)",
                        "url": "https://linkedin.com/jobs/view/3847291047",
                        "description": """
                            JPMorgan Chase is looking for a Full Stack Developer to join our digital banking team.
                            
                            What you'll do:
                            • Develop backend services using Java and Spring Boot
                            • Build responsive UI with React and Redux
                            • Work with both SQL (Oracle) and NoSQL (MongoDB) databases
                            • Deploy to AWS cloud infrastructure
                            • Implement secure APIs with OAuth2 and JWT
                            
                            Requirements:
                            • 4+ years full stack development experience
                            • Strong Java backend skills
                            • React frontend expertise
                            • AWS cloud experience
                        """,
                        "requirements": [
                            "Java", "Spring Boot", "React", "Redux", "AWS", "Oracle", "REST APIs"
                        ],
                        "job_type": "full-time",
                        "experience_level": "mid-senior",
                        "salary_range": "$140,000 - $180,000",
                        "posted_date": "3 days ago"
                    }
                ])
            
            # React Frontend Jobs
            if any(kw in params.keywords.lower() for kw in ['react', 'frontend', 'ui developer']):
                jobs.extend([
                    {
                        "job_id": f"react_{datetime.now().timestamp()}_1",
                        "title": "Senior React Developer",
                        "company": "Microsoft",
                        "location": "Redmond, WA (Remote)",
                        "url": "https://linkedin.com/jobs/view/3847291048",
                        "description": """
                            Microsoft is seeking a React Developer for our Azure portal team.
                            
                            Requirements:
                            • Expert knowledge of React and Redux
                            • Experience with TypeScript
                            • Strong CSS/SASS skills
                            • RESTful API integration
                            • Experience with Jest testing
                            
                            Nice to have:
                            • Java backend knowledge
                            • AWS or Azure experience
                        """,
                        "requirements": [
                            "React", "Redux", "TypeScript", "CSS", "REST API", "Jest"
                        ],
                        "job_type": "full-time",
                        "experience_level": "mid-senior",
                        "salary_range": "$130,000 - $170,000",
                        "posted_date": "1 week ago"
                    }
                ])
            
            # Angular Frontend Jobs
            if 'angular' in params.keywords.lower():
                jobs.extend([
                    {
                        "job_id": f"angular_{datetime.now().timestamp()}_1",
                        "title": "Angular Developer",
                        "company": "Deloitte",
                        "location": "Chicago, IL (Hybrid)",
                        "url": "https://linkedin.com/jobs/view/3847291049",
                        "description": """
                            Deloitte Digital is looking for an Angular Developer.
                            
                            Requirements:
                            • Strong Angular and TypeScript skills
                            • Experience with NGRX state management
                            • REST API integration
                            • HTML5, CSS3 expertise
                            • Agile/Scrum experience
                        """,
                        "requirements": [
                            "Angular", "TypeScript", "NGRX", "REST API", "HTML5", "CSS3"
                        ],
                        "job_type": "full-time",
                        "experience_level": "mid-senior",
                        "salary_range": "$110,000 - $150,000",
                        "posted_date": "4 days ago"
                    }
                ])
            
            # Microservices Developer
            if 'microservices' in params.keywords.lower():
                jobs.extend([
                    {
                        "job_id": f"micro_{datetime.now().timestamp()}_1",
                        "title": "Microservices Architect",
                        "company": "Amazon",
                        "location": "Seattle, WA (Remote)",
                        "url": "https://linkedin.com/jobs/view/3847291050",
                        "description": """
                            Amazon is seeking a Microservices Architect for AWS team.
                            
                            Requirements:
                            • Expert in Java and Spring Boot
                            • Deep knowledge of microservices patterns
                            • AWS services expertise (Lambda, ECS, EKS)
                            • Docker and Kubernetes experience
                            • API Gateway and service mesh knowledge
                        """,
                        "requirements": [
                            "Java", "Spring Boot", "Microservices", "AWS", "Docker", "Kubernetes"
                        ],
                        "job_type": "full-time",
                        "experience_level": "mid-senior",
                        "salary_range": "$160,000 - $200,000",
                        "posted_date": "5 days ago"
                    }
                ])
            
            # Add metadata to all jobs
            for job in jobs:
                job["scraped_at"] = datetime.now().isoformat()
                job["source"] = "LinkedIn"
                if "requirements" not in job:
                    job["requirements"] = []
                if "qualifications" not in job:
                    job["qualifications"] = []
            
            # Limit to max_results
            jobs = jobs[:params.max_results]
            
            self.jobs_scraped.extend(jobs)
            logger.info(f"Found {len(jobs)} jobs for '{params.keywords}'")
            
            return jobs
            
        except Exception as e:
            logger.error(f"Job search failed: {e}")
            return []
        finally:
            await self.cleanup()
    
    async def cleanup(self):
        """Clean up resources."""
        logger.info("Scraper cleanup completed")
    
    def get_scraped_jobs(self) -> List[Dict[str, Any]]:
        """Get all jobs scraped in this session."""
        return self.jobs_scraped