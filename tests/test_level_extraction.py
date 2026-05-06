"""Test enhanced extraction with Level field (years as number)."""
import asyncio
from scrapers.linkedin_scraper_playwright import LinkedInScraperPlaywright, JobSearchParams

async def test_level_extraction():
    print('🔍 Testing Level extraction (years as number)...\n')
    scraper = LinkedInScraperPlaywright()
    
    try:
        await scraper.initialize()
        print('✓ Browser initialized with stealth mode')
        
        await scraper.login()
        print('✓ Logged in successfully\n')
        
        params = JobSearchParams(
            keywords='Senior Java Developer',  # Using "Senior" to likely get jobs with years requirement
            location='United States',
            date_posted='Past 24 hours'
        )
        
        print('📋 Searching for Senior Java Developer jobs...')
        print('This will extract years of experience as Level field...\n')
        
        jobs = await scraper.search_jobs(params)
        
        print(f'\n✅ Extracted {len(jobs)} jobs\n')
        
        # Display results with Level field
        for i, job in enumerate(jobs[:5], 1):  # Show first 5 jobs
            print(f'{"="*60}')
            print(f'Job {i}: {job.get("title", "Unknown Title")}')
            print(f'Company: {job.get("company", "Unknown Company")}')
            print(f'Location: {job.get("location", "Unknown")}')
            
            # Show Level (years as number)
            level = job.get("level")
            if level is not None:
                print(f'📊 Level (Years): {level}')
                exp_level = job.get("experience_level", "")
                print(f'   Experience Level: {exp_level}')
            else:
                print(f'📊 Level: Not specified')
            
            # Show if responsibilities were extracted
            responsibilities = job.get("responsibilities", [])
            if responsibilities and isinstance(responsibilities, list) and responsibilities != ["See job posting for full responsibilities"]:
                print(f'\n✅ Responsibilities extracted ({len(responsibilities)} items):')
                print(f'   - {responsibilities[0][:80]}...' if len(responsibilities[0]) > 80 else f'   - {responsibilities[0]}')
            else:
                print(f'\n❌ Responsibilities: Not extracted (showing placeholder)')
            
            # Show requirements
            requirements = job.get("requirements", [])
            if requirements and isinstance(requirements, list) and "See job posting" not in str(requirements):
                print(f'\nRequirements ({len(requirements)} items):')
                for req in requirements[:2]:
                    if "years" in req.lower():
                        print(f'   ⭐ {req}')  # Highlight years requirement
                    else:
                        print(f'   - {req[:60]}...' if len(req) > 60 else f'   - {req}')
            
            print()
        
        # Statistics
        print(f'{"="*60}')
        print('📊 Level Extraction Statistics:\n')
        
        with_level = sum(1 for j in jobs if j.get("level") is not None)
        with_responsibilities = sum(1 for j in jobs if j.get("responsibilities") and 
                                   isinstance(j.get("responsibilities"), list) and 
                                   j.get("responsibilities") != ["See job posting for full responsibilities"])
        
        print(f'Jobs with Level (years): {with_level}/{len(jobs)} ({with_level/len(jobs)*100:.1f}%)')
        print(f'Jobs with real responsibilities: {with_responsibilities}/{len(jobs)} ({with_responsibilities/len(jobs)*100:.1f}%)')
        
        # Show level distribution
        levels = [j.get("level") for j in jobs if j.get("level") is not None]
        if levels:
            print(f'\nLevel Distribution:')
            print(f'  Min years: {min(levels)}')
            print(f'  Max years: {max(levels)}')
            print(f'  Average: {sum(levels)/len(levels):.1f} years')
        
    except Exception as e:
        print(f'❌ Error: {e}')
        import traceback
        traceback.print_exc()
    finally:
        await scraper.close()
        print('\n✅ Test completed!')

if __name__ == "__main__":
    asyncio.run(test_level_extraction())