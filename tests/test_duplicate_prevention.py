#!/usr/bin/env python3
"""Test script for duplicate prevention in Google Sheets."""

import asyncio
import logging
from datetime import datetime
from typing import List

from models.job_model import JobListing
from services.google_sheets_service import GoogleSheetsService
from config import settings

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_test_jobs() -> List[JobListing]:
    """Create test job listings with some duplicates."""
    jobs = [
        JobListing(
            job_id="job_001",
            title="Software Engineer",
            company="TechCorp",
            location="San Francisco, CA",
            description="Build amazing software",
            url="https://linkedin.com/jobs/job_001",
            scraped_at=datetime.now()
        ),
        JobListing(
            job_id="job_002",
            title="Data Scientist",
            company="DataCo",
            location="New York, NY",
            description="Analyze data and build ML models",
            url="https://linkedin.com/jobs/job_002",
            scraped_at=datetime.now()
        ),
        JobListing(
            job_id="job_003",
            title="Product Manager",
            company="StartupXYZ",
            location="Austin, TX",
            description="Lead product development",
            url="https://linkedin.com/jobs/job_003",
            scraped_at=datetime.now()
        ),
        # Duplicate of job_001
        JobListing(
            job_id="job_001",
            title="Software Engineer",
            company="TechCorp",
            location="San Francisco, CA",
            description="Build amazing software",
            url="https://linkedin.com/jobs/job_001",
            scraped_at=datetime.now()
        ),
        JobListing(
            job_id="job_004",
            title="DevOps Engineer",
            company="CloudInc",
            location="Seattle, WA",
            description="Manage cloud infrastructure",
            url="https://linkedin.com/jobs/job_004",
            scraped_at=datetime.now()
        ),
        # Another duplicate of job_002
        JobListing(
            job_id="job_002",
            title="Data Scientist",
            company="DataCo",
            location="New York, NY",
            description="Analyze data and build ML models",
            url="https://linkedin.com/jobs/job_002",
            scraped_at=datetime.now()
        )
    ]
    return jobs


def test_single_job_duplicates():
    """Test duplicate prevention for single job additions."""
    print("\n" + "="*60)
    print("TEST 1: Single Job Duplicate Prevention")
    print("="*60)
    
    try:
        # Initialize Google Sheets service
        sheets_service = GoogleSheetsService()
        
        if not sheets_service.service:
            print("⚠️  Google Sheets service not configured. Please set up credentials.")
            return
        
        # Create test jobs
        jobs = create_test_jobs()
        
        # Add jobs one by one
        print(f"\n📝 Attempting to add {len(jobs)} jobs (including duplicates)...")
        for i, job in enumerate(jobs, 1):
            print(f"\n{i}. Adding job: {job.job_id} - {job.title} at {job.company}")
            sheets_service.add_job(job)
        
        print(f"\n✅ Test completed. Check the logs for duplicate detection.")
        print(f"📊 Cache now contains {len(sheets_service.cached_job_ids)} unique job IDs")
        
        # Show cache contents
        print("\n🗂️  Cached Job IDs:")
        for job_id in sorted(sheets_service.cached_job_ids):
            print(f"   - {job_id}")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")


def test_batch_job_duplicates():
    """Test duplicate prevention for batch job additions."""
    print("\n" + "="*60)
    print("TEST 2: Batch Job Duplicate Prevention")
    print("="*60)
    
    try:
        # Initialize Google Sheets service
        sheets_service = GoogleSheetsService()
        
        if not sheets_service.service:
            print("⚠️  Google Sheets service not configured. Please set up credentials.")
            return
        
        # Create test jobs
        jobs = create_test_jobs()
        
        # Add all jobs in batch
        print(f"\n📝 Attempting to add {len(jobs)} jobs in batch (including duplicates)...")
        sheets_service.add_jobs_batch(jobs)
        
        print(f"\n✅ Batch test completed. Check the logs for duplicate filtering.")
        print(f"📊 Cache now contains {len(sheets_service.cached_job_ids)} unique job IDs")
        
        # Try adding the same batch again
        print(f"\n🔄 Attempting to add the same batch again...")
        sheets_service.add_jobs_batch(jobs)
        
        print(f"\n✅ Second batch attempt completed. All should be filtered as duplicates.")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")


def test_cache_refresh():
    """Test cache refresh functionality."""
    print("\n" + "="*60)
    print("TEST 3: Cache Refresh")
    print("="*60)
    
    try:
        # Initialize Google Sheets service
        sheets_service = GoogleSheetsService()
        
        if not sheets_service.service:
            print("⚠️  Google Sheets service not configured. Please set up credentials.")
            return
        
        print(f"\n📊 Initial cache size: {len(sheets_service.cached_job_ids)} job IDs")
        
        # Refresh cache
        print("\n🔄 Refreshing cache...")
        sheets_service.refresh_cache()
        
        print(f"📊 Cache size after refresh: {len(sheets_service.cached_job_ids)} job IDs")
        
        # Test duplicate check
        test_id = "job_001"
        is_duplicate = sheets_service.check_duplicate(test_id)
        print(f"\n🔍 Checking if '{test_id}' is a duplicate: {is_duplicate}")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")


def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("🧪 DUPLICATE PREVENTION TEST SUITE")
    print("="*70)
    
    if not settings.google_sheets_id:
        print("\n⚠️  No Google Sheets ID configured in settings.")
        print("Please set GOOGLE_SHEETS_ID in your .env file")
        return
    
    print(f"\n📋 Using Google Sheet: {settings.google_sheets_id}")
    print(f"🔗 Sheet URL: https://docs.google.com/spreadsheets/d/{settings.google_sheets_id}")
    
    # Run tests
    test_single_job_duplicates()
    test_batch_job_duplicates()
    test_cache_refresh()
    
    print("\n" + "="*70)
    print("✅ ALL TESTS COMPLETED")
    print("="*70)
    print("\n📝 Check your Google Sheet to verify:")
    print("  1. Job ID column is present as the first column")
    print("  2. No duplicate job IDs exist in the sheet")
    print("  3. Logs show duplicates being filtered")
    print(f"\n🔗 Sheet URL: https://docs.google.com/spreadsheets/d/{settings.google_sheets_id}")


if __name__ == "__main__":
    main()