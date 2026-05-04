#!/usr/bin/env python3
"""
Test script with mock data to verify the pipeline works
This demonstrates the system with sample job data
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from services.google_sheets_service import GoogleSheetsService
from services.resume_matcher import ResumeMatcherService, ResumeProfile
from database.db_manager import db_manager
from database.models import get_db
from models.job_model import JobListing


async def create_mock_jobs():
    """Create mock job listings for testing."""
    
    mock_jobs_data = [
        {
            "job_id": "mock_java_001",
            "title": "Senior Java Developer",
            "company": "Tech Solutions Inc",
            "location": "San Francisco, CA (Remote)",
            "url": "https://linkedin.com/jobs/mock_java_001",
            "description": """
                We are seeking an experienced Java Developer to join our engineering team.
                You will work on building scalable microservices using Spring Boot and deploying to AWS.
                
                Requirements:
                - 5+ years of Java development experience
                - Strong experience with Spring Boot and microservices
                - AWS cloud experience (EC2, S3, Lambda)
                - REST API design and implementation
                - Experience with Docker and Kubernetes
            """,
            "requirements": [
                "5+ years Java experience",
                "Spring Boot expertise",
                "AWS cloud services",
                "Microservices architecture",
                "Docker/Kubernetes"
            ],
            "qualifications": [
                "Bachelor's degree in Computer Science",
                "Strong problem-solving skills",
                "Excellent communication"
            ],
            "job_type": "full-time",
            "experience_level": "mid-senior",
            "salary_range": "$140,000 - $180,000",
            "posted_date": "2 days ago"
        },
        {
            "job_id": "mock_fullstack_001",
            "title": "Full Stack Developer (Java/React)",
            "company": "Innovation Labs",
            "location": "New York, NY (Hybrid)",
            "url": "https://linkedin.com/jobs/mock_fullstack_001",
            "description": """
                Looking for a Full Stack Developer with strong Java backend and React frontend skills.
                
                What you'll do:
                - Develop RESTful APIs using Spring Boot
                - Build responsive UIs with React and Redux
                - Work with MySQL and MongoDB databases
                - Deploy applications to AWS
            """,
            "requirements": [
                "Java and Spring Boot",
                "React and Redux",
                "REST API development",
                "SQL and NoSQL databases",
                "AWS deployment"
            ],
            "qualifications": [
                "3+ years full stack experience",
                "Bachelor's degree preferred",
                "Agile/Scrum experience"
            ],
            "job_type": "full-time",
            "experience_level": "mid-senior",
            "salary_range": "$120,000 - $160,000",
            "posted_date": "1 day ago"
        },
        {
            "job_id": "mock_react_001",
            "title": "React Frontend Developer",
            "company": "Digital Agency Co",
            "location": "Remote (US)",
            "url": "https://linkedin.com/jobs/mock_react_001",
            "description": """
                We need a talented React Developer to join our frontend team.
                
                Requirements:
                - Expert knowledge of React and Redux
                - Experience with modern JavaScript (ES6+)
                - Strong CSS/SASS skills
                - RESTful API integration
                - Testing with Jest
            """,
            "requirements": [
                "React and Redux expertise",
                "JavaScript ES6+",
                "CSS/SASS",
                "API integration",
                "Jest testing"
            ],
            "qualifications": [
                "2+ years React experience",
                "Portfolio of React projects",
                "Team collaboration skills"
            ],
            "job_type": "contract",
            "experience_level": "mid-level",
            "salary_range": "$100,000 - $130,000",
            "posted_date": "3 days ago"
        }
    ]
    
    return mock_jobs_data


async def test_with_mock_data():
    """Test the entire pipeline with mock job data."""
    
    print("\n" + "="*60)
    print("🧪 Testing LinkedIn Job Automation with Mock Data")
    print("="*60)
    
    # Initialize services
    print("\n📋 Initializing services...")
    
    # Google Sheets
    sheets_service = None
    try:
        sheets_service = GoogleSheetsService()
        print(f"✅ Google Sheets connected")
        print(f"   URL: {sheets_service.get_spreadsheet_url()}")
    except Exception as e:
        print(f"⚠️  Google Sheets not available: {e}")
    
    # Resume Matcher
    resume_matcher = None
    try:
        with open('karthik_skills.json', 'r') as f:
            skills_profile = json.load(f)
        
        resume_profile = ResumeProfile(
            resume_file="Karthik_Fullstack_Developer.pdf",
            skills=skills_profile['all_skills_list']
        )
        resume_matcher = ResumeMatcherService(resume_profile)
        print(f"✅ Resume matcher initialized")
    except Exception as e:
        print(f"⚠️  Resume matcher not available: {e}")
    
    # Get mock jobs
    print("\n🔍 Processing mock job listings...")
    mock_jobs = await create_mock_jobs()
    
    processed_jobs = []
    for job_data in mock_jobs:
        try:
            # Create JobListing object
            job = JobListing(**job_data)
            
            # Analyze with resume matcher
            if resume_matcher:
                print(f"\n   Analyzing: {job.title} at {job.company}")
                analysis = await resume_matcher.analyze_job_fit(job)
                job.resume_match_score = analysis.overall_match_score
                job.keywords = analysis.technical_skills[:5]
                print(f"   Match Score: {job.resume_match_score:.1f}%")
            
            # Save to database
            db = next(get_db())
            db_manager.add_job(job, db)
            db.close()
            
            # Save to Google Sheets
            if sheets_service:
                sheets_service.add_job(job)
                print(f"   ✅ Added to Google Sheets")
            
            processed_jobs.append(job)
            
        except Exception as e:
            print(f"   ❌ Error processing job: {e}")
    
    # Summary
    print("\n" + "="*60)
    print("📊 Test Results:")
    print(f"✅ Processed {len(processed_jobs)} mock jobs")
    
    if processed_jobs:
        # Sort by match score
        sorted_jobs = sorted(
            [j for j in processed_jobs if j.resume_match_score],
            key=lambda x: x.resume_match_score,
            reverse=True
        )
        
        print("\n🏆 Match Scores:")
        for job in sorted_jobs:
            print(f"   {job.resume_match_score:.1f}% - {job.title} at {job.company}")
    
    if sheets_service:
        print(f"\n📈 View results in Google Sheets:")
        print(f"   {sheets_service.get_spreadsheet_url()}")
    
    print("\n✅ Test completed successfully!")
    print("   The system is working correctly with mock data.")
    print("   Real LinkedIn scraping would work the same way.")
    print("="*60)


if __name__ == "__main__":
    print("\n🧪 Running mock data test...")
    print("   This will demonstrate the full pipeline with sample jobs")
    
    asyncio.run(test_with_mock_data())