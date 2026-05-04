"""Quick test for company extraction with stealth mode."""
import asyncio
from scrapers.linkedin_scraper_playwright import LinkedInScraperPlaywright
from models.job_model import JobSearchParams

async def test_company_extraction():
    print('Testing enhanced company extraction...')
    scraper = LinkedInScraperPlaywright()
    
    try:
        await scraper.initialize()
        print('✓ Browser initialized with stealth mode')
        
        await scraper.login()
        print('✓ Logged in successfully')
        
        params = JobSearchParams(
            keywords='Java Developer',
            location='United States', 
            date_posted='Past 24 hours'
        )
        
        print('Searching for Java Developer jobs...')
        jobs = await scraper.search_jobs(params)
        
        print(f'\n✅ Extracted {len(jobs)} jobs\n')
        
        # Check company extraction success rate
        successful = 0
        failed = 0
        
        for i, job in enumerate(jobs[:10]):  # Check first 10 jobs
            company = job.get('company', 'Unknown Company')
            title = job.get('title', 'Unknown Title')
            
            if company and company != 'Unknown Company':
                successful += 1
                print(f'✓ Job {i+1}: {title} at {company}')
            else:
                failed += 1
                print(f'✗ Job {i+1}: {title} - COMPANY MISSING')
        
        print(f'\n📊 Results:')
        print(f'  Successful extractions: {successful}/{min(10, len(jobs))}')
        print(f'  Failed extractions: {failed}/{min(10, len(jobs))}')
        print(f'  Success rate: {(successful/(successful+failed)*100 if (successful+failed) > 0 else 0):.1f}%')
        
    except Exception as e:
        print(f'❌ Error: {e}')
    finally:
        await scraper.close()
        print('\n✅ Test completed!')

if __name__ == "__main__":
    asyncio.run(test_company_extraction())