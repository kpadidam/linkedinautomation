"""Quick test to verify LinkedIn scraper fixes."""
import asyncio
from scrapers.linkedin_scraper_playwright import LinkedInJobScraper

async def test_quick():
    scraper = LinkedInJobScraper()
    
    # Load job config
    job_categories = [
        {
            "category": "Java Developer", 
            "keywords": ["Java Developer"],
            "location": "United States"
        }
    ]
    
    await scraper.run_full_search(job_categories)
    await scraper.close()

if __name__ == "__main__":
    asyncio.run(test_quick())