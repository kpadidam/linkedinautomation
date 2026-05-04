"""Test enhanced job extraction with full details."""
import asyncio
from scrapers.linkedin_scraper_playwright import LinkedInScraperPlaywright, JobSearchParams

async def test_full_extraction():
    print('🔍 Testing enhanced job extraction with full details...\n')
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
        
        print('📋 Searching for Java Developer jobs...')
        print('This will click each job to extract full details...\n')
        
        jobs = await scraper.search_jobs(params)
        
        print(f'\n✅ Extracted {len(jobs)} jobs with details\n')
        
        # Analyze extraction quality
        for i, job in enumerate(jobs[:3]):  # Show first 3 jobs in detail
            print(f'{"="*60}')
            print(f'Job {i+1}: {job.get("title", "Unknown Title")}')
            print(f'Company: {job.get("company", "Unknown Company")}')
            print(f'Location: {job.get("location", "Unknown")}')
            print(f'Salary: {job.get("salary_range", "Not specified")}')
            
            # Check experience level extraction
            exp_level = job.get("experience_level", "Not determined")
            print(f'Experience Level: {exp_level}')
            
            # Check responsibilities
            responsibilities = job.get("responsibilities", [])
            if responsibilities and isinstance(responsibilities, list):
                print(f'\nResponsibilities ({len(responsibilities)} found):')
                for j, resp in enumerate(responsibilities[:3], 1):
                    print(f'  {j}. {resp[:80]}...' if len(resp) > 80 else f'  {j}. {resp}')
            else:
                print('\nResponsibilities: Not extracted')
            
            # Check requirements
            requirements = job.get("requirements", [])
            if requirements and isinstance(requirements, list):
                print(f'\nRequirements ({len(requirements)} found):')
                for j, req in enumerate(requirements[:3], 1):
                    print(f'  {j}. {req[:80]}...' if len(req) > 80 else f'  {j}. {req}')
            else:
                print('\nRequirements: Not extracted')
            
            # Check skills
            skills = job.get("skills", [])
            if skills and isinstance(skills, list) and skills != ["Not specified"]:
                print(f'\nSkills ({len(skills)} found): {", ".join(skills[:10])}')
            else:
                print('\nSkills: Not extracted')
            
            print()
        
        # Summary statistics
        print(f'{"="*60}')
        print('📊 Extraction Statistics:\n')
        
        total = len(jobs)
        with_responsibilities = sum(1 for j in jobs if j.get("responsibilities") and isinstance(j.get("responsibilities"), list) and len(j.get("responsibilities")) > 0)
        with_requirements = sum(1 for j in jobs if j.get("requirements") and isinstance(j.get("requirements"), list) and len(j.get("requirements")) > 0)
        with_exp_level = sum(1 for j in jobs if j.get("experience_level") and j.get("experience_level") != "Not determined")
        with_skills = sum(1 for j in jobs if j.get("skills") and isinstance(j.get("skills"), list) and j.get("skills") != ["Not specified"])
        
        print(f'Jobs with responsibilities: {with_responsibilities}/{total} ({with_responsibilities/total*100:.1f}%)')
        print(f'Jobs with requirements: {with_requirements}/{total} ({with_requirements/total*100:.1f}%)')
        print(f'Jobs with experience level: {with_exp_level}/{total} ({with_exp_level/total*100:.1f}%)')
        print(f'Jobs with skills extracted: {with_skills}/{total} ({with_skills/total*100:.1f}%)')
        
    except Exception as e:
        print(f'❌ Error: {e}')
    finally:
        await scraper.close()
        print('\n✅ Test completed!')

if __name__ == "__main__":
    asyncio.run(test_full_extraction())