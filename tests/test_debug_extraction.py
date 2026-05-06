"""Debug test for job detail extraction."""
import asyncio
import logging
from scrapers.linkedin_scraper_playwright import LinkedInScraperPlaywright, JobSearchParams

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

async def test_debug_extraction():
    print('🔍 Testing job detail extraction with debug mode...\n')
    scraper = LinkedInScraperPlaywright()
    
    try:
        await scraper.initialize()
        print('✓ Browser initialized with stealth mode')
        
        await scraper.login()
        print('✓ Logged in successfully\n')
        
        params = JobSearchParams(
            keywords='Java Developer',
            location='United States',
            date_posted='Past 24 hours'
        )
        
        # Override to get just 2 jobs for testing
        print('📋 Searching for jobs (limited to 2 for debug)...\n')
        
        jobs = await scraper.search_jobs(params)
        
        # Limit to first 2 jobs for detailed analysis
        jobs = jobs[:2] if len(jobs) > 2 else jobs
        
        print(f'\n✅ Analyzed {len(jobs)} jobs\n')
        
        for i, job in enumerate(jobs, 1):
            print(f'{"="*60}')
            print(f'Job {i}: {job.get("title", "Unknown Title")}')
            print(f'Company: {job.get("company", "Unknown Company")}')
            
            # Check responsibilities
            responsibilities = job.get("responsibilities", [])
            if isinstance(responsibilities, list):
                if responsibilities and responsibilities != ["See job posting for full responsibilities"]:
                    print(f'✅ Responsibilities extracted: {len(responsibilities)} items')
                    print(f'   First: {responsibilities[0][:100]}...')
                else:
                    print(f'❌ Responsibilities NOT extracted (placeholder text)')
            else:
                print(f'❌ Responsibilities format error: {type(responsibilities)}')
            
            # Check description
            desc = job.get("description", "")
            if desc and "See job posting" not in desc:
                print(f'✅ Description extracted: {len(desc)} chars')
            else:
                print(f'❌ Description NOT extracted')
            
            # Check level
            level = job.get("level")
            if level is not None:
                print(f'✅ Level extracted: {level} years')
            else:
                print(f'❌ Level NOT extracted')
            
            print()
        
        print('\n📊 Check debug screenshots in current directory:')
        print('   - debug_no_panel_*.png - If detail panel not found')
        print('   - debug_no_description_*.png - If description not extracted')
        print('\nCheck logs above for selector matches and panel detection.')
        
    except Exception as e:
        print(f'❌ Error: {e}')
        import traceback
        traceback.print_exc()
    finally:
        await scraper.close()
        print('\n✅ Test completed!')

if __name__ == "__main__":
    asyncio.run(test_debug_extraction())