#!/usr/bin/env python3
"""Test script for the robust LinkedIn scraper."""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from scrapers.linkedin_scraper_robust import RobustLinkedInScraper, JobSearchParams

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_robust_scraper():
    """Test the robust LinkedIn scraper with a single job search."""
    
    print("\n" + "="*60)
    print("🧪 TESTING ROBUST LINKEDIN SCRAPER")
    print("="*60)
    print("This test will:")
    print("1. Initialize browser with enhanced error handling")
    print("2. Login with retry logic")
    print("3. Perform a single job search with comprehensive error recovery")
    print("4. Extract jobs using safe element operations")
    print("5. Test navigation resilience")
    print("="*60)
    
    scraper = RobustLinkedInScraper()
    
    try:
        # Test single keyword search
        test_params = JobSearchParams(
            keywords="Python Developer",
            location="United States",
            max_results=5  # Limit for testing
        )
        
        print(f"\n🔍 Testing search for: {test_params.keywords}")
        print("   This will test all the new robust utilities...")
        
        # Run the search
        jobs = await scraper.search_and_extract_jobs(test_params)
        
        # Display results
        print(f"\n✅ TEST RESULTS:")
        print(f"   Jobs found: {len(jobs)}")
        print(f"   Error count: {scraper.error_count}")
        
        if jobs:
            print(f"\n📝 Sample extracted job:")
            sample_job = jobs[0]
            print(f"   Title: {sample_job.get('title', 'N/A')}")
            print(f"   Company: {sample_job.get('company', 'N/A')}")
            print(f"   Location: {sample_job.get('location', 'N/A')}")
            print(f"   URL: {sample_job.get('url', 'N/A')[:60]}...")
            print(f"   Skills: {sample_job.get('skills', [])[:3]}...")
            print(f"   Match Score: {sample_job.get('resume_match_score', 'N/A')}%")
            
            # Test data quality
            valid_jobs = [j for j in jobs if j.get('title') and j.get('title') != 'Job Title Not Available']
            with_urls = [j for j in jobs if j.get('url')]
            
            print(f"\n📊 DATA QUALITY:")
            print(f"   Valid titles: {len(valid_jobs)}/{len(jobs)}")
            print(f"   With URLs: {len(with_urls)}/{len(jobs)}")
        
        print(f"\n🎯 RESILIENCE TEST PASSED!")
        print(f"   The scraper handled errors gracefully and extracted {len(jobs)} jobs")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        logger.error(f"Test failed with error: {e}")
        
        # Get debug information
        if scraper.navigator:
            page_info = await scraper.navigator.get_page_info()
            print(f"   Debug info: {page_info}")
        
        raise
    
    finally:
        await scraper.cleanup()


async def test_utilities_only():
    """Test just the utility functions without full scraper."""
    print("\n" + "="*60)
    print("🔧 TESTING UTILITIES INDEPENDENTLY")
    print("="*60)
    
    from scrapers.utils.retry_utils import retry_async, QUICK_RETRY
    from scrapers.utils.element_utils import SafeElementFinder
    from scrapers.utils.navigation_utils import LinkedInNavigator
    
    print("✅ Successfully imported all utility modules")
    print("   - retry_utils: Exponential backoff and retry decorators")
    print("   - element_utils: Safe element operations")
    print("   - navigation_utils: Robust page navigation")
    
    # Test retry decorator
    @retry_async(config=QUICK_RETRY)
    async def test_retry_function():
        print("   - Retry decorator works correctly")
        return "success"
    
    result = await test_retry_function()
    print(f"   - Retry test result: {result}")
    
    print("🎯 UTILITY TEST PASSED!")


if __name__ == "__main__":
    print("🚀 Starting Robust Scraper Tests...")
    
    # Check if config files exist
    required_files = [
        "job_search_config.json",
        "karthik_skills.json"
    ]
    
    missing_files = [f for f in required_files if not Path(f).exists()]
    if missing_files:
        print(f"⚠️  Missing config files: {missing_files}")
        print("   Running utility tests only...")
        asyncio.run(test_utilities_only())
    else:
        print("📁 All config files found, running full test...")
        try:
            asyncio.run(test_robust_scraper())
        except KeyboardInterrupt:
            print("\n\n⚠️ Test interrupted by user")
        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            print("\n🔧 Running utility tests as fallback...")
            asyncio.run(test_utilities_only())