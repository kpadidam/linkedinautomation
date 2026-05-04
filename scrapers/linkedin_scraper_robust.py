"""Robust LinkedIn job scraper using Playwright with comprehensive error handling."""

import asyncio
import logging
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
import re
import sys
import random
from pathlib import Path
from playwright.async_api import async_playwright, Page, Browser
from playwright_stealth import Stealth
from pydantic import BaseModel

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings
from services.resume_matcher import ResumeMatcherService, ResumeProfile
from services.google_sheets_service import GoogleSheetsService
from models.job_model import JobListing

# Import our robust utilities
from .utils.retry_utils import (
    retry_async, 
    STANDARD_RETRY, 
    NAVIGATION_RETRY, 
    ELEMENT_WAIT_RETRY,
    retry_navigation,
    retry_element_operation
)
from .utils.element_utils import SafeElementFinder
from .utils.navigation_utils import LinkedInNavigator

logger = logging.getLogger(__name__)


class JobSearchParams(BaseModel):
    """Parameters for LinkedIn job search."""
    keywords: str
    location: str = settings.default_location
    job_type: Optional[str] = settings.default_job_type
    experience_level: Optional[str] = None
    remote: Optional[bool] = None
    posted_within: Optional[str] = "1h"
    company_size: Optional[str] = None
    max_results: int = settings.max_results_per_search


class RobustLinkedInScraper:
    """Enhanced LinkedIn job scraper with comprehensive error handling and retry logic."""
    
    def __init__(self, enable_resume_matching: Optional[bool] = None):
        """Initialize the robust LinkedIn scraper.

        Args:
            enable_resume_matching: If provided, overrides the env-driven
                ``settings.enable_resume_matching`` for this scraper instance.
                When ``None`` (default), falls back to the env value so existing
                callers continue to work unchanged.
        """
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.jobs_scraped = []
        self.resume_matcher = None
        self.google_sheets = None

        # Resolve resume-matching flag: explicit constructor arg wins; otherwise env.
        self.enable_resume_matching = (
            enable_resume_matching
            if enable_resume_matching is not None
            else settings.enable_resume_matching
        )
        
        # Enhanced utilities
        self.element_finder: Optional[SafeElementFinder] = None
        self.navigator: Optional[LinkedInNavigator] = None
        
        # Error tracking
        self.error_count = 0
        self.max_errors = 10
        
    @retry_async(config=STANDARD_RETRY)
    async def initialize(self):
        """Initialize browser and services with retry logic."""
        try:
            playwright = await async_playwright().start()

            # Persistent context: cookies/session survive across runs so we don't
            # re-trigger LinkedIn's bot detection on every launch.
            user_data_dir = str(Path(__file__).parent.parent / "data" / "browser_profile")
            Path(user_data_dir).mkdir(parents=True, exist_ok=True)

            context = await playwright.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                headless=False,
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                extra_http_headers={
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                },
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                ]
            )
            self.browser = context  # cleanup uses self.browser.close()
            self.page = context.pages[0] if context.pages else await context.new_page()
            
            # Apply stealth mode
            stealth_config = Stealth()
            await stealth_config.apply_stealth_async(self.page)
            logger.info("Stealth mode applied successfully")
            
            # Initialize utility classes
            self.element_finder = SafeElementFinder(self.page)
            self.navigator = LinkedInNavigator(self.page)
            
            # Initialize resume matcher (gated by feature flag to avoid LLM cost)
            if self.enable_resume_matching and settings.resume_file_path:
                resume_profile = ResumeProfile(
                    resume_file=settings.resume_file_path,
                    skills=settings.skills_list
                )
                self.resume_matcher = ResumeMatcherService(resume_profile)
                logger.info("Resume matcher initialized successfully")
            
            # Initialize Google Sheets
            if settings.google_sheets_id:
                self.google_sheets = GoogleSheetsService()
                logger.info("Google Sheets service initialized successfully")
            
            logger.info("All services initialized successfully")
            
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            await self._emergency_cleanup()
            raise
    
    @retry_navigation(config=NAVIGATION_RETRY)
    async def login(self):
        """Enhanced login with retry logic and error handling."""
        try:
            logger.info("Starting LinkedIn login process")

            # Try the feed first — persistent context may already have a valid session
            await self.navigator.goto_with_retry("https://www.linkedin.com/feed/")
            if "/feed" in self.page.url and "/login" not in self.page.url:
                logger.info("Already logged in via persistent session — skipping login form")
                return

            # Navigate to login page with retry
            login_success = await self.navigator.goto_with_retry(
                settings.linkedin_url,
                expected_selectors=['input[id="username"]', 'input[id="password"]']
            )

            if not login_success:
                raise Exception("Failed to load LinkedIn login page")
            
            # Dismiss any overlays
            await self.element_finder.dismiss_overlays()
            await asyncio.sleep(1)
            
            # Enter credentials with error handling
            logger.info("Entering login credentials")
            
            # Fill email
            email_success = await self.element_finder.safe_fill(
                'input[id="username"]',
                settings.linkedin_email,
                timeout=15000
            )
            if not email_success:
                raise Exception("Failed to enter email")
            
            await asyncio.sleep(random.uniform(0.5, 1.5))
            
            # Fill password
            password_success = await self.element_finder.safe_fill(
                'input[id="password"]',
                settings.linkedin_password,
                timeout=15000
            )
            if not password_success:
                raise Exception("Failed to enter password")
            
            # Random delay before clicking
            await asyncio.sleep(random.uniform(0.8, 1.8))
            
            # Click sign in with multiple strategies
            sign_in_selectors = [
                'button[type="submit"]',
                'button[data-litms-control-urn*="signin"]',
                '.btn__primary--large'
            ]
            
            clicked = await self.element_finder.safe_click(
                sign_in_selectors[0],
                alternative_selectors=sign_in_selectors[1:]
            )
            
            if not clicked:
                raise Exception("Failed to click sign in button")
            
            # Wait for login completion with timeout
            logger.info("Waiting for login completion")
            await asyncio.sleep(5)
            
            # Verify login success - wait for global navigation
            login_verified = await self._verify_login_success()
            
            if not login_verified:
                # Take screenshot for debugging
                await self.page.screenshot(path="login_failure.png")
                raise Exception("Login verification failed")
            
            logger.info("LinkedIn login successful")
            
        except Exception as e:
            logger.error(f"Login failed: {e}")
            # Take screenshot for debugging
            try:
                await self.page.screenshot(path="login_error.png")
            except:
                pass
            raise
    
    async def _verify_login_success(self, timeout: int = 20000) -> bool:
        """Verify that login was successful."""
        success_indicators = [
            '.global-nav',
            '.feed-container', 
            '[data-test-id="nav-jobs"]',
            '.nav-item__icon'
        ]
        
        start_time = asyncio.get_event_loop().time()
        while (asyncio.get_event_loop().time() - start_time) < (timeout / 1000):
            for indicator in success_indicators:
                element = await self.page.query_selector(indicator)
                if element and await element.is_visible():
                    logger.debug(f"Login verified with indicator: {indicator}")
                    return True
            
            # Check if we're stuck on login page
            current_url = self.page.url
            if '/login' in current_url:
                await asyncio.sleep(1)
                continue
            elif 'linkedin.com' in current_url:
                # We've been redirected away from login - probably successful
                return True
            
            await asyncio.sleep(0.5)
        
        logger.warning("Login verification timed out")
        return False
    
    async def search_and_extract_jobs(self, params: JobSearchParams) -> List[Dict[str, Any]]:
        """
        Enhanced job search and extraction with comprehensive error handling.
        
        Args:
            params: Search parameters
            
        Returns:
            List of job dictionaries with match scores
        """
        try:
            logger.info(f"Starting job search for: {params.keywords}")
            self._increment_error_count()  # Reset on successful operation

            # Direct URL navigation — bypasses LinkedIn's search bar entirely.
            # Time filter: r3600 = past hour, r86400 = past 24h.
            from urllib.parse import urlencode, quote_plus
            time_filter = getattr(params, "posted_within", None) or "r3600"
            time_filter_map = {
                "1h": "r3600", "hour": "r3600",
                "24h": "r86400", "day": "r86400",
                "week": "r604800", "month": "r2592000",
            }
            time_filter = time_filter_map.get(time_filter, time_filter)
            if not time_filter.startswith("r"):
                time_filter = "r3600"

            qs = urlencode({
                "keywords": params.keywords,
                "f_TPR": time_filter,
                **({"location": params.location} if getattr(params, "location", None) else {}),
            }, quote_via=quote_plus)
            jobs_url = f"https://www.linkedin.com/jobs/search/?{qs}"
            logger.info(f"Navigating directly to: {jobs_url}")

            nav_ok = await self.navigator.goto_with_retry(jobs_url)
            if not nav_ok:
                logger.error("Failed to load jobs search page")
                return []

            # Confirm we landed on the jobs search page (not redirected to login/feed)
            await asyncio.sleep(2)
            current_url = self.page.url
            if "/jobs/search" not in current_url:
                logger.error(f"Unexpected page after navigation: {current_url}")
                return []

            # Wait for stabilisation, dismiss overlays
            await asyncio.sleep(3)
            await self.element_finder.dismiss_overlays()
            
            # Step 4: Extract jobs with enhanced error handling
            jobs = await self._extract_jobs_with_enhanced_handling()
            
            # Step 5: Process jobs (calculate match scores, add to Google Sheets)
            processed_jobs = await self._process_extracted_jobs(jobs, params)
            
            # Limit results
            final_jobs = processed_jobs[:params.max_results]
            self.jobs_scraped.extend(final_jobs)
            
            logger.info(f"Successfully extracted {len(final_jobs)} jobs for '{params.keywords}'")
            return final_jobs
            
        except Exception as e:
            logger.error(f"Search and extract failed for '{params.keywords}': {e}")
            self._increment_error_count()
            
            # Try one recovery attempt
            if self.error_count < self.max_errors:
                logger.info("Attempting recovery and retry")
                recovery_success = await self.navigator.recover_from_navigation_failure()
                if recovery_success:
                    await asyncio.sleep(2)
                    # Don't retry recursively, just return empty list
                    logger.warning("Recovery completed but not retrying extraction to avoid recursion")
            
            return []
    
    async def _extract_jobs_with_enhanced_handling(self) -> List[Dict[str, Any]]:
        """Extract job listings with comprehensive error handling."""
        jobs = []
        
        try:
            # Wait for job cards with progressive timeout strategy
            job_cards = await self._find_job_cards_with_fallback()
            
            if not job_cards:
                logger.warning("No job cards found")
                return jobs
            
            logger.info(f"Found {len(job_cards)} job cards to process")
            
            # Process each job card with individual error handling
            for i, card in enumerate(job_cards):
                try:
                    logger.debug(f"Processing job card {i+1}/{len(job_cards)}")
                    
                    job_data = await self._extract_single_job_safely(card, i)
                    if job_data:
                        jobs.append(job_data)
                        
                    # Rate limiting between cards
                    if i < len(job_cards) - 1:
                        await asyncio.sleep(random.uniform(0.5, 1.2))
                        
                except Exception as e:
                    logger.warning(f"Failed to extract job {i+1}: {e}")
                    continue  # Skip this job and continue with others
            
            logger.info(f"Successfully extracted {len(jobs)} jobs from {len(job_cards)} cards")
            
        except Exception as e:
            logger.error(f"Job extraction failed: {e}")
            # Take screenshot for debugging
            try:
                await self.page.screenshot(path="extraction_error.png")
            except:
                pass
        
        return jobs
    
    @retry_element_operation(config=ELEMENT_WAIT_RETRY)
    async def _find_job_cards_with_fallback(self) -> List:
        """Find job cards using multiple strategies."""
        # Scroll to trigger lazy loading
        await self.element_finder.scroll_and_wait('.job-search-card', timeout=8000)
        
        # Try multiple selectors for job cards
        card_selectors = [
            '.job-search-card',
            'div.job-card-container',
            'li.jobs-search-results__list-item',
            'div[data-job-id]',
            'li[data-occludable-job-id]',
            '.scaffold-layout__list-container li'
        ]
        
        for selector in card_selectors:
            cards = await self.page.query_selector_all(selector)
            if cards:
                logger.debug(f"Found {len(cards)} job cards using selector: {selector}")
                
                # Verify cards are actually visible
                visible_cards = []
                for card in cards[:20]:  # Limit to first 20 to avoid timeout
                    try:
                        if await card.is_visible():
                            visible_cards.append(card)
                    except:
                        continue
                
                if visible_cards:
                    return visible_cards
        
        logger.warning("No job cards found with any selector")
        return []
    
    async def _extract_single_job_safely(self, card, index: int) -> Optional[Dict[str, Any]]:
        """Extract data from a single job card with error handling."""
        try:
            job_data = {}
            
            # Extract basic information from card (without clicking)
            basic_info = await self._extract_basic_job_info(card, index)
            job_data.update(basic_info)
            
            # Try to get detailed information
            detailed_info = await self._extract_detailed_job_info(card, index)
            if detailed_info:
                job_data.update(detailed_info)
            
            # Validate essential data
            if not job_data.get('title') or job_data.get('title') == 'Job Title Not Available':
                logger.debug(f"Job {index+1} has no valid title, skipping")
                return None
            
            return job_data
            
        except Exception as e:
            logger.warning(f"Failed to extract job data from card {index+1}: {e}")
            return None
    
    async def _extract_basic_job_info(self, card, index: int) -> Dict[str, Any]:
        """Extract basic job info via in-page JS — robust to LinkedIn DOM churn."""
        job_data = {
            "job_id": f"job_{index}",
            "title": "Job Title Not Available",
            "company": "Unknown Company",
            "location": "Location not specified",
            "url": "",
            "posted_date": "Recently",
            "applicants_count": "",
            "salary_range": "",
            "description": ""
        }

        try:
            # JS evaluation runs INSIDE the card element. We search broadly so
            # the result survives LinkedIn renaming hashed CSS classes.
            extracted = await card.evaluate(r"""
                (el) => {
                    const text = (n) => (n && n.innerText || '').trim();
                    const out = {};

                    // job_id from data attributes (any descendant or self)
                    out.job_id = el.getAttribute('data-job-id')
                              || el.getAttribute('data-occludable-job-id')
                              || (el.querySelector('[data-job-id]')?.getAttribute('data-job-id'))
                              || (el.querySelector('[data-occludable-job-id]')?.getAttribute('data-occludable-job-id'))
                              || '';

                    // Card aria-label is often the cleanest signal:
                    //   "Senior Data Analyst at Acme in San Francisco, CA · 2 days ago · ..."
                    const cardAria = el.getAttribute('aria-label') || '';
                    if (cardAria) {
                        const ataIdx = cardAria.indexOf(' at ');
                        if (ataIdx > 0) {
                            out.title = cardAria.slice(0, ataIdx).trim();
                            const rest = cardAria.slice(ataIdx + 4);
                            const inIdx = rest.indexOf(' in ');
                            if (inIdx > 0) {
                                out.company = rest.slice(0, inIdx).trim();
                                out.location = rest.slice(inIdx + 4).split('·')[0].trim();
                            } else {
                                out.company = rest.split('·')[0].trim();
                            }
                        }
                    }

                    // url: first /jobs/view/ link
                    const jobLink = el.querySelector('a[href*="/jobs/view/"]');
                    if (jobLink) {
                        let href = jobLink.getAttribute('href') || '';
                        if (href.startsWith('/')) href = 'https://www.linkedin.com' + href;
                        out.url = href.split('?')[0];

                        // title — prefer aria-label of the link, then strong/h3 text inside it
                        const aria = jobLink.getAttribute('aria-label');
                        if (aria && aria.trim()) out.title = aria.trim();
                        if (!out.title) {
                            const strong = jobLink.querySelector('strong, h3, span[aria-hidden="true"]');
                            if (strong) out.title = text(strong);
                        }
                        if (!out.title) out.title = text(jobLink);
                    }

                    // fallback title: any visible h3 / strong
                    if (!out.title) {
                        const h = el.querySelector('h3, strong');
                        if (h) out.title = text(h);
                    }

                    // company: link to /company/ → its text; else aria-label of the card; else first subtitle
                    const compLink = el.querySelector('a[href*="/company/"]');
                    if (compLink) out.company = text(compLink);
                    if (!out.company) {
                        const sub = el.querySelector('[class*="subtitle"], [class*="company"]');
                        if (sub) out.company = text(sub);
                    }

                    // location: try metadata items; else last small grey-looking line
                    const metaCandidates = el.querySelectorAll(
                        '[class*="metadata"], [class*="caption"], li, span'
                    );
                    for (const m of metaCandidates) {
                        const t = text(m);
                        // crude heuristic: location lines tend to contain a comma or "Remote"
                        if (t && (t.includes(',') || /remote|hybrid|on[- ]site/i.test(t)) && t.length < 80) {
                            out.location = t;
                            break;
                        }
                    }

                    // posted date: <time> element
                    const time = el.querySelector('time');
                    if (time) out.posted_date = text(time) || time.getAttribute('datetime') || '';

                    return out;
                }
            """)

            if extracted:
                if extracted.get("job_id"): job_data["job_id"] = extracted["job_id"]
                if extracted.get("title"): job_data["title"] = extracted["title"]
                if extracted.get("company"): job_data["company"] = extracted["company"]
                if extracted.get("location"): job_data["location"] = extracted["location"]
                if extracted.get("url"): job_data["url"] = extracted["url"]
                if extracted.get("posted_date"): job_data["posted_date"] = extracted["posted_date"]

            # Surface diagnostics if extraction failed
            if job_data["title"] == "Job Title Not Available":
                try:
                    raw = (await card.inner_text())[:200]
                    logger.warning(f"Card {index+1}: no title extracted. inner_text head: {raw!r}")
                except Exception:
                    pass

        except Exception as e:
            logger.debug(f"Error extracting basic job info: {e}")

        return job_data
    
    async def _extract_detailed_job_info(self, card, index: int) -> Optional[Dict[str, Any]]:
        """Open the card's detail panel and pull the full job description."""
        try:
            # Click the card directly (more reliable than selector lookup)
            try:
                await card.scroll_into_view_if_needed(timeout=3000)
            except Exception:
                pass
            try:
                await card.click(timeout=4000)
            except Exception as e:
                logger.debug(f"Card click failed for {index+1}: {e}")
                return None

            # Wait for any description-like element to appear
            try:
                await self.page.wait_for_selector(
                    '[class*="description"], [class*="job-details"], article',
                    timeout=4000,
                )
            except Exception:
                pass
            await asyncio.sleep(0.6)

            detail_info = await self._extract_from_details_panel()
            return detail_info

        except Exception as e:
            logger.debug(f"Failed to extract detailed info for job {index+1}: {e}")
            return None

    async def _extract_from_details_panel(self) -> Dict[str, Any]:
        """Extract description text from the job details panel via in-page JS."""
        details = {
            "skills": [],
            "requirements": [],
            "responsibilities": [],
            "experience_level": None,
            "job_type": None,
            "level": None,
        }

        try:
            # Find the largest text block under a description-ish container.
            description_text = await self.page.evaluate(r"""
                () => {
                    const candidates = document.querySelectorAll(
                        '[class*="description"], [class*="job-details"], article, [class*="DescriptionContainer"]'
                    );
                    let best = '';
                    for (const c of candidates) {
                        const t = (c.innerText || '').trim();
                        if (t.length > best.length) best = t;
                    }
                    return best;
                }
            """) or ""

            if description_text and len(description_text) > 100:
                details.update(self._parse_job_description(description_text))
            else:
                logger.debug("No description text found in details panel")

        except Exception as e:
            logger.debug(f"Error extracting from details panel: {e}")

        return details

    def _parse_job_description(self, description: str) -> Dict[str, Any]:
        """Parse job description to extract structured information."""
        # Keep the full description — UI handles its own truncation if needed
        parsed = {"description": description}
        
        try:
            # Extract years of experience
            years_match = re.search(r'(\d+)\+?\s*years?\s*(?:of\s*)?(?:experience|exp)', description.lower())
            if years_match:
                years = int(years_match.group(1))
                parsed["level"] = years
                
                # Map to experience level
                if years <= 2:
                    parsed["experience_level"] = 'entry'
                elif years <= 5:
                    parsed["experience_level"] = 'associate'
                elif years <= 8:
                    parsed["experience_level"] = 'mid-senior'
                else:
                    parsed["experience_level"] = 'director'
            
            # Extract skills
            skills = self._extract_skills_from_description(description)
            if skills:
                parsed["skills"] = skills
            
            # Extract requirements
            requirements = self._extract_requirements_from_description(description)
            if requirements:
                parsed["requirements"] = requirements
            
            # Extract responsibilities
            responsibilities = self._extract_responsibilities_from_description(description)
            if responsibilities:
                parsed["responsibilities"] = responsibilities
                
        except Exception as e:
            logger.debug(f"Error parsing job description: {e}")
        
        return parsed
    
    def _extract_skills_from_description(self, description: str) -> List[str]:
        """Extract technical skills from job description."""
        skills = []
        tech_skills = [
            'Java', 'Python', 'JavaScript', 'TypeScript', 'React', 'Angular', 'Vue', 
            'Spring', 'Spring Boot', 'Node.js', 'Express', '.NET', 'C#', 'C++',
            'SQL', 'NoSQL', 'MongoDB', 'PostgreSQL', 'MySQL', 'Redis',
            'AWS', 'Azure', 'GCP', 'Docker', 'Kubernetes', 'Jenkins',
            'REST', 'API', 'GraphQL', 'Git', 'Agile', 'Scrum'
        ]
        
        desc_lower = description.lower()
        for skill in tech_skills:
            if re.search(r'\b' + re.escape(skill.lower()) + r'\b', desc_lower):
                skills.append(skill)
        
        return skills[:10]  # Limit to top 10
    
    def _extract_requirements_from_description(self, description: str) -> List[str]:
        """Extract requirements from job description."""
        requirements = []
        lines = description.split('\n')
        
        in_requirements = False
        for line in lines:
            line_lower = line.lower().strip()
            
            if any(keyword in line_lower for keyword in ['requirements:', 'qualifications:', 'must have:']):
                in_requirements = True
                continue
            elif any(keyword in line_lower for keyword in ['responsibilities:', 'benefits:', 'nice to have:']):
                in_requirements = False
            elif in_requirements and line.strip():
                cleaned = re.sub(r'^[\s•\-\*\d\.]+', '', line.strip())
                if cleaned and len(cleaned) > 10:
                    requirements.append(cleaned)
                    if len(requirements) >= 8:
                        break

        return requirements
    
    def _extract_responsibilities_from_description(self, description: str) -> List[str]:
        """Extract responsibilities from job description."""
        responsibilities = []
        lines = description.split('\n')
        
        in_responsibilities = False
        for line in lines:
            line_lower = line.lower().strip()
            
            if any(keyword in line_lower for keyword in ['responsibilities:', 'what you\'ll do:', 'you will:']):
                in_responsibilities = True
                continue
            elif any(keyword in line_lower for keyword in ['requirements:', 'qualifications:', 'skills:']):
                in_responsibilities = False
            elif in_responsibilities and line.strip():
                cleaned = re.sub(r'^[\s•\-\*\d\.]+', '', line.strip())
                if cleaned and len(cleaned) > 10:
                    responsibilities.append(cleaned)
                    if len(responsibilities) >= 8:
                        break

        return responsibilities
    
    async def _process_extracted_jobs(self, jobs: List[Dict[str, Any]], params: JobSearchParams) -> List[Dict[str, Any]]:
        """Process extracted jobs with match scores and Google Sheets logging."""
        processed_jobs = []
        
        for job in jobs:
            try:
                # Add metadata
                job["scraped_at"] = datetime.now().isoformat()
                job["source"] = "LinkedIn"
                job["time_filter"] = "1_hour"
                job["search_keywords"] = params.keywords
                job["search_location"] = params.location
                
                # Calculate match score if resume matcher is available
                if self.resume_matcher:
                    try:
                        job_listing = JobListing(**job)
                        analysis = await self.resume_matcher.analyze_job_fit(job_listing)
                        job["resume_match_score"] = analysis.overall_match_score
                        job["matching_skills"] = analysis.matching_skills
                        job["missing_skills"] = analysis.missing_skills
                        logger.debug(f"Match score for '{job['title']}': {analysis.overall_match_score}%")
                    except Exception as e:
                        logger.warning(f"Could not calculate match score for '{job.get('title', 'Unknown')}': {e}")
                        job["resume_match_score"] = 0
                
                # Persist to SQLite so the dashboard surfaces it
                try:
                    from database.models import SessionLocal
                    from database.db_manager import db_manager
                    db = SessionLocal()
                    try:
                        job_listing = JobListing(**{k: v for k, v in job.items() if k in JobListing.model_fields})
                        db_manager.add_job(job_listing, db)
                    finally:
                        db.close()
                except Exception as e:
                    logger.warning(f"Could not persist '{job.get('title', 'Unknown')}' to DB: {e}")

                # Log to Google Sheets if available
                if self.google_sheets and "resume_match_score" in job:
                    try:
                        job_listing = JobListing(**job)
                        self.google_sheets.add_job(job_listing)
                        logger.debug(f"Added to Google Sheets: {job['title']}")
                    except Exception as e:
                        logger.warning(f"Could not add '{job.get('title', 'Unknown')}' to Google Sheets: {e}")

                processed_jobs.append(job)
                
            except Exception as e:
                logger.warning(f"Failed to process job '{job.get('title', 'Unknown')}': {e}")
                continue
        
        return processed_jobs
    
    def _increment_error_count(self):
        """Increment error count and check if we should abort."""
        self.error_count += 1
        if self.error_count > self.max_errors:
            logger.error(f"Too many errors ({self.error_count}), aborting")
            raise Exception(f"Maximum error count ({self.max_errors}) exceeded")
    
    async def run_full_search(self, job_categories: List[Dict[str, Any]]):
        """
        Run full search for all job categories with robust error handling.
        """
        try:
            await self.initialize()
            await self.login()
            
            all_jobs = []
            
            for category in job_categories:
                logger.info(f"\n{'='*60}")
                logger.info(f"Processing category: {category['category']}")
                logger.info(f"{'='*60}")
                
                category_jobs = []
                
                # Process keywords with individual error handling
                for keyword in category['keywords'][:3]:  # Limit to first 3 keywords
                    # Track search run in DB so Dashboard "Recent searches" populates
                    from database.models import SessionLocal
                    from database.db_manager import db_manager
                    db = SessionLocal()
                    search_id = None
                    try:
                        search_record = db_manager.add_search_run({
                            "keywords": keyword,
                            "location": category.get('location', 'United States'),
                            "job_type": category.get('job_type', ['full-time'])[0] if category.get('job_type') else None,
                            "posted_within": "1h",
                        }, db)
                        search_id = search_record.search_id
                    except Exception as e:
                        logger.warning(f"Could not create search_run record: {e}")

                    try:
                        params = JobSearchParams(
                            keywords=keyword,
                            location=category.get('location', 'United States'),
                            job_type=category.get('job_type', ['full-time'])[0] if category.get('job_type') else None,
                            posted_within="1h",
                            max_results=min(15, category.get('max_results', 50))
                        )

                        jobs = await self.search_and_extract_jobs(params)
                        category_jobs.extend(jobs)

                        logger.info(f"Found {len(jobs)} jobs for '{keyword}'")

                        if search_id:
                            try:
                                matched = sum(1 for j in jobs if (j.get("resume_match_score") or 0) >= 70)
                                db_manager.update_search_run(
                                    search_id, db,
                                    status="completed",
                                    total_results=len(jobs),
                                    jobs_scraped=len(jobs),
                                    jobs_matched=matched,
                                )
                            except Exception as e:
                                logger.warning(f"Could not finalize search_run: {e}")

                        # Longer delay between searches to be respectful
                        await asyncio.sleep(random.uniform(8, 15))

                    except Exception as e:
                        logger.error(f"Failed to process keyword '{keyword}': {e}")
                        if search_id:
                            try:
                                db_manager.update_search_run(search_id, db, status="failed", error_message=str(e))
                            except Exception:
                                pass
                        continue  # Continue with next keyword
                    finally:
                        try: db.close()
                        except Exception: pass
                
                all_jobs.extend(category_jobs)
                logger.info(f"Category '{category['category']}' total: {len(category_jobs)} jobs")
                
                # Delay between categories
                await asyncio.sleep(random.uniform(5, 10))
            
            logger.info(f"\n{'='*60}")
            logger.info(f"SEARCH COMPLETED")
            logger.info(f"Total jobs extracted: {len(all_jobs)}")
            
            # Summary statistics
            high_match_jobs = [j for j in all_jobs if j.get('resume_match_score', 0) >= 70]
            logger.info(f"High-match jobs (70%+): {len(high_match_jobs)}")
            
            if self.google_sheets:
                sheet_url = self.google_sheets.get_spreadsheet_url()
                logger.info(f"View results: {sheet_url}")
            
            return all_jobs
            
        except Exception as e:
            logger.error(f"Full search failed: {e}")
            page_info = await self.navigator.get_page_info() if self.navigator else {}
            logger.error(f"Page info at failure: {page_info}")
            raise
        finally:
            await self.cleanup()
    
    async def cleanup(self):
        """Enhanced cleanup with error handling."""
        try:
            if self.page:
                await self.page.close()
                logger.debug("Page closed successfully")
            if self.browser:
                await self.browser.close()
                logger.debug("Browser closed successfully")
            logger.info("Cleanup completed successfully")
        except Exception as e:
            logger.warning(f"Cleanup error (non-critical): {e}")
    
    async def _emergency_cleanup(self):
        """Emergency cleanup in case of critical errors."""
        try:
            if hasattr(self, 'browser') and self.browser:
                await self.browser.close()
        except:
            pass
    
    def get_scraped_jobs(self) -> List[Dict[str, Any]]:
        """Get all jobs scraped in this session."""
        return self.jobs_scraped


# Alias for backward compatibility
LinkedInScraperPlaywright = RobustLinkedInScraper