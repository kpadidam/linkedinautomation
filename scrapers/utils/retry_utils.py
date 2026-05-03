"""Retry utilities with exponential backoff for robust scraping operations."""

import asyncio
import logging
import random
from functools import wraps
from typing import Any, Callable, Optional, Type, Union, Tuple
from playwright.async_api import TimeoutError as PlaywrightTimeoutError, Error as PlaywrightError

logger = logging.getLogger(__name__)


class RetryConfig:
    """Configuration for retry behavior."""
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        backoff_factor: float = 1.0
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.backoff_factor = backoff_factor


def calculate_delay(attempt: int, config: RetryConfig) -> float:
    """Calculate delay for a given attempt number."""
    delay = config.base_delay * (config.exponential_base ** (attempt - 1)) * config.backoff_factor
    delay = min(delay, config.max_delay)
    
    if config.jitter:
        # Add random jitter of ±25%
        jitter_range = delay * 0.25
        delay += random.uniform(-jitter_range, jitter_range)
    
    return max(0.1, delay)  # Minimum 0.1 seconds


def retry_async(
    config: Optional[RetryConfig] = None,
    exceptions: Tuple[Type[Exception], ...] = (PlaywrightTimeoutError, PlaywrightError, ConnectionError, asyncio.TimeoutError),
    log_attempts: bool = True
):
    """
    Decorator for async functions to add retry logic with exponential backoff.
    
    Args:
        config: Retry configuration. Defaults to basic config.
        exceptions: Tuple of exception types to retry on.
        log_attempts: Whether to log retry attempts.
    """
    if config is None:
        config = RetryConfig()
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(1, config.max_attempts + 1):
                try:
                    if log_attempts and attempt > 1:
                        logger.info(f"Retry attempt {attempt}/{config.max_attempts} for {func.__name__}")
                    
                    result = await func(*args, **kwargs)
                    
                    if attempt > 1:
                        logger.info(f"Success on attempt {attempt} for {func.__name__}")
                    
                    return result
                    
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == config.max_attempts:
                        logger.error(f"All {config.max_attempts} attempts failed for {func.__name__}: {e}")
                        raise e
                    
                    delay = calculate_delay(attempt, config)
                    if log_attempts:
                        logger.warning(f"Attempt {attempt} failed for {func.__name__}: {e}. Retrying in {delay:.2f}s")
                    
                    await asyncio.sleep(delay)
                
                except Exception as e:
                    # Don't retry on unexpected exceptions
                    logger.error(f"Non-retryable exception in {func.__name__}: {e}")
                    raise e
            
            # This should never be reached, but just in case
            if last_exception:
                raise last_exception
            
        return wrapper
    return decorator


class RetryableOperation:
    """Context manager for retryable operations with custom logic."""
    
    def __init__(
        self,
        operation_name: str,
        config: Optional[RetryConfig] = None,
        exceptions: Tuple[Type[Exception], ...] = (PlaywrightTimeoutError, PlaywrightError),
        cleanup_func: Optional[Callable] = None
    ):
        self.operation_name = operation_name
        self.config = config or RetryConfig()
        self.exceptions = exceptions
        self.cleanup_func = cleanup_func
        self.attempt = 0
        self.last_exception = None
    
    async def __aenter__(self):
        self.attempt += 1
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type and issubclass(exc_type, self.exceptions):
            self.last_exception = exc_val
            
            if self.attempt < self.config.max_attempts:
                delay = calculate_delay(self.attempt, self.config)
                logger.warning(f"Attempt {self.attempt} failed for {self.operation_name}: {exc_val}. Retrying in {delay:.2f}s")
                
                if self.cleanup_func:
                    try:
                        await self.cleanup_func()
                    except Exception as cleanup_error:
                        logger.warning(f"Cleanup failed for {self.operation_name}: {cleanup_error}")
                
                await asyncio.sleep(delay)
                return True  # Suppress exception to continue retrying
            else:
                logger.error(f"All {self.config.max_attempts} attempts failed for {self.operation_name}")
                return False  # Let exception propagate
        
        return False


# Predefined retry configurations for common scenarios
QUICK_RETRY = RetryConfig(max_attempts=2, base_delay=0.5, max_delay=2.0)
STANDARD_RETRY = RetryConfig(max_attempts=3, base_delay=1.0, max_delay=10.0)
PATIENT_RETRY = RetryConfig(max_attempts=5, base_delay=2.0, max_delay=30.0)
NAVIGATION_RETRY = RetryConfig(max_attempts=4, base_delay=1.5, max_delay=15.0)
ELEMENT_WAIT_RETRY = RetryConfig(max_attempts=3, base_delay=0.8, max_delay=8.0)


async def retry_until_success(
    func: Callable,
    config: Optional[RetryConfig] = None,
    exceptions: Tuple[Type[Exception], ...] = (PlaywrightTimeoutError, PlaywrightError),
    success_check: Optional[Callable[[Any], bool]] = None,
    operation_name: str = "operation"
) -> Any:
    """
    Retry a function until it succeeds or max attempts reached.
    
    Args:
        func: Async function to retry
        config: Retry configuration
        exceptions: Exception types to retry on
        success_check: Function to validate if result is successful
        operation_name: Name for logging
    """
    if config is None:
        config = STANDARD_RETRY
    
    last_exception = None
    
    for attempt in range(1, config.max_attempts + 1):
        try:
            result = await func()
            
            # Check if result meets success criteria
            if success_check and not success_check(result):
                raise ValueError(f"Success check failed for {operation_name}")
            
            if attempt > 1:
                logger.info(f"Success on attempt {attempt} for {operation_name}")
            
            return result
            
        except exceptions as e:
            last_exception = e
            
            if attempt == config.max_attempts:
                logger.error(f"All {config.max_attempts} attempts failed for {operation_name}: {e}")
                raise e
            
            delay = calculate_delay(attempt, config)
            logger.warning(f"Attempt {attempt} failed for {operation_name}: {e}. Retrying in {delay:.2f}s")
            await asyncio.sleep(delay)
        
        except Exception as e:
            logger.error(f"Non-retryable exception in {operation_name}: {e}")
            raise e
    
    if last_exception:
        raise last_exception


# Specific retry decorators for common LinkedIn scraping operations
def retry_element_operation(config: Optional[RetryConfig] = None):
    """Retry decorator specifically for element operations."""
    return retry_async(
        config=config or ELEMENT_WAIT_RETRY,
        exceptions=(PlaywrightTimeoutError, PlaywrightError, AttributeError),
        log_attempts=True
    )


def retry_navigation(config: Optional[RetryConfig] = None):
    """Retry decorator specifically for navigation operations."""
    return retry_async(
        config=config or NAVIGATION_RETRY,
        exceptions=(PlaywrightTimeoutError, PlaywrightError, ConnectionError),
        log_attempts=True
    )


def retry_network_operation(config: Optional[RetryConfig] = None):
    """Retry decorator for network-related operations."""
    return retry_async(
        config=config or PATIENT_RETRY,
        exceptions=(PlaywrightTimeoutError, ConnectionError, OSError),
        log_attempts=True
    )