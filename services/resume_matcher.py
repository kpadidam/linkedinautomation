"""Resume matching service using AI for job fit analysis."""

import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import json

from openai import OpenAI
from groq import Groq
import PyPDF2

from config import settings
from models.job_model import JobListing, JobAnalysis

logger = logging.getLogger(__name__)


class ResumeProfile:
    """User resume profile for matching."""
    
    def __init__(self, 
                 resume_text: Optional[str] = None,
                 resume_file: Optional[str] = None,
                 skills: Optional[List[str]] = None):
        """
        Initialize resume profile.
        
        Args:
            resume_text: Direct resume text
            resume_file: Path to resume file
            skills: List of skills (if not extracting from resume)
        """
        self.resume_text = resume_text or ""
        self.skills = skills or []
        self.experience = []
        self.education = []
        self.certifications = []
        
        if resume_file:
            self._load_resume_file(resume_file)
        elif not resume_text and settings.resume_file_path:
            self._load_resume_file(settings.resume_file_path)
        
        if not self.skills and settings.skills_list:
            self.skills = settings.skills_list
    
    def _load_resume_file(self, file_path: str):
        """Load resume from file."""
        try:
            path = Path(file_path)
            
            if path.suffix.lower() == '.pdf':
                with open(file_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    text = ""
                    for page in pdf_reader.pages:
                        text += page.extract_text()
                    self.resume_text = text
                    
            elif path.suffix.lower() in ['.txt', '.md']:
                with open(file_path, 'r', encoding='utf-8') as file:
                    self.resume_text = file.read()
                    
            logger.info(f"Loaded resume from {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to load resume file: {e}")


class ResumeMatcherService:
    """Service for matching resumes with job listings."""
    
    def __init__(self, resume_profile: Optional[ResumeProfile] = None):
        """
        Initialize resume matcher.
        
        Args:
            resume_profile: User's resume profile
        """
        self.resume_profile = resume_profile or ResumeProfile()
        
        # Initialize AI clients
        self.openai_client = OpenAI(api_key=settings.openai_api_key)
        self.groq_client = None
        
        if settings.groq_api_key:
            self.groq_client = Groq(api_key=settings.groq_api_key)
    
    async def analyze_job_fit(self, job: JobListing) -> JobAnalysis:
        """
        Analyze how well a job matches the resume profile.
        
        Args:
            job: Job listing to analyze
            
        Returns:
            Job analysis with match scores and recommendations
        """
        try:
            # Prepare job context
            job_context = self._prepare_job_context(job)
            
            # Use Groq for fast analysis if available, otherwise OpenAI
            if self.groq_client:
                analysis = await self._analyze_with_groq(job_context)
            else:
                analysis = await self._analyze_with_openai(job_context)
            
            # Update job with match score
            job.resume_match_score = analysis.overall_match_score
            job.keywords = analysis.technical_skills + analysis.soft_skills
            job.skills = analysis.technical_skills
            
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to analyze job fit: {e}")
            raise
    
    def _prepare_job_context(self, job: JobListing) -> str:
        """Prepare job context for AI analysis."""
        context = f"""
        JOB DETAILS:
        Title: {job.title}
        Company: {job.company}
        Location: {job.location}
        Type: {job.job_type or 'Not specified'}
        Experience Level: {job.experience_level or 'Not specified'}
        
        Description:
        {job.description}
        
        Requirements:
        {', '.join(job.requirements)}
        
        Qualifications:
        {', '.join(job.qualifications)}
        
        Responsibilities:
        {', '.join(job.responsibilities)}
        
        CANDIDATE PROFILE:
        Resume:
        {self.resume_profile.resume_text[:3000]}  # Limit to 3000 chars
        
        Known Skills:
        {', '.join(self.resume_profile.skills)}
        """
        return context
    
    async def _analyze_with_openai(self, job_context: str) -> JobAnalysis:
        """Analyze job fit using OpenAI."""
        try:
            prompt = f"""
            Analyze the job-candidate fit based on the following information:
            
            {job_context}
            
            Provide a detailed analysis in JSON format with:
            1. technical_skills: List of technical skills required
            2. soft_skills: List of soft skills required
            3. tools_technologies: List of tools and technologies mentioned
            4. certifications: List of required certifications
            5. overall_match_score: Overall match percentage (0-100)
            6. skills_match_score: Skills match percentage (0-100)
            7. experience_match_score: Experience match percentage (0-100)
            8. missing_skills: Skills the candidate is missing
            9. matching_skills: Skills the candidate has
            10. recommendations: List of 3-5 actionable recommendations
            11. ai_summary: Brief summary of the job (100 words)
            12. ai_fit_assessment: Assessment of candidate fit (100 words)
            13. interview_tips: List of 3-5 interview preparation tips
            
            Be specific and accurate in your scoring.
            """
            
            response = self.openai_client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": "You are an expert career advisor and resume analyst."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # Create JobAnalysis object
            analysis = JobAnalysis(
                job_id=job_context[:50],  # Use part of context as ID
                technical_skills=result.get("technical_skills", []),
                soft_skills=result.get("soft_skills", []),
                tools_technologies=result.get("tools_technologies", []),
                certifications=result.get("certifications", []),
                overall_match_score=result.get("overall_match_score", 0),
                skills_match_score=result.get("skills_match_score", 0),
                experience_match_score=result.get("experience_match_score", 0),
                missing_skills=result.get("missing_skills", []),
                matching_skills=result.get("matching_skills", []),
                recommendations=result.get("recommendations", []),
                ai_summary=result.get("ai_summary", ""),
                ai_fit_assessment=result.get("ai_fit_assessment", ""),
                interview_tips=result.get("interview_tips", [])
            )
            
            return analysis
            
        except Exception as e:
            logger.error(f"OpenAI analysis failed: {e}")
            # Return a basic analysis on failure
            return self._create_basic_analysis(job_context)
    
    async def _analyze_with_groq(self, job_context: str) -> JobAnalysis:
        """Analyze job fit using Groq for faster inference."""
        try:
            prompt = f"""
            Analyze the job-candidate fit. Return ONLY valid JSON:
            
            {job_context}
            
            Required JSON structure:
            {{
                "technical_skills": [],
                "soft_skills": [],
                "tools_technologies": [],
                "certifications": [],
                "overall_match_score": 0-100,
                "skills_match_score": 0-100,
                "experience_match_score": 0-100,
                "missing_skills": [],
                "matching_skills": [],
                "recommendations": [],
                "ai_summary": "brief job summary",
                "ai_fit_assessment": "fit assessment",
                "interview_tips": []
            }}
            """
            
            response = self.groq_client.chat.completions.create(
                model=settings.groq_model,
                messages=[
                    {"role": "system", "content": "You are a career advisor. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            # Extract JSON from response
            content = response.choices[0].message.content
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            
            if json_match:
                result = json.loads(json_match.group())
            else:
                raise ValueError("No JSON found in response")
            
            # Create JobAnalysis object
            analysis = JobAnalysis(
                job_id=job_context[:50],
                technical_skills=result.get("technical_skills", []),
                soft_skills=result.get("soft_skills", []),
                tools_technologies=result.get("tools_technologies", []),
                certifications=result.get("certifications", []),
                overall_match_score=float(result.get("overall_match_score", 0)),
                skills_match_score=float(result.get("skills_match_score", 0)),
                experience_match_score=float(result.get("experience_match_score", 0)),
                missing_skills=result.get("missing_skills", []),
                matching_skills=result.get("matching_skills", []),
                recommendations=result.get("recommendations", []),
                ai_summary=result.get("ai_summary", ""),
                ai_fit_assessment=result.get("ai_fit_assessment", ""),
                interview_tips=result.get("interview_tips", [])
            )
            
            return analysis
            
        except Exception as e:
            logger.error(f"Groq analysis failed: {e}")
            # Fall back to OpenAI if Groq fails
            if self.openai_client:
                return await self._analyze_with_openai(job_context)
            return self._create_basic_analysis(job_context)
    
    def _create_basic_analysis(self, job_context: str) -> JobAnalysis:
        """Create a basic analysis when AI services fail."""
        # Extract skills using regex
        tech_keywords = ['python', 'java', 'javascript', 'react', 'sql', 'aws', 'docker', 'kubernetes']
        soft_keywords = ['communication', 'leadership', 'teamwork', 'problem-solving']
        
        job_lower = job_context.lower()
        
        technical_skills = [skill for skill in tech_keywords if skill in job_lower]
        soft_skills = [skill for skill in soft_keywords if skill in job_lower]
        
        # Basic matching
        resume_lower = self.resume_profile.resume_text.lower()
        matching_skills = [skill for skill in technical_skills if skill in resume_lower]
        
        match_percentage = (len(matching_skills) / len(technical_skills) * 100) if technical_skills else 50
        
        return JobAnalysis(
            job_id=job_context[:50],
            technical_skills=technical_skills,
            soft_skills=soft_skills,
            tools_technologies=technical_skills,
            certifications=[],
            overall_match_score=match_percentage,
            skills_match_score=match_percentage,
            experience_match_score=50,
            missing_skills=[s for s in technical_skills if s not in matching_skills],
            matching_skills=matching_skills,
            recommendations=["Review job requirements carefully", "Tailor your resume to match"],
            ai_summary="Job analysis unavailable",
            ai_fit_assessment="Basic analysis only",
            interview_tips=["Research the company", "Prepare examples of your work"]
        )
    
    def extract_keywords_from_job(self, job: JobListing) -> List[str]:
        """
        Extract keywords from job listing.
        
        Args:
            job: Job listing
            
        Returns:
            List of keywords
        """
        text = f"{job.title} {job.description} {' '.join(job.requirements)} {' '.join(job.qualifications)}"
        
        # Common tech keywords
        keywords = []
        tech_patterns = [
            r'\b(python|java|javascript|typescript|c\+\+|c#|ruby|go|rust|swift|kotlin)\b',
            r'\b(react|angular|vue|node|django|flask|spring|rails|laravel)\b',
            r'\b(aws|azure|gcp|docker|kubernetes|jenkins|ci/cd|devops)\b',
            r'\b(sql|nosql|mongodb|postgresql|mysql|redis|elasticsearch)\b',
            r'\b(machine learning|ai|data science|deep learning|nlp|computer vision)\b',
            r'\b(agile|scrum|kanban|jira|git|github|gitlab)\b'
        ]
        
        text_lower = text.lower()
        for pattern in tech_patterns:
            matches = re.findall(pattern, text_lower)
            keywords.extend(matches)
        
        # Remove duplicates and return
        return list(set(keywords))
    
    async def batch_analyze_jobs(self, jobs: List[JobListing]) -> List[Tuple[JobListing, JobAnalysis]]:
        """
        Analyze multiple jobs in batch.
        
        Args:
            jobs: List of job listings
            
        Returns:
            List of tuples (job, analysis)
        """
        results = []
        
        for job in jobs:
            try:
                analysis = await self.analyze_job_fit(job)
                results.append((job, analysis))
            except Exception as e:
                logger.error(f"Failed to analyze job {job.title}: {e}")
                continue
        
        return results


def test_resume_matcher():
    """Test resume matching service."""
    import asyncio
    
    # Create test resume profile
    resume = ResumeProfile(
        resume_text="""
        John Doe
        Software Engineer
        
        Skills: Python, JavaScript, React, Node.js, SQL, AWS, Docker
        
        Experience:
        - 5 years as Full Stack Developer
        - Built scalable web applications
        - Led team of 3 developers
        """,
        skills=["Python", "JavaScript", "React", "AWS"]
    )
    
    # Create test job
    job = JobListing(
        job_id="test456",
        title="Senior Software Engineer",
        company="Tech Corp",
        location="San Francisco, CA",
        description="Looking for experienced Python developer with AWS knowledge",
        requirements=["5+ years experience", "Python expertise", "AWS certification preferred"],
        qualifications=["Bachelor's degree", "Strong communication skills"]
    )
    
    # Test matching
    async def run_test():
        matcher = ResumeMatcherService(resume)
        analysis = await matcher.analyze_job_fit(job)
        
        print(f"Overall Match: {analysis.overall_match_score}%")
        print(f"Matching Skills: {analysis.matching_skills}")
        print(f"Missing Skills: {analysis.missing_skills}")
        print(f"Recommendations: {analysis.recommendations}")
    
    asyncio.run(run_test())


if __name__ == "__main__":
    test_resume_matcher()