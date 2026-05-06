"""Safe element handling utilities that prevent execution context destruction errors."""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Union, Callable
from playwright.async_api import Page, ElementHandle, Locator, TimeoutError as PlaywrightTimeoutError

from .retry_utils import retry_element_operation, ELEMENT_WAIT_RETRY, retry_until_success

logger = logging.getLogger(__name__)


class SafeElementFinder:
    """Safe element operations that handle context destruction and timeouts."""
    
    def __init__(self, page: Page):
        self.page = page
        
    @retry_element_operation()
    async def wait_for_element(
        self, 
        selector: str, 
        timeout: int = 10000, 
        state: str = "visible"
    ) -> Optional[ElementHandle]:
        """
        Safely wait for an element to appear with retry logic.
        
        Args:
            selector: CSS selector or text selector
            timeout: Maximum wait time in milliseconds
            state: Element state to wait for ('visible', 'attached', 'hidden')
        """
        try:
            element = await self.page.wait_for_selector(
                selector, 
                timeout=timeout, 
                state=state
            )
            return element
        except PlaywrightTimeoutError:
            logger.debug(f"Element not found within {timeout}ms: {selector}")
            return None
            
    @retry_element_operation()
    async def find_element_multi_selector(
        self, 
        selectors: List[str], 
        timeout: int = 8000
    ) -> Optional[ElementHandle]:
        """
        Try multiple selectors until one succeeds.
        
        Args:
            selectors: List of CSS selectors to try
            timeout: Timeout for each selector attempt
        """
        for i, selector in enumerate(selectors):
            try:
                element = await self.page.wait_for_selector(
                    selector, 
                    timeout=timeout // len(selectors),  # Distribute timeout across selectors
                    state="visible"
                )
                if element:
                    logger.debug(f"Found element using selector {i+1}/{len(selectors)}: {selector}")
                    return element
            except PlaywrightTimeoutError:
                logger.debug(f"Selector {i+1}/{len(selectors)} failed: {selector}")
                continue
        
        logger.warning(f"All {len(selectors)} selectors failed")
        return None
    
    async def safe_click(
        self, 
        selector: str, 
        timeout: int = 10000,
        force: bool = False,
        alternative_selectors: Optional[List[str]] = None
    ) -> bool:
        """
        Safely click an element with multiple strategies and retry logic.
        
        Args:
            selector: Primary CSS selector
            timeout: Maximum wait time
            force: Whether to force click even if element not visible
            alternative_selectors: Fallback selectors to try
        """
        selectors_to_try = [selector]
        if alternative_selectors:
            selectors_to_try.extend(alternative_selectors)
        
        for attempt_selector in selectors_to_try:
            try:
                # Strategy 1: Wait and click normally
                element = await self.wait_for_element(attempt_selector, timeout=timeout)
                if element:
                    try:
                        await element.scroll_into_view_if_needed()
                        await asyncio.sleep(0.2)  # Brief pause for stability
                        await element.click(force=force)
                        logger.debug(f"Successfully clicked: {attempt_selector}")
                        return True
                    except Exception as click_error:
                        logger.debug(f"Normal click failed for {attempt_selector}: {click_error}")
                        
                        # Strategy 2: Try JavaScript click
                        try:
                            await self.page.evaluate('(element) => element.click()', element)
                            logger.debug(f"JavaScript click succeeded: {attempt_selector}")
                            return True
                        except Exception as js_error:
                            logger.debug(f"JavaScript click failed: {js_error}")
                            
                        # Strategy 3: Try using locator
                        try:
                            locator = self.page.locator(attempt_selector).first
                            await locator.click(force=force, timeout=timeout)
                            logger.debug(f"Locator click succeeded: {attempt_selector}")
                            return True
                        except Exception as locator_error:
                            logger.debug(f"Locator click failed: {locator_error}")
                            
            except Exception as e:
                logger.debug(f"Click attempt failed for {attempt_selector}: {e}")
                continue
        
        logger.warning(f"All click strategies failed for selectors: {selectors_to_try}")
        return False
    
    async def safe_fill(
        self, 
        selector: str, 
        text: str, 
        timeout: int = 10000,
        clear_first: bool = True
    ) -> bool:
        """
        Safely fill an input field with retry logic.
        
        Args:
            selector: CSS selector for input field
            text: Text to fill
            timeout: Maximum wait time
            clear_first: Whether to clear field before filling
        """
        try:
            element = await self.wait_for_element(selector, timeout=timeout)
            if not element:
                return False
            
            await element.scroll_into_view_if_needed()
            await asyncio.sleep(0.1)
            
            if clear_first:
                await element.fill("")  # Clear existing content
                await asyncio.sleep(0.1)
            
            # Type with human-like delay
            await element.type(text, delay=50)  # 50ms between keystrokes
            
            # Verify the text was entered correctly
            current_value = await element.input_value()
            if current_value != text:
                logger.warning(f"Text verification failed. Expected: '{text}', Got: '{current_value}'")
                # Try fill as fallback
                await element.fill(text)
            
            logger.debug(f"Successfully filled field: {selector}")
            return True
            
        except Exception as e:
            logger.warning(f"Failed to fill field {selector}: {e}")
            return False
    
    async def safe_get_text(
        self, 
        selector: str, 
        timeout: int = 5000,
        attribute: Optional[str] = None
    ) -> Optional[str]:
        """
        Safely get text from an element without causing context destruction.
        
        Args:
            selector: CSS selector
            timeout: Maximum wait time
            attribute: Specific attribute to get (e.g., 'href', 'title')
        """
        try:
            element = await self.wait_for_element(selector, timeout=timeout)
            if not element:
                return None
            
            if attribute:
                # Get specific attribute
                value = await element.get_attribute(attribute)
            else:
                # Get text content
                value = await element.inner_text()
            
            return value.strip() if value else None
            
        except Exception as e:
            logger.debug(f"Failed to get text from {selector}: {e}")
            return None
    
    async def safe_get_multiple_texts(
        self, 
        selectors: List[str], 
        timeout: int = 5000
    ) -> Dict[str, Optional[str]]:
        """
        Get text from multiple selectors safely.
        
        Args:
            selectors: List of CSS selectors
            timeout: Maximum wait time per selector
        """
        results = {}
        
        for selector in selectors:
            try:
                text = await self.safe_get_text(selector, timeout=timeout // len(selectors))
                results[selector] = text
            except Exception as e:
                logger.debug(f"Failed to get text from {selector}: {e}")
                results[selector] = None
        
        return results
    
    async def wait_for_any_element(
        self, 
        selectors: List[str], 
        timeout: int = 10000
    ) -> Optional[ElementHandle]:
        """
        Wait for any of the provided selectors to appear.
        
        Args:
            selectors: List of selectors to wait for
            timeout: Maximum total wait time
        """
        start_time = asyncio.get_event_loop().time()
        
        while (asyncio.get_event_loop().time() - start_time) < (timeout / 1000):
            for selector in selectors:
                try:
                    element = await self.page.query_selector(selector)
                    if element:
                        # Verify element is actually visible/usable
                        is_visible = await element.is_visible()
                        if is_visible:
                            logger.debug(f"Found element: {selector}")
                            return element
                except Exception:
                    continue
            
            await asyncio.sleep(0.5)  # Check every 500ms
        
        logger.debug(f"No elements found from selectors: {selectors}")
        return None
    
    async def scroll_and_wait(
        self, 
        selector: str, 
        timeout: int = 10000,
        scroll_delay: float = 1.0
    ) -> Optional[ElementHandle]:
        """
        Scroll to trigger lazy loading and wait for element.
        
        Args:
            selector: CSS selector to wait for
            timeout: Maximum wait time
            scroll_delay: Delay between scrolls
        """
        start_time = asyncio.get_event_loop().time()
        scroll_position = 0
        scroll_increment = 300
        
        while (asyncio.get_event_loop().time() - start_time) < (timeout / 1000):
            # Check if element exists
            element = await self.page.query_selector(selector)
            if element and await element.is_visible():
                return element
            
            # Scroll to trigger loading
            await self.page.mouse.wheel(0, scroll_increment)
            scroll_position += scroll_increment
            await asyncio.sleep(scroll_delay)
            
            # Reset scroll position if we've gone too far
            if scroll_position > 2000:
                await self.page.evaluate("window.scrollTo(0, 0)")
                scroll_position = 0
                await asyncio.sleep(scroll_delay)
        
        return None
    
    async def verify_page_ready(self, expected_selectors: List[str]) -> bool:
        """
        Verify page is ready by checking for expected elements.
        
        Args:
            expected_selectors: List of selectors that should be present when page is ready
        """
        for selector in expected_selectors:
            element = await self.page.query_selector(selector)
            if not element:
                logger.debug(f"Page not ready - missing: {selector}")
                return False
        
        logger.debug("Page appears ready")
        return True
    
    async def dismiss_overlays(self) -> bool:
        """
        Dismiss common LinkedIn overlays and modals.
        
        Returns:
            True if any overlays were dismissed
        """
        overlay_selectors = [
            # LinkedIn premium popup
            '[data-test-modal-id="premium-upsell-modal"] button[aria-label="Dismiss"]',
            'button[aria-label="Dismiss premium upsell"]',
            
            # Cookie banners
            'button:has-text("Accept")',
            'button:has-text("Allow")',
            '[data-test-id="cookie-accept"]',
            
            # General modal close buttons
            'button[aria-label="Close"]',
            'button[aria-label="Dismiss"]',
            '.modal button[data-control-name="overlay.close_overlay"]',
            
            # LinkedIn specific overlays
            '.msg-overlay-bubble-header__controls button',
            'button[data-test-modal-close-btn]',
        ]
        
        dismissed_any = False
        
        for selector in overlay_selectors:
            try:
                element = await self.page.query_selector(selector)
                if element and await element.is_visible():
                    await element.click()
                    dismissed_any = True
                    logger.debug(f"Dismissed overlay: {selector}")
                    await asyncio.sleep(0.5)  # Wait for dismissal animation
            except Exception as e:
                logger.debug(f"Could not dismiss overlay {selector}: {e}")
                continue
        
        # Also try ESC key to close any modal
        try:
            await self.page.keyboard.press("Escape")
            await asyncio.sleep(0.3)
        except Exception:
            pass
        
        return dismissed_any