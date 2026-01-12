"""LinkedIn job scraper using Playwright with login and URL parameter manipulation."""

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

logger = logging.getLogger(__name__)


class JobSearchParams(BaseModel):
    """Parameters for LinkedIn job search."""
    keywords: str
    location: str = settings.default_location
    job_type: Optional[str] = settings.default_job_type
    experience_level: Optional[str] = None
    remote: Optional[bool] = None
    posted_within: Optional[str] = "24h"
    company_size: Optional[str] = None
    max_results: int = settings.max_results_per_search


class LinkedInScraperPlaywright:
    """LinkedIn job scraper using Playwright with login, search, and URL manipulation."""
    
    def __init__(self):
        """Initialize the LinkedIn scraper."""
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.jobs_scraped = []
        self.resume_matcher = None
        self.google_sheets = None
        
    async def initialize(self):
        """Initialize browser and services."""
        try:
            playwright = await async_playwright().start()
            
            # Launch browser (set headless=True for production)
            self.browser = await playwright.chromium.launch(
                headless=False,  # Set to True in production
                args=['--disable-blink-features=AutomationControlled']
            )
            
            # Create new page with realistic viewport
            context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            self.page = await context.new_page()
            
            # Apply stealth mode to bypass detection
            stealth_config = Stealth()
            await stealth_config.apply_stealth_async(self.page)
            logger.info("Stealth mode applied to browser")
            
            # Initialize resume matcher
            if settings.resume_file_path:
                resume_profile = ResumeProfile(
                    resume_file=settings.resume_file_path,
                    skills=settings.skills_list
                )
                self.resume_matcher = ResumeMatcherService(resume_profile)
                logger.info("Resume matcher initialized")
            
            # Initialize Google Sheets
            if settings.google_sheets_id:
                self.google_sheets = GoogleSheetsService()
                logger.info("Google Sheets service initialized")
            
            logger.info("Browser and services initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize: {e}")
            raise
    
    async def login(self):
        """Login to LinkedIn using credentials from settings."""
        try:
            logger.info(f"Navigating to LinkedIn login: {settings.linkedin_url}")
            
            # Go to login page
            await self.page.goto(settings.linkedin_url, wait_until='networkidle')
            await asyncio.sleep(2)
            
            # Enter email with human-like behavior
            logger.info("Entering email...")
            email_input = await self.page.wait_for_selector('input[id="username"]', timeout=10000)
            await asyncio.sleep(random.uniform(0.5, 1.5))
            await email_input.fill(settings.linkedin_email)
            
            # Enter password with human-like behavior
            logger.info("Entering password...")
            password_input = await self.page.wait_for_selector('input[id="password"]', timeout=10000)
            await asyncio.sleep(random.uniform(0.5, 1.5))
            await password_input.fill(settings.linkedin_password)
            
            # Random mouse movement before clicking
            await self.page.mouse.move(
                random.randint(100, 800),
                random.randint(100, 600)
            )
            
            # Click sign in button with delay
            logger.info("Clicking sign in...")
            sign_in_button = await self.page.wait_for_selector('button[type="submit"]', timeout=10000)
            await asyncio.sleep(random.uniform(0.3, 0.8))
            await sign_in_button.click()
            
            # Wait for navigation after login
            await asyncio.sleep(5)
            
            # Check if login was successful by looking for feed or home elements
            try:
                await self.page.wait_for_selector('div.global-nav', timeout=10000)
                logger.info("Successfully logged in to LinkedIn")
            except:
                logger.warning("Login verification timeout - continuing anyway")
            
        except Exception as e:
            logger.error(f"Login failed: {e}")
            raise
    
    async def search_and_extract_jobs(self, params: JobSearchParams) -> List[Dict[str, Any]]:
        """
        Search for jobs using the search bar and extract with URL manipulation.
        
        Steps:
        1. Use search bar to search for role
        2. Click Jobs radio button
        3. Apply Date Posted filter (Past 24 hours)
        4. Modify URL from r86400 to r3600
        5. Extract jobs with links
        
        Args:
            params: Search parameters
            
        Returns:
            List of job dictionaries with match scores
        """
        try:
            logger.info(f"Searching for: {params.keywords}")
            
            # Step 1: Use the search bar
            logger.info("Looking for search bar...")
            search_bar = await self.page.wait_for_selector(
                'input[placeholder*="Search"], input[aria-label*="Search"]', 
                timeout=10000
            )
            await search_bar.fill(params.keywords)
            await search_bar.press('Enter')
            
            await asyncio.sleep(3)
            
            # Step 2: Navigate to Jobs section
            logger.info("Navigating to Jobs section...")
            
            # Check if we're already on a jobs page
            current_url = self.page.url
            if '/jobs/' in current_url:
                logger.info("Already on jobs search page, skipping Jobs navigation")
            else:
                try:
                    # Wait for primary navigation to be visible
                    try:
                        await self.page.wait_for_selector('nav[aria-label="Primary"]', timeout=5000)
                        logger.info("Primary navigation found")
                    except:
                        logger.warning("Primary navigation not found, trying alternative approach")
                    
                    # Method 1: Try to find Jobs link in primary navigation
                    jobs_button = await self.page.query_selector('nav[aria-label="Primary"] a:has-text("Jobs")')
                    
                    # Method 2: Try data-test attribute
                    if not jobs_button:
                        jobs_button = await self.page.query_selector('a[data-test-global-nav-link="jobs"]')
                    
                    # Method 3: Try finding Jobs in the header navigation
                    if not jobs_button:
                        jobs_button = await self.page.query_selector('header a:has-text("Jobs")')
                    
                    # Method 4: Try the filter pills if we're on search results
                    if not jobs_button:
                        jobs_button = await self.page.query_selector('button:text("Jobs"):not(.artdeco-card button)')
                    
                    if jobs_button:
                        # Scroll into view and click
                        await jobs_button.scroll_into_view_if_needed()
                        await jobs_button.click()
                        logger.info("Successfully clicked Jobs button")
                        await asyncio.sleep(3)
                    else:
                        # Take a screenshot for debugging
                        await self.page.screenshot(path="jobs_button_not_found.png")
                        logger.warning("Could not find Jobs button, screenshot saved. Continuing anyway...")
                        
                        # Alternative: Navigate directly to jobs URL
                        jobs_url = f"https://www.linkedin.com/jobs/search/?keywords={params.keywords.replace(' ', '%20')}"
                        logger.info(f"Navigating directly to jobs URL: {jobs_url}")
                        await self.page.goto(jobs_url, wait_until='domcontentloaded', timeout=15000)
                        
                except Exception as e:
                    logger.error(f"Error navigating to Jobs: {e}")
                    # Continue anyway as we might already be on the right page
            
            await asyncio.sleep(2)
            
            # Step 3: Apply Date Posted filter
            logger.info("Applying Date Posted filter...")
            date_filter_applied = False
            
            # Click Date Posted button
            date_button_selectors = [
                'button:has-text("Date posted")',
                'button:has-text("Date Posted")',
                'button[aria-label*="Date posted"]',
                '[data-control-name="date_posted_filter"]'
            ]
            
            for selector in date_button_selectors:
                try:
                    button = await self.page.wait_for_selector(selector, timeout=5000)
                    await button.click()
                    logger.info("Opened Date Posted dropdown")
                    await asyncio.sleep(2)
                    
                    # Click Past 24 hours option
                    past_24_selectors = [
                        'label:has-text("Past 24 hours")',
                        'span:has-text("Past 24 hours")',
                        'input[value="r86400"]',
                        '[aria-label="Past 24 hours"]'
                    ]
                    
                    for past_selector in past_24_selectors:
                        try:
                            option = await self.page.wait_for_selector(past_selector, timeout=3000)
                            await option.click()
                            logger.info("Selected Past 24 hours")
                            
                            # Apply the filter
                            apply_selectors = [
                                'button:has-text("Show results")',
                                'button:has-text("Apply")',
                                'button[aria-label*="Apply"]'
                            ]
                            
                            for apply_selector in apply_selectors:
                                try:
                                    apply_btn = await self.page.wait_for_selector(apply_selector, timeout=3000)
                                    await apply_btn.click()
                                    date_filter_applied = True
                                    logger.info("Applied date filter")
                                    break
                                except:
                                    continue
                            
                            if date_filter_applied:
                                break
                        except:
                            continue
                    
                    if date_filter_applied:
                        break
                except:
                    continue
            
            await asyncio.sleep(3)
            
            # Step 4: Modify URL from r86400 to r3600
            current_url = self.page.url
            logger.info(f"Current URL: {current_url}")
            
            # Check if URL already has the 1-hour filter
            if 'f_TPR=r3600' in current_url:
                logger.info("URL already has 1-hour filter (r3600), skipping navigation")
                await asyncio.sleep(3)  # Just wait for any dynamic content
            else:
                # Need to modify the URL
                if 'f_TPR=' in current_url:
                    # Replace existing time filter with r3600
                    modified_url = re.sub(r'f_TPR=r\d+', 'f_TPR=r3600', current_url)
                else:
                    # Add the parameter if not present
                    separator = '&' if '?' in current_url else '?'
                    modified_url = f"{current_url}{separator}f_TPR=r3600"
                
                logger.info(f"Modified URL (1-hour filter): {modified_url}")
                
                # Navigate with shorter timeout and different wait strategy
                try:
                    await self.page.goto(modified_url, wait_until='domcontentloaded', timeout=15000)
                    await asyncio.sleep(5)  # Wait for jobs to load
                except Exception as e:
                    logger.warning(f"Navigation timeout, continuing anyway: {e}")
                    await asyncio.sleep(3)
            
            # Step 5: Extract jobs from the page
            logger.info("Extracting jobs from 1-hour filtered results...")
            jobs = await self._extract_jobs_with_details()
            
            # Add metadata and calculate match scores
            for job in jobs:
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
                        logger.info(f"Job '{job['title']}' - Match Score: {analysis.overall_match_score}%")
                    except Exception as e:
                        logger.warning(f"Could not calculate match score: {e}")
                        job["resume_match_score"] = 0
                
                # Log to Google Sheets if available
                if self.google_sheets and "resume_match_score" in job:
                    try:
                        job_listing = JobListing(**job)
                        self.google_sheets.add_job(job_listing)
                        logger.info(f"Added job to Google Sheets: {job['title']}")
                    except Exception as e:
                        logger.warning(f"Could not add to Google Sheets: {e}")
            
            # Limit to max_results
            jobs = jobs[:params.max_results]
            self.jobs_scraped.extend(jobs)
            
            logger.info(f"Successfully extracted {len(jobs)} jobs from 1-hour filter")
            return jobs
            
        except Exception as e:
            logger.error(f"Search and extract failed: {e}")
            return []
    
    async def _extract_job_details_from_panel(self) -> Dict[str, Any]:
        """Extract full job details from the opened detail panel."""
        details = {}
        
        try:
            # MORE COMPREHENSIVE selectors for LinkedIn 2024/2025
            desc_selectors = [
                # Most common current selectors
                'div[class*="jobs-description"]',
                'div[class*="job-details"]',
                'section[class*="jobs-description"]',
                'div.jobs-unified-description__content',
                'div#job-details',
                
                # Try broader selectors
                'article[class*="jobs"]',
                'div[class*="description-content"]',
                '[data-job-description]',
                
                # Very broad but specific to job content
                'div.scaffold-layout__detail',
                'div.jobs-search__job-details',
                'div.jobs-view-layout',
                
                # Legacy selectors
                '.jobs-description-content',
                '.details-pane__content'
            ]
            
            # First, wait a bit longer for panel to fully load
            await asyncio.sleep(2)
            
            # Try to find ANY job detail element
            panel_loaded = False
            for selector in desc_selectors:
                try:
                    elem = await self.page.query_selector(selector)
                    if elem:
                        panel_loaded = True
                        logger.info(f"Found panel element with selector: {selector}")
                        break
                except:
                    continue
            
            if not panel_loaded:
                logger.warning("No detail panel found! Taking debug screenshot...")
                await self.page.screenshot(path=f"debug_no_panel_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                
                # Try to get ANY text from the right side of the page
                try:
                    right_panel = await self.page.query_selector('div.scaffold-layout__detail, div[class*="detail"], aside')
                    if right_panel:
                        panel_text = await right_panel.inner_text()
                        logger.info(f"Right panel text length: {len(panel_text) if panel_text else 0}")
                except:
                    pass
            
            # Extract full description - try ALL selectors
            full_description = ""
            for selector in desc_selectors:
                try:
                    desc_elem = await self.page.query_selector(selector)
                    if desc_elem:
                        text = await desc_elem.inner_text()
                        if text and len(text) > 100:  # Meaningful content
                            full_description = text
                            logger.info(f"✓ Found description using selector: {selector} (length: {len(text)})")
                            break
                except:
                    continue
            
            # If still no description, try to get text from the entire right panel
            if not full_description or len(full_description) < 100:
                logger.warning("No description from specific selectors, trying broader approach...")
                try:
                    # Try to get all text from the detail section
                    detail_section = await self.page.query_selector('div.scaffold-layout__detail, aside[class*="scaffold"], div.jobs-search__job-details--container')
                    if detail_section:
                        full_description = await detail_section.inner_text()
                        logger.info(f"Got description from detail section (length: {len(full_description)})")
                except:
                    pass
            
            if full_description:
                # Parse responsibilities
                details['responsibilities'] = self._parse_responsibilities(full_description)
                
                # Parse requirements and determine experience level
                requirements, exp_level, years_num = self._parse_requirements_and_experience(full_description)
                details['requirements'] = requirements
                if exp_level:
                    details['experience_level'] = exp_level
                if years_num is not None:
                    details['level'] = years_num
                
                # Extract skills from full description
                details['skills'] = self._extract_skills_from_full_description(full_description)
                
                # Store full description
                details['description'] = full_description[:500] + "..." if len(full_description) > 500 else full_description
            
            # Try to extract skills from skill badges/tags if present
            skill_badges = await self.page.query_selector_all(
                '.job-details-skill-match__skill-name, .jobs-description__skill-item'
            )
            badge_skills = []
            for badge in skill_badges:
                try:
                    skill_text = await badge.inner_text()
                    if skill_text:
                        badge_skills.append(skill_text.strip())
                except:
                    pass
            
            if badge_skills:
                existing_skills = details.get('skills', [])
                details['skills'] = list(set(existing_skills + badge_skills))[:15]
            
            # Debug if no description found
            if not full_description or len(full_description) < 100:
                logger.warning(f"No meaningful description found (length: {len(full_description)})")
                # Save screenshot for debugging
                await self.page.screenshot(path=f"debug_no_description_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                
        except Exception as e:
            logger.debug(f"Could not extract full details from panel: {e}")
            
        return details
    
    def _parse_responsibilities(self, description: str) -> List[str]:
        """Parse responsibilities section from job description."""
        responsibilities = []
        lines = description.split('\n')
        
        # Look for responsibilities section
        in_responsibilities = False
        for i, line in enumerate(lines):
            line_lower = line.lower().strip()
            
            # Check if we're entering responsibilities section
            if any(keyword in line_lower for keyword in [
                'responsibilities:', 'what you\'ll do:', 'you will:', 
                'your responsibilities:', 'key responsibilities:', 'duties:'
            ]):
                in_responsibilities = True
                continue
                
            # Check if we're leaving responsibilities section
            elif any(keyword in line_lower for keyword in [
                'requirements:', 'qualifications:', 'skills:', 'what we need:',
                'about you:', 'experience:', 'education:', 'benefits:'
            ]):
                in_responsibilities = False
                
            # Collect responsibility lines
            elif in_responsibilities and line.strip():
                # Clean up bullet points and numbers
                cleaned = re.sub(r'^[\s•\-\*\d\.]+', '', line.strip())
                if cleaned and len(cleaned) > 10:
                    responsibilities.append(cleaned)
                    if len(responsibilities) >= 5:  # Limit to 5 responsibilities
                        break
        
        return responsibilities if responsibilities else ["See job posting for full responsibilities"]
    
    def _extract_years_as_level(self, text: str) -> Optional[int]:
        """Extract years of experience as a numeric level."""
        
        # Comprehensive patterns to match years of experience
        patterns = [
            r'(\d+)\+?\s*years?\s*(?:of\s*)?(?:experience|exp)',
            r'(\d+)\s*-\s*(\d+)\s*years?\s*(?:of\s*)?(?:experience|exp)',  # Take lower bound
            r'minimum\s*(?:of\s*)?(\d+)\s*years?',
            r'at\s*least\s*(\d+)\s*years?',
            r'(\d+)\s*years?\s*minimum',
            r'requires?\s*(\d+)\s*years?',
            r'(\d+)\s*years?\s*required',
            r'(\d+)\s*years?\s*preferred'
        ]
        
        text_lower = text.lower()
        for pattern in patterns:
            match = re.search(pattern, text_lower)
            if match:
                # Return the first number found (lower bound if range)
                return int(match.group(1))
        
        # Check for entry-level indicators
        if any(term in text_lower for term in ['entry level', 'entry-level', '0-2 years', 'fresh graduate', 'new graduate']):
            return 0
        
        return None
    
    def _parse_requirements_and_experience(self, description: str) -> Tuple[List[str], Optional[str], Optional[int]]:
        """Parse requirements, experience level, and numeric years."""
        requirements = []
        exp_level = None
        
        # Extract years as number using dedicated function
        years_num = self._extract_years_as_level(description)
        
        # Determine experience level based on years
        if years_num is not None:
            if years_num <= 2:
                exp_level = 'entry'
            elif years_num <= 5:
                exp_level = 'associate'
            elif years_num <= 8:
                exp_level = 'mid-senior'
            elif years_num <= 12:
                exp_level = 'director'
            else:
                exp_level = 'executive'
            
            # Add to requirements
            requirements.append(f"{years_num}+ years of experience required")
        
        # Extract other requirements
        lines = description.split('\n')
        in_requirements = False
        
        for line in lines:
            line_lower = line.lower().strip()
            
            # Check if we're in requirements section
            if any(keyword in line_lower for keyword in [
                'requirements:', 'qualifications:', 'must have:', 'required:'
            ]):
                in_requirements = True
                continue
            elif any(keyword in line_lower for keyword in [
                'responsibilities:', 'benefits:', 'nice to have:', 'preferred:'
            ]):
                in_requirements = False
                
            # Collect requirement lines
            elif in_requirements and line.strip():
                cleaned = re.sub(r'^[\s•\-\*\d\.]+', '', line.strip())
                if cleaned and len(cleaned) > 10:
                    requirements.append(cleaned)
                    if len(requirements) >= 5:
                        break
        
        # Look for degree requirements
        if 'bachelor' in desc_lower or 'bs ' in desc_lower or 'ba ' in desc_lower:
            if not any('bachelor' in req.lower() for req in requirements):
                requirements.append("Bachelor's degree required")
        elif 'master' in desc_lower or 'ms ' in desc_lower or 'mba' in desc_lower:
            if not any('master' in req.lower() for req in requirements):
                requirements.append("Master's degree preferred")
                
        return requirements[:5], exp_level, years_num
    
    def _extract_skills_from_full_description(self, description: str) -> List[str]:
        """Extract technical skills from the full job description."""
        skills = []
        
        # Comprehensive tech skills list
        tech_skills = [
            'Java', 'Python', 'JavaScript', 'TypeScript', 'React', 'Angular', 'Vue', 
            'Spring', 'Spring Boot', 'Node.js', 'Express', '.NET', 'C#', 'C++',
            'SQL', 'NoSQL', 'MongoDB', 'PostgreSQL', 'MySQL', 'Oracle', 'Redis',
            'AWS', 'Azure', 'GCP', 'Cloud', 'Docker', 'Kubernetes', 'Jenkins',
            'CI/CD', 'DevOps', 'Microservices', 'REST', 'RESTful', 'API', 'GraphQL',
            'Git', 'GitHub', 'GitLab', 'Agile', 'Scrum', 'JIRA', 'Kafka', 'RabbitMQ',
            'HTML', 'CSS', 'SASS', 'Bootstrap', 'Material UI', 'Tailwind',
            'JPA', 'Hibernate', 'Maven', 'Gradle', 'JUnit', 'Jest', 'Selenium',
            'Machine Learning', 'AI', 'TensorFlow', 'PyTorch', 'Pandas', 'NumPy'
        ]
        
        desc_lower = description.lower()
        seen_skills = set()
        
        # Extract skills that appear in the description
        for skill in tech_skills:
            # Use word boundaries for more accurate matching
            pattern = r'\b' + re.escape(skill.lower()) + r'\b'
            if re.search(pattern, desc_lower) and skill not in seen_skills:
                skills.append(skill)
                seen_skills.add(skill)
        
        return skills[:15]  # Limit to 15 most relevant skills

    async def _extract_jobs_with_details(self) -> List[Dict[str, Any]]:
        """Extract job listings with all details including links."""
        jobs = []
        
        try:
            # Wait for job cards to load with shorter timeout
            try:
                await self.page.wait_for_selector(
                    'div.job-card-container, li.jobs-search-results__list-item, ul.scaffold-layout__list-container',
                    timeout=7000
                )
            except:
                logger.warning("Timeout waiting for job cards, checking if any exist...")
            
            # Human-like scrolling to trigger lazy loading
            await self.page.mouse.wheel(0, random.randint(200, 400))
            await asyncio.sleep(random.uniform(1, 2))
            await self.page.mouse.wheel(0, random.randint(200, 400))
            await asyncio.sleep(random.uniform(0.5, 1.5))
            
            # Try different selectors for job cards - updated for current LinkedIn
            job_card_selectors = [
                '.job-search-card',  # Current LinkedIn primary selector
                'div.job-card-container',
                'li.jobs-search-results__list-item',
                'div[data-job-id]',
                'li[data-occludable-job-id]'
            ]
            
            job_cards = []
            for selector in job_card_selectors:
                cards = await self.page.query_selector_all(selector)
                if cards:
                    job_cards = cards
                    logger.info(f"Found {len(cards)} job cards using selector: {selector}")
                    break
            
            if not job_cards:
                logger.warning("No job cards found on page")
                return jobs
            
            for i, card in enumerate(job_cards):
                try:
                    job_data = {}
                    
                    # Extract job ID
                    job_id = await card.get_attribute('data-job-id')
                    if not job_id:
                        job_id = await card.get_attribute('data-occludable-job-id')
                    job_data["job_id"] = job_id or f"job_{i}"
                    
                    # Extract title - simplified for current LinkedIn structure
                    title = ""
                    
                    # Primary selector for job title
                    title_elem = await card.query_selector('.base-search-card__title')
                    if title_elem:
                        try:
                            title = await title_elem.inner_text()
                            title = title.strip()
                        except:
                            pass
                    
                    # Fallback selectors if primary fails
                    if not title:
                        fallback_selectors = [
                            'h3.base-search-card__title',
                            'a.job-card-list__title strong',
                            'div.job-card-container a strong',
                            'a.job-card-container__link span[aria-hidden="true"]'
                        ]
                        for selector in fallback_selectors:
                            elem = await card.query_selector(selector)
                            if elem:
                                try:
                                    title = await elem.inner_text()
                                    title = title.strip()
                                    if title:
                                        break
                                except:
                                    pass
                    
                    job_data["title"] = title or "Job Title Not Available"
                    
                    # Extract URL
                    url = ""
                    link_elem = await card.query_selector('a.job-card-container__link, a.job-card-list__title, a[data-tracking-control-name*="job"]')
                    if link_elem:
                        try:
                            href = await link_elem.get_attribute('href')
                            if href:
                                if href.startswith('/'):
                                    url = f"https://www.linkedin.com{href}"
                                else:
                                    url = href
                                # Clean URL - remove tracking parameters
                                url = url.split('?')[0] if '?' in url else url
                        except:
                            pass
                    job_data["url"] = url
                    
                    # Extract company - two-stage approach with stealth mode
                    company = ""
                    
                    # Stage 1: Try extracting from job card
                    card_selectors = [
                        'a[class*="subtitle"]',
                        'span[class*="subtitle"]',
                        '.base-search-card__subtitle > a',
                        '.base-search-card__subtitle',
                        '.artdeco-entity-lockup__subtitle',
                        '[data-test-job-card-company-name]',
                        'h4.job-card-container__company-name',
                        'span.job-card-container__primary-description'
                    ]
                    
                    for selector in card_selectors:
                        elem = await card.query_selector(selector)
                        if elem:
                            try:
                                text = await elem.inner_text()
                                text = text.strip()
                                # Validate it's likely a company name
                                if text and len(text) > 2 and not any(skip in text.lower() for skip in ['remote', 'ago', 'applicant', 'hybrid', 'on-site']):
                                    company = text
                                    break
                            except:
                                pass
                    
                    # Stage 2: If no company found, click job to open details panel
                    if not company or company == "Unknown Company":
                        try:
                            # Add human-like delay
                            await asyncio.sleep(random.uniform(0.5, 1.5))
                            
                            # Click the job card to open details
                            await card.click()
                            
                            # Wait for details panel to load
                            await self.page.wait_for_selector(
                                '.jobs-unified-top-card__company-name, .top-card-layout__company-url, .jobs-view-top-card__company',
                                timeout=3000
                            )
                            
                            # Extract from detail panel (more reliable)
                            detail_selectors = [
                                '.jobs-unified-top-card__company-name a',
                                '.top-card-layout__company-url',
                                '.jobs-view-top-card__company',
                                '.jobs-unified-top-card__subtitle-primary-grouping span',
                                'a[href*="/company/"]'
                            ]
                            
                            for selector in detail_selectors:
                                elem = await self.page.query_selector(selector)
                                if elem:
                                    try:
                                        text = await elem.inner_text()
                                        text = text.strip()
                                        if text and len(text) > 2:
                                            company = text
                                            break
                                    except:
                                        pass
                            
                            # Close detail panel (ESC key) to return to list
                            await self.page.keyboard.press('Escape')
                            await asyncio.sleep(0.5)
                            
                        except Exception as e:
                            logger.debug(f"Failed to extract from details panel: {e}")
                    
                    # Final fallback: extract from aria-label
                    if not company:
                        try:
                            aria_label = await card.get_attribute('aria-label')
                            if aria_label and ' at ' in aria_label:
                                # Extract company from "Job Title at Company Name in Location"
                                parts = aria_label.split(' at ')
                                if len(parts) > 1:
                                    company_part = parts[1].split(' in ')[0]
                                    company = company_part.strip()
                        except:
                            pass
                    
                    # Debug logging if still no company found
                    if not company or company == "Unknown Company":
                        logger.warning(f"Failed to extract company for job {i}")
                        # Save HTML for debugging
                        try:
                            card_html = await card.inner_html()
                            with open(f"debug_card_{i}.html", 'w') as f:
                                f.write(card_html)
                            await card.screenshot(path=f"debug_company_card_{i}.png")
                        except:
                            pass
                    
                    job_data["company"] = company or "Unknown Company"
                    
                    # Extract location - with fallback
                    location_elem = await card.query_selector(
                        'li.job-card-container__metadata-item, .job-card-container__metadata-wrapper span, span.job-card-container__location'
                    )
                    if location_elem:
                        try:
                            job_data["location"] = await location_elem.inner_text()
                        except:
                            job_data["location"] = "Location not specified"
                    else:
                        job_data["location"] = "Location not specified"
                    
                    # Extract posted date
                    posted_date = ""
                    time_elem = await card.query_selector('time')
                    if time_elem:
                        try:
                            posted_date = await time_elem.inner_text()
                        except:
                            pass
                    job_data["posted_date"] = posted_date or "Recently"
                    
                    # Extract applicants count
                    applicants = ""
                    applicants_selectors = [
                        'span:has-text("applicants")',
                        'span:has-text("applicant")',
                        '.job-card-container__applicant-count',
                        'span.job-card-container__footer-item'
                    ]
                    for selector in applicants_selectors:
                        app_elem = await card.query_selector(selector)
                        if app_elem:
                            try:
                                text = await app_elem.inner_text()
                                if 'applicant' in text.lower():
                                    applicants = text
                                    break
                            except:
                                continue
                    job_data["applicants_count"] = applicants
                    
                    # Extract salary if available
                    salary = ""
                    salary_selectors = [
                        'span:has-text("$")',
                        '.job-card-container__salary-info',
                        'span.job-card-container__metadata-item:has-text("$")'
                    ]
                    for selector in salary_selectors:
                        salary_elem = await card.query_selector(selector)
                        if salary_elem:
                            try:
                                text = await salary_elem.inner_text()
                                if '$' in text:
                                    salary = text
                                    break
                            except:
                                continue
                    job_data["salary_range"] = salary or ""
                    
                    # Extract description - look for snippet or benefits
                    description = ""
                    desc_selectors = [
                        '.job-card-list__snippet',
                        '.job-card-search__body',
                        '.job-card-container__benefits',
                        'ul.job-card-container__benefits li',
                        '.base-search-card__metadata',
                        '[class*="snippet"]',
                        '[class*="description"]'
                    ]
                    desc_parts = []
                    for selector in desc_selectors:
                        desc_elems = await card.query_selector_all(selector)
                        for desc_elem in desc_elems:
                            try:
                                text = await desc_elem.inner_text()
                                if text and text.strip() and len(text.strip()) > 20:
                                    desc_parts.append(text.strip())
                            except:
                                continue
                    
                    # Combine all description parts
                    if desc_parts:
                        description = " | ".join(desc_parts[:3])  # Limit to 3 parts
                    job_data["description"] = description or "See job posting for details"
                    
                    # Extract job type and experience level from badges/metadata and other areas
                    job_type = None
                    exp_level = None
                    
                    # First check metadata items - expanded selectors
                    metadata_selectors = [
                        '.job-card-container__metadata-item',
                        'span.job-card-search__badge',
                        '.base-search-card__metadata span',
                        'li.result-benefits__text',
                        '[class*="job-type"]',
                        '[class*="employment"]',
                        '[class*="seniority"]',
                        '.job-card-container__footer-item'
                    ]
                    
                    for selector in metadata_selectors:
                        items = await card.query_selector_all(selector)
                        for item in items:
                            try:
                                text = await item.inner_text()
                                text_lower = text.lower().strip()
                                
                                # Map to valid job type enum values
                                if not job_type:
                                    if 'full-time' in text_lower or 'full time' in text_lower:
                                        job_type = 'full-time'
                                    elif 'part-time' in text_lower or 'part time' in text_lower:
                                        job_type = 'part-time'
                                    elif 'contract' in text_lower:
                                        job_type = 'contract'
                                    elif 'temporary' in text_lower or 'temp' in text_lower:
                                        job_type = 'temporary'
                                    elif 'internship' in text_lower or 'intern' in text_lower:
                                        job_type = 'internship'
                                    elif 'volunteer' in text_lower:
                                        job_type = 'volunteer'
                                
                                # Map to valid experience level enum values
                                if not exp_level:
                                    if 'entry' in text_lower or 'junior' in text_lower:
                                        exp_level = 'entry'
                                    elif 'associate' in text_lower:
                                        exp_level = 'associate'
                                    elif 'mid-senior' in text_lower or 'mid senior' in text_lower:
                                        exp_level = 'mid-senior'
                                    elif 'senior' in text_lower and 'mid' not in text_lower:
                                        exp_level = 'mid-senior'  # Map senior to mid-senior
                                    elif 'director' in text_lower or 'lead' in text_lower or 'principal' in text_lower:
                                        exp_level = 'director'
                                    elif 'executive' in text_lower or 'vp' in text_lower or 'president' in text_lower:
                                        exp_level = 'executive'
                            except:
                                continue
                    
                    # If still not found, check the title for clues about experience level
                    if not exp_level and title:
                        title_lower = title.lower()
                        if 'senior' in title_lower or 'sr.' in title_lower or 'sr ' in title_lower:
                            exp_level = 'mid-senior'
                        elif 'junior' in title_lower or 'jr.' in title_lower or 'jr ' in title_lower:
                            exp_level = 'entry'
                        elif 'lead' in title_lower or 'principal' in title_lower:
                            exp_level = 'director'
                        elif 'director' in title_lower or 'manager' in title_lower:
                            exp_level = 'director'
                        elif 'vp' in title_lower or 'vice president' in title_lower:
                            exp_level = 'executive'
                    
                    # Set to None if not found (not empty string)
                    job_data["job_type"] = job_type
                    job_data["experience_level"] = exp_level
                    
                    # Extract skills from description and title if available
                    skills = []
                    # Expanded skill list based on user's job search categories
                    tech_skills = [
                        'Java', 'Python', 'JavaScript', 'React', 'Angular', 'Spring', 'Spring Boot', 
                        'SQL', 'AWS', 'Azure', 'GCP', 'Cloud', 'Docker', 'Kubernetes', 'REST', 
                        'RESTful', 'API', 'Git', 'Agile', 'Node.js', 'TypeScript', 'MongoDB', 
                        'PostgreSQL', 'MySQL', 'Redis', 'Jenkins', 'CI/CD', 'Microservices',
                        'HTML', 'CSS', 'Vue', 'Redux', 'GraphQL', 'Kafka', 'RabbitMQ',
                        'JPA', 'Hibernate', 'Maven', 'Gradle', 'JUnit', 'Testing',
                        'Full Stack', 'Frontend', 'Backend', 'DevOps', 'Scrum', 'TDD'
                    ]
                    
                    # Check both description and title for skills
                    combined_text = f"{description} {title}".lower() if description else title.lower() if title else ""
                    seen_skills = set()
                    
                    for skill in tech_skills:
                        if skill.lower() in combined_text and skill not in seen_skills:
                            skills.append(skill)
                            seen_skills.add(skill)
                    
                    # Also extract requirements from description
                    requirements = []
                    if "experience" in combined_text:
                        requirements.append("Professional experience required")
                    if "degree" in combined_text or "bachelor" in combined_text:
                        requirements.append("Bachelor's degree or equivalent")
                    
                    job_data["skills"] = skills[:10] if skills else ["Not specified"]
                    job_data["requirements"] = requirements if requirements else ["See job posting for requirements"]
                    job_data["qualifications"] = []
                    job_data["responsibilities"] = []
                    job_data["level"] = None  # Will be populated from detail panel
                    
                    # Click job to get full details
                    logger.info(f"Extracting detailed info for job {i+1}/{len(job_cards)}: {title}")
                    try:
                        # Make sure card is in view
                        await card.scroll_into_view_if_needed()
                        await asyncio.sleep(0.5)
                        
                        # Try multiple click strategies
                        clicked = False
                        
                        # Strategy 1: Click the title link
                        title_link = await card.query_selector('a[class*="job-card-list__title"], a.job-card-container__link, a[href*="/jobs/view/"]')
                        if title_link:
                            try:
                                await title_link.click()
                                clicked = True
                                logger.debug("Clicked title link")
                            except:
                                pass
                        
                        # Strategy 2: Click anywhere on the card
                        if not clicked:
                            try:
                                await card.click()
                                clicked = True
                                logger.debug("Clicked card element")
                            except:
                                pass
                        
                        # Strategy 3: Use JavaScript to click
                        if not clicked:
                            try:
                                await self.page.evaluate('(element) => element.click()', card)
                                clicked = True
                                logger.debug("Clicked via JavaScript")
                            except:
                                pass
                        
                        if not clicked:
                            logger.warning(f"Could not click job {i+1}")
                            continue
                        
                        # Wait longer and check if panel loaded
                        await asyncio.sleep(4)  # Increased wait time
                        
                        # Check if we're on a new page (job detail page) or still on search
                        current_url = self.page.url
                        if '/jobs/view/' in current_url:
                            logger.info("Navigated to job detail page")
                            # Wait for the page to load
                            await self.page.wait_for_load_state('networkidle')
                        
                        # Extract full details from the panel
                        full_details = await self._extract_job_details_from_panel()
                        
                        # If no details and we have a URL, try navigating directly
                        if (not full_details or not full_details.get('responsibilities') or 
                            full_details.get('responsibilities') == ["See job posting for full responsibilities"]):
                            if job_data.get('url'):
                                logger.warning(f"No details from panel, trying direct navigation to {job_data['url']}")
                                try:
                                    await self.page.goto(job_data['url'], wait_until='networkidle', timeout=10000)
                                    await asyncio.sleep(3)
                                    full_details = await self._extract_job_details_from_panel()
                                    # Navigate back
                                    await self.page.go_back()
                                    await asyncio.sleep(2)
                                except Exception as e:
                                    logger.error(f"Direct navigation failed: {e}")
                        
                        # Update job data with full details
                        if full_details:
                            # Update with better data from detail panel
                            if full_details.get('description'):
                                job_data['description'] = full_details['description']
                            if full_details.get('responsibilities'):
                                job_data['responsibilities'] = full_details['responsibilities']
                            if full_details.get('requirements'):
                                job_data['requirements'] = full_details['requirements']
                            if full_details.get('skills'):
                                # Merge skills from both sources
                                existing_skills = job_data.get('skills', [])
                                if isinstance(existing_skills, list) and existing_skills != ["Not specified"]:
                                    all_skills = list(set(existing_skills + full_details['skills']))
                                    job_data['skills'] = all_skills[:15]
                                else:
                                    job_data['skills'] = full_details['skills']
                            if full_details.get('experience_level'):
                                job_data['experience_level'] = full_details['experience_level']
                            if full_details.get('level') is not None:
                                job_data['level'] = full_details['level']
                                logger.info(f"Extracted experience years: {full_details['level']}")
                        
                        # Close detail panel (ESC key) to return to job list
                        await self.page.keyboard.press('Escape')
                        await asyncio.sleep(0.5)
                        
                    except Exception as e:
                        logger.debug(f"Could not get full details for job {i}: {e}")
                        # Keep the default values if extraction fails
                    
                    # Add ALL jobs - even with missing data
                    # LinkedIn already filtered for relevant results
                    jobs.append(job_data)
                    logger.info(f"Extracted: {job_data.get('title', 'Unknown')} at {job_data.get('company', 'Unknown')} - Salary: {job_data.get('salary_range', 'N/A')}")
                    
                    # Log if URL is missing for debugging
                    if not job_data.get("url"):
                        logger.debug(f"Note: Job '{job_data.get('title')}' has no URL")
                    
                except Exception as e:
                    logger.warning(f"Failed to extract job from card: {e}")
                    continue
            
            logger.info(f"Extracted {len(jobs)} jobs from current page")
            
        except Exception as e:
            logger.error(f"Failed to extract jobs: {e}")
        
        return jobs
    
    async def run_full_search(self, job_categories: List[Dict[str, Any]]):
        """
        Run full search for all job categories.
        
        Args:
            job_categories: List of job category configurations
        """
        try:
            await self.initialize()
            await self.login()
            
            all_jobs = []
            
            for category in job_categories:
                logger.info(f"\n{'='*60}")
                logger.info(f"Processing category: {category['category']}")
                logger.info(f"{'='*60}")
                
                # Search each keyword in the category
                for keyword in category['keywords'][:3]:  # Limit to first 3 keywords
                    params = JobSearchParams(
                        keywords=keyword,
                        location=category.get('location', 'United States'),
                        job_type=category.get('job_type', ['full-time'])[0],
                        posted_within="24h",  # Will be changed to 1 hour
                        max_results=min(20, category.get('max_results', 50))
                    )
                    
                    jobs = await self.search_and_extract_jobs(params)
                    all_jobs.extend(jobs)
                    
                    logger.info(f"Found {len(jobs)} jobs for '{keyword}'")
                    
                    # Delay between searches
                    await asyncio.sleep(5)
            
            logger.info(f"\n{'='*60}")
            logger.info(f"Total jobs extracted: {len(all_jobs)}")
            
            # Summary of high-match jobs
            high_match_jobs = [j for j in all_jobs if j.get('resume_match_score', 0) >= 70]
            logger.info(f"High-match jobs (70%+): {len(high_match_jobs)}")
            
            if self.google_sheets:
                sheet_url = self.google_sheets.get_spreadsheet_url()
                logger.info(f"View results in Google Sheets: {sheet_url}")
            
            return all_jobs
            
        except Exception as e:
            logger.error(f"Full search failed: {e}")
            raise
        finally:
            await self.cleanup()
    
    async def cleanup(self):
        """Clean up browser resources."""
        try:
            if self.page:
                await self.page.close()
            if self.browser:
                await self.browser.close()
            logger.info("Browser cleanup completed")
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
    
    def get_scraped_jobs(self) -> List[Dict[str, Any]]:
        """Get all jobs scraped in this session."""
        return self.jobs_scraped


async def test_scraper():
    """Test the LinkedIn scraper with login and URL manipulation."""
    import json
    
    # Load job categories
    with open('config/job_preferences.json', 'r') as f:
        config = json.load(f)
    
    scraper = LinkedInScraperPlaywright()
    
    try:
        print("Starting LinkedIn Scraper Test")
        print("=" * 60)
        print("This will:")
        print("1. Login to LinkedIn")
        print("2. Search for jobs using search bar")
        print("3. Click Jobs filter")
        print("4. Apply 'Past 24 hours' filter")
        print("5. Change URL to 1-hour filter (r3600)")
        print("6. Extract jobs with match scores")
        print("7. Log to Google Sheets")
        print("=" * 60)
        
        # Test with first category only
        test_categories = [config['job_categories'][0]]  # Just test first category
        
        jobs = await scraper.run_full_search(test_categories)
        
        print(f"\n✅ Test completed successfully!")
        print(f"Total jobs extracted: {len(jobs)}")
        
        if jobs:
            print("\nSample jobs:")
            for job in jobs[:5]:
                print(f"\n- {job.get('title', 'N/A')} at {job.get('company', 'N/A')}")
                print(f"  URL: {job.get('url', 'N/A')}")
                print(f"  Match Score: {job.get('resume_match_score', 0)}%")
                print(f"  Posted: {job.get('posted_date', 'N/A')}")
        
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("\n🔧 Testing LinkedIn Scraper with Login and URL Manipulation...")
    asyncio.run(test_scraper())