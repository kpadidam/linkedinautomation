#!/usr/bin/env python3
"""
Quick Search Script for LinkedIn Job Automation
Searches all configured job categories and logs to Google Sheets
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from scrapers.linkedin_scraper_robust import RobustLinkedInScraper
from config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class JobSearchAutomation:
    """Automated job search across multiple categories."""
    
    def __init__(self):
        """Initialize the automation system."""
        # Load configurations
        self.load_configs()
        self.total_jobs_found = 0
        self.total_jobs_matched = 0
        
    def load_configs(self):
        """Load job search and skills configurations.

        If the user has saved search_roles in their profile (Settings UI),
        those override job_search_config.json. Each role becomes a single
        category with that role string as the only keyword.
        """
        # Load skills profile (used for resume context only)
        with open('karthik_skills.json', 'r') as f:
            self.skills_profile = json.load(f)

        # Try DB-stored roles first
        user_roles = []
        user_location = "United States"
        # Default to env-level setting; DB override applied below.
        self.enable_resume_matching = settings.enable_resume_matching
        # Resumable-checkpoint state (Option A). 0 means start from scratch.
        self.resume_from_index = 0
        self.checkpoint_started_at = None
        try:
            from database.models import SessionLocal
            from database.db_manager import db_manager
            db = SessionLocal()
            try:
                profile = db_manager.get_or_create_user_profile(db)
                user_roles = list(profile.search_roles or [])
                if profile.preferred_locations:
                    user_location = profile.preferred_locations[0]
                # Pull persisted feature flag (UI-editable). Fallback to env.
                if profile.enable_resume_matching is not None:
                    self.enable_resume_matching = bool(profile.enable_resume_matching)

                # Honor checkpoint only if fresh (<24h). Stale = reset.
                idx = profile.last_completed_category_index
                started = profile.pending_search_started_at
                if (
                    idx is not None and idx >= 0
                    and started is not None
                    and (datetime.utcnow() - started) < timedelta(hours=24)
                ):
                    self.resume_from_index = idx + 1
                    self.checkpoint_started_at = started
                else:
                    profile.last_completed_category_index = -1
                    profile.pending_search_started_at = None
                    db.commit()
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"Could not load profile settings from DB: {e}")

        if user_roles:
            self.job_config = {
                "job_categories": [
                    {
                        "category": role,
                        "keywords": [role],
                        "location": user_location,
                        "max_results": 15,
                        "posted_within": "1h",
                    }
                    for role in user_roles
                ]
            }
            logger.info(f"Using {len(user_roles)} user-defined search roles from Settings")
        else:
            with open('job_search_config.json', 'r') as f:
                self.job_config = json.load(f)
            logger.info(f"Loaded {len(self.job_config['job_categories'])} job categories from job_search_config.json")

        if self.resume_from_index > 0:
            total = len(self.job_config['job_categories'])
            logger.info(
                f"📌 Resuming from category {self.resume_from_index + 1} of {total} "
                f"(checkpoint @ {self.checkpoint_started_at})"
            )

        logger.info(f"Profile: {self.skills_profile['name']} - {self.skills_profile['title']}")
    
    async def run_all_searches(self):
        """Run searches for all configured categories using Playwright scraper."""
        all_categories = self.job_config['job_categories']
        total = len(all_categories)
        start_idx = self.resume_from_index
        remaining = all_categories[start_idx:]

        print("\n" + "="*60)
        print("🚀 LinkedIn Job Search Automation")
        print(f"👤 Profile: {self.skills_profile['name']}")
        if start_idx > 0:
            print(f"📍 Resuming: category {start_idx + 1} of {total} (skipping {start_idx} already done)")
        else:
            print(f"📍 Categories: {total}")
        print("="*60)

        # Persist a fresh start timestamp only if this is NOT a resume.
        # On resume, we keep the original timestamp so the 24h freshness
        # window is measured from the very first start of the run.
        from database.models import SessionLocal
        from database.db_manager import db_manager
        if start_idx == 0:
            try:
                db = SessionLocal()
                try:
                    profile = db_manager.get_or_create_user_profile(db)
                    profile.last_completed_category_index = -1
                    profile.pending_search_started_at = datetime.utcnow()
                    db.commit()
                finally:
                    db.close()
            except Exception as e:
                logger.warning(f"Could not stamp pending_search_started_at: {e}")

        async def _checkpoint(rel_idx, _category):
            """Persist absolute completed-category index after each one."""
            absolute_idx = start_idx + rel_idx
            try:
                db = SessionLocal()
                try:
                    profile = db_manager.get_or_create_user_profile(db)
                    profile.last_completed_category_index = absolute_idx
                    db.commit()
                    logger.info(f"📌 Checkpoint: completed {absolute_idx + 1}/{total}")
                finally:
                    db.close()
            except Exception as e:
                logger.warning(f"Checkpoint write failed: {e}")

        try:
            # Initialize the Robust LinkedIn scraper with DB-driven flags
            scraper = RobustLinkedInScraper(
                enable_resume_matching=self.enable_resume_matching
            )

            # Run search over the remaining (unfinished) categories
            all_jobs = await scraper.run_full_search(
                remaining, on_category_complete=_checkpoint
            )

            # Successful completion → clear checkpoint so next run is fresh.
            try:
                db = SessionLocal()
                try:
                    profile = db_manager.get_or_create_user_profile(db)
                    profile.last_completed_category_index = -1
                    profile.pending_search_started_at = None
                    db.commit()
                finally:
                    db.close()
            except Exception as e:
                logger.warning(f"Could not clear checkpoint after completion: {e}")
            
            self.total_jobs_found = len(all_jobs)
            self.total_jobs_matched = len([j for j in all_jobs if j.get('resume_match_score', 0) >= 70])
            
            # Summary
            print("\n" + "="*60)
            print("📊 Search Complete!")
            print(f"✅ Total jobs found: {self.total_jobs_found}")
            print(f"🎯 High matches (70%+): {self.total_jobs_matched}")
            
            if settings.google_sheets_id:
                sheet_url = f"https://docs.google.com/spreadsheets/d/{settings.google_sheets_id}"
                print(f"📈 View results: {sheet_url}")
            
            # Show top matches
            if all_jobs:
                top_jobs = sorted(
                    [job for job in all_jobs if job.get('resume_match_score')],
                    key=lambda x: x.get('resume_match_score', 0),
                    reverse=True
                )[:5]
                
                if top_jobs:
                    print("\n🏆 Top 5 Matches:")
                    for i, job in enumerate(top_jobs, 1):
                        print(f"{i}. {job.get('title', 'N/A')} at {job.get('company', 'N/A')} - {job.get('resume_match_score', 0):.1f}% match")
                        print(f"   URL: {job.get('url', 'N/A')}")
            
            print("="*60)
            
            return all_jobs
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            print(f"\n❌ Error: {e}")
            raise


async def main():
    """Main entry point."""
    try:
        automation = JobSearchAutomation()
        await automation.run_all_searches()
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Search interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Automation failed: {e}")
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    print("\n🔧 Starting LinkedIn Job Search Automation...")
    print("   This will:")
    print("   1. Login to LinkedIn")
    print("   2. Use the search bar to enter each job category and navigate to the Jobs section")
    print("   4. Apply 'Past 24 hours' filter")
    print("   5.Adjust the URL segment from r86000 (24 hours) to r3600 to filter for jobs in the last hour.")
    print("   6. Extract jobs with LinkedIn URLs")
    print("   7. Calculate match scores")
    print("   8. Log to Google Sheets")
    print("   Press Ctrl+C to stop at any time\n")
    
    # Check for required files
    if not Path("job_search_config.json").exists():
        print("❌ job_search_config.json not found!")
        sys.exit(1)
    
    if not Path("karthik_skills.json").exists():
        print("❌ karthik_skills.json not found!")
        sys.exit(1)
    
    if not Path("Karthik_Fullstack_Developer.pdf").exists():
        print("⚠️  Resume PDF not found, matching may be limited")
    
    # Run the automation
    asyncio.run(main())