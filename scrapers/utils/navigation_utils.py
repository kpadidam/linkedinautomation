"""Robust navigation utilities for handling LinkedIn's dynamic UI and network issues."""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from playwright.async_api import Page, Response, TimeoutError as PlaywrightTimeoutError

from .retry_utils import retry_navigation, NAVIGATION_RETRY, retry_until_success
from .element_utils import SafeElementFinder

logger = logging.getLogger(__name__)


class NavigationState:
    """Track navigation state to enable recovery."""
    
    def __init__(self):
        self.current_url: Optional[str] = None
        self.previous_url: Optional[str] = None
        self.page_title: Optional[str] = None
        self.key_elements_present: bool = False
        self.last_successful_operation: Optional[str] = None
        self.navigation_history: List[str] = []
    
    def update(
        self, 
        url: str, 
        title: str = "", 
        elements_present: bool = False, 
        operation: str = ""
    ):
        """Update navigation state."""
        self.previous_url = self.current_url
        self.current_url = url
        self.page_title = title
        self.key_elements_present = elements_present
        self.last_successful_operation = operation
        if url not in self.navigation_history[-3:]:  # Keep last 3 URLs
            self.navigation_history.append(url)
            if len(self.navigation_history) > 10:
                self.navigation_history = self.navigation_history[-10:]


class LinkedInNavigator:
    """Robust navigation utilities for LinkedIn scraping."""
    
    def __init__(self, page: Page):
        self.page = page
        self.element_finder = SafeElementFinder(page)
        self.state = NavigationState()
        self.base_url = "https://www.linkedin.com"
        
        # Common selectors that indicate page readiness
        self.readiness_indicators = {
            'home': ['.global-nav', '.feed-container'],
            'jobs': ['.jobs-search-results-list', '.scaffold-layout'],
            'job_detail': ['.jobs-unified-top-card', '.jobs-description'],
            'search': ['.search-results-container', '.reusable-search-filters']
        }
    
    @retry_navigation()
    async def goto_with_retry(
        self, 
        url: str, 
        wait_until: str = "domcontentloaded",
        timeout: int = 30000,
        expected_selectors: Optional[List[str]] = None
    ) -> bool:
        """
        Navigate to URL with retry logic and state validation.
        
        Args:
            url: Target URL
            wait_until: When to consider navigation complete
            timeout: Maximum wait time
            expected_selectors: Selectors that should be present when page is ready
        """
        try:
            logger.info(f"Navigating to: {url}")
            
            # Handle relative URLs
            if url.startswith('/'):
                url = f"{self.base_url}{url}"
            
            # Navigate with timeout
            response = await self.page.goto(
                url, 
                wait_until=wait_until, 
                timeout=timeout
            )
            
            # Check response status
            if response and response.status >= 400:
                logger.warning(f"Navigation returned status {response.status}")
                
            # Wait for page to stabilize
            await asyncio.sleep(2)
            
            # Verify page loaded correctly
            current_url = self.page.url
            page_title = await self.page.title()
            
            # Check for LinkedIn login redirect
            if '/login' in current_url and '/login' not in url:
                logger.warning("Redirected to login page unexpectedly")
                return False
            
            # Check for expected elements if provided
            elements_ready = True
            if expected_selectors:
                elements_ready = await self.element_finder.verify_page_ready(expected_selectors)
            
            # Dismiss any overlays
            await self.element_finder.dismiss_overlays()
            
            # Update navigation state
            self.state.update(current_url, page_title, elements_ready, "navigation")
            
            logger.info(f"Navigation successful: {current_url}")
            return True
            
        except PlaywrightTimeoutError:
            logger.warning(f"Navigation timeout to {url}")
            return False
        except Exception as e:
            logger.error(f"Navigation failed to {url}: {e}")
            return False
    
    async def wait_for_navigation_complete(
        self, 
        timeout: int = 15000, 
        stability_timeout: int = 2000
    ) -> bool:
        """
        Wait for navigation to complete and page to stabilize.
        
        Args:
            timeout: Maximum wait time
            stability_timeout: Time to wait for page stability
        """
        try:
            # Wait for network to be idle
            await self.page.wait_for_load_state('networkidle', timeout=timeout)
            
            # Additional wait for dynamic content
            await asyncio.sleep(stability_timeout / 1000)
            
            # Dismiss any overlays that might have appeared
            await self.element_finder.dismiss_overlays()
            
            return True
            
        except PlaywrightTimeoutError:
            logger.warning("Navigation completion timeout")
            return False
    
    async def modify_url_parameters(
        self, 
        parameter_updates: Dict[str, str],
        navigate: bool = True
    ) -> str:
        """
        Modify URL parameters safely.
        
        Args:
            parameter_updates: Dictionary of parameter updates
            navigate: Whether to navigate to the modified URL
            
        Returns:
            Modified URL string
        """
        current_url = self.page.url
        parsed = urlparse(current_url)
        query_params = parse_qs(parsed.query)
        
        # Update parameters
        for key, value in parameter_updates.items():
            query_params[key] = [value]
        
        # Rebuild URL
        new_query = urlencode(query_params, doseq=True)
        new_parsed = parsed._replace(query=new_query)
        modified_url = urlunparse(new_parsed)
        
        logger.info(f"Modified URL: {current_url} -> {modified_url}")
        
        if navigate:
            success = await self.goto_with_retry(modified_url)
            if not success:
                logger.warning("Failed to navigate to modified URL")
                return current_url
        
        return modified_url
    
    async def ensure_linkedin_jobs_page(self) -> bool:
        """
        Ensure we're on a LinkedIn jobs page with proper filters.
        
        Returns:
            True if successfully on jobs page
        """
        current_url = self.page.url
        
        # Check if already on jobs page
        if '/jobs/search' in current_url or '/jobs/' in current_url:
            logger.debug("Already on LinkedIn jobs page")
            
            # Verify page is ready
            jobs_indicators = self.readiness_indicators.get('jobs', [])
            await self.element_finder.wait_for_any_element(jobs_indicators, timeout=5000)
            return True
        
        # Navigate to jobs page
        jobs_url = f"{self.base_url}/jobs"
        return await self.goto_with_retry(
            jobs_url, 
            expected_selectors=self.readiness_indicators.get('jobs')
        )
    
    async def apply_time_filter(self, time_period: str = "r3600") -> bool:
        """
        Apply time filter to current jobs search.
        
        Args:
            time_period: Time filter parameter (r3600=1hr, r86400=24hr)
        """
        try:
            current_url = self.page.url
            
            # Check if already has the desired filter
            if f"f_TPR={time_period}" in current_url:
                logger.info(f"Time filter {time_period} already applied")
                return True
            
            # Method 1: Try to use the UI filter
            ui_success = await self._apply_time_filter_via_ui(time_period)
            if ui_success:
                return True
            
            # Method 2: Modify URL directly
            logger.info("Applying time filter via URL modification")
            
            parameter_updates = {"f_TPR": time_period}
            modified_url = await self.modify_url_parameters(parameter_updates, navigate=True)
            
            # Verify filter was applied
            await asyncio.sleep(3)
            final_url = self.page.url
            
            if f"f_TPR={time_period}" in final_url:
                logger.info(f"Time filter {time_period} successfully applied")
                return True
            else:
                logger.warning("Time filter application verification failed")
                return False
                
        except Exception as e:
            logger.error(f"Failed to apply time filter: {e}")
            return False
    
    async def _apply_time_filter_via_ui(self, time_period: str) -> bool:
        """Try to apply time filter through UI interactions."""
        try:
            # Click Date Posted button
            date_selectors = [
                'button:has-text("Date posted")',
                'button:has-text("Date Posted")',
                'button[aria-label*="Date posted"]',
                '[data-control-name="date_posted_filter"]'
            ]
            
            clicked = await self.element_finder.safe_click(
                date_selectors[0],
                alternative_selectors=date_selectors[1:]
            )
            
            if not clicked:
                logger.debug("Could not click date posted button")
                return False
            
            await asyncio.sleep(1)
            
            # Select appropriate time period
            time_selectors = {
                "r3600": [  # Past hour
                    'label:has-text("Past hour")',
                    'span:has-text("Past hour")',
                    'input[value="r3600"]'
                ],
                "r86400": [  # Past 24 hours  
                    'label:has-text("Past 24 hours")',
                    'span:has-text("Past 24 hours")',
                    'input[value="r86400"]'
                ]
            }
            
            period_selectors = time_selectors.get(time_period, time_selectors["r3600"])
            
            selected = await self.element_finder.safe_click(
                period_selectors[0],
                alternative_selectors=period_selectors[1:]
            )
            
            if not selected:
                logger.debug(f"Could not select time period {time_period}")
                return False
            
            # Apply the filter
            apply_selectors = [
                'button:has-text("Show results")',
                'button:has-text("Apply")',
                'button[aria-label*="Apply"]'
            ]
            
            applied = await self.element_finder.safe_click(
                apply_selectors[0],
                alternative_selectors=apply_selectors[1:]
            )
            
            if applied:
                await asyncio.sleep(2)
                logger.info("Time filter applied via UI")
                return True
            
            return False
            
        except Exception as e:
            logger.debug(f"UI time filter application failed: {e}")
            return False
    
    async def search_jobs(self, keywords: str) -> bool:
        """
        Perform job search using the search bar.
        
        Args:
            keywords: Search keywords
        """
        try:
            logger.info(f"Searching for jobs: {keywords}")
            
            # Find search bar with multiple selectors
            search_selectors = [
                'input[data-testid="typeahead-input"]',
                'input[componentkey*="SearchTyah"]',
                'input[placeholder="I\'m looking for…"]',
                'input[placeholder*="Search"]',
                'input[aria-label*="Search"]',
                'input[data-test-id*="search"]',
                '.search-global-typeahead__input',
                '#global-nav-search input'
            ]
            
            search_element = await self.element_finder.find_element_multi_selector(
                search_selectors, 
                timeout=10000
            )
            
            if not search_element:
                logger.error("Could not find search bar")
                return False
            
            # Fill search bar
            success = await self.element_finder.safe_fill(
                search_selectors[0],  # Use first selector for fill
                keywords,
                clear_first=True
            )
            
            if not success:
                logger.error("Failed to fill search bar")
                return False
            
            # Submit search
            await self.page.keyboard.press("Enter")
            await asyncio.sleep(2)
            
            # Wait for search results
            await self.wait_for_navigation_complete()
            
            logger.info(f"Search completed for: {keywords}")
            return True
            
        except Exception as e:
            logger.error(f"Job search failed: {e}")
            return False
    
    async def navigate_to_jobs_section(self) -> bool:
        """
        Navigate to the Jobs section from search results.
        """
        try:
            current_url = self.page.url
            
            # Check if already on jobs page
            if '/jobs/' in current_url:
                logger.debug("Already in jobs section")
                return True
            
            # Find and click Jobs filter/button
            jobs_selectors = [
                'nav[aria-label="Primary"] a:has-text("Jobs")',
                'a[data-test-global-nav-link="jobs"]',
                'header a:has-text("Jobs")',
                'button:text("Jobs"):not(.artdeco-card button)',
                '.search-navigation button:has-text("Jobs")',
                'li[data-test-id="nav-jobs"] a'
            ]
            
            clicked = await self.element_finder.safe_click(
                jobs_selectors[0],
                alternative_selectors=jobs_selectors[1:]
            )
            
            if not clicked:
                logger.warning("Could not find Jobs button, trying direct navigation")
                
                # Extract search keywords from current URL for direct navigation
                try:
                    parsed = urlparse(current_url)
                    query_params = parse_qs(parsed.query)
                    keywords = query_params.get('keywords', [''])[0]
                    
                    jobs_url = f"{self.base_url}/jobs/search/?keywords={keywords.replace(' ', '%20')}"
                    return await self.goto_with_retry(
                        jobs_url, 
                        expected_selectors=self.readiness_indicators.get('jobs')
                    )
                except Exception as e:
                    logger.error(f"Direct jobs navigation failed: {e}")
                    return False
            
            # Wait for navigation to jobs section
            await self.wait_for_navigation_complete()
            
            # Verify we're in jobs section
            final_url = self.page.url
            if '/jobs/' in final_url:
                logger.info("Successfully navigated to jobs section")
                return True
            else:
                logger.warning(f"Navigation to jobs section may have failed. Current URL: {final_url}")
                return False
            
        except Exception as e:
            logger.error(f"Failed to navigate to jobs section: {e}")
            return False
    
    async def recover_from_navigation_failure(self) -> bool:
        """
        Attempt to recover from navigation failures.
        
        Returns:
            True if recovery was successful
        """
        try:
            logger.info("Attempting navigation recovery")
            
            # Strategy 1: Go back to last known good page
            if self.state.previous_url:
                logger.info(f"Trying to return to previous page: {self.state.previous_url}")
                success = await self.goto_with_retry(self.state.previous_url)
                if success:
                    return True
            
            # Strategy 2: Go to LinkedIn home page
            logger.info("Trying to return to LinkedIn home")
            success = await self.goto_with_retry(
                f"{self.base_url}/feed",
                expected_selectors=self.readiness_indicators.get('home')
            )
            if success:
                return True
            
            # Strategy 3: Full page reload
            logger.info("Attempting page reload")
            await self.page.reload(wait_until="domcontentloaded")
            await asyncio.sleep(3)
            
            # Check if recovery was successful
            current_url = self.page.url
            if self.base_url in current_url and '/login' not in current_url:
                logger.info("Recovery successful")
                return True
            
            logger.error("All recovery strategies failed")
            return False
            
        except Exception as e:
            logger.error(f"Recovery attempt failed: {e}")
            return False
    
    async def get_page_info(self) -> Dict[str, Any]:
        """
        Get current page information for debugging.
        
        Returns:
            Dictionary with page information
        """
        try:
            return {
                'url': self.page.url,
                'title': await self.page.title(),
                'ready_state': await self.page.evaluate('document.readyState'),
                'has_global_nav': bool(await self.page.query_selector('.global-nav')),
                'is_jobs_page': '/jobs/' in self.page.url,
                'navigation_state': {
                    'current_url': self.state.current_url,
                    'previous_url': self.state.previous_url,
                    'last_operation': self.state.last_successful_operation
                }
            }
        except Exception as e:
            logger.error(f"Failed to get page info: {e}")
            return {'error': str(e)}