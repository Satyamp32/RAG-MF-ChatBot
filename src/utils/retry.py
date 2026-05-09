"""
Retry utilities with exponential backoff for resilient operations.
"""

import time
import random
from functools import wraps
from typing import Callable, Any, Optional, Type, Union

import structlog
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    after_log
)

logger = structlog.get_logger(__name__)


def with_retry(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retry_exceptions: Union[Type[Exception], tuple] = Exception,
    before_sleep_message: str = "Retrying after error",
    operation_name: str = "operation"
):
    """
    Decorator for retrying functions with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts
        initial_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        exponential_base: Base for exponential backoff
        jitter: Whether to add jitter to delay
        retry_exceptions: Exception types to retry on
        before_sleep_message: Message to log before sleep
        operation_name: Name of the operation for logging
    """
    def decorator(func: Callable) -> Callable:
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(
                multiplier=initial_delay,
                max=max_delay,
                exp_base=exponential_base,
                jitter=random.uniform(0.8, 1.2) if jitter else 1.0
            ),
            retry=retry_if_exception_type(retry_exceptions),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            after=after_log(logger, logging.INFO)
        )
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            logger.info(
                f"Starting {operation_name}",
                operation=operation_name,
                max_attempts=max_attempts
            )
            try:
                result = func(*args, **kwargs)
                logger.info(
                    f"Completed {operation_name} successfully",
                    operation=operation_name
                )
                return result
            except Exception as e:
                logger.error(
                    f"Failed {operation_name} after all retries",
                    operation=operation_name,
                    error=str(e),
                    error_type=type(e).__name__
                )
                raise
        
        return wrapper
    return decorator


class RetryableError(Exception):
    """Base class for retryable errors."""
    pass


class NetworkError(RetryableError):
    """Network-related errors that should be retried."""
    pass


class TemporaryError(RetryableError):
    """Temporary errors that might resolve on retry."""
    pass


class RateLimitError(RetryableError):
    """Rate limiting errors that should be retried with backoff."""
    pass


def http_retry(max_attempts: int = 3, operation_name: str = "HTTP request"):
    """Specific retry decorator for HTTP operations."""
    return with_retry(
        max_attempts=max_attempts,
        initial_delay=1.0,
        max_delay=30.0,
        retry_exceptions=(NetworkError, RateLimitError, TemporaryError),
        operation_name=operation_name
    )
