"""
Custom exceptions for Phase 1.1 URL ingestion and scraping.
"""


class FetchingError(Exception):
    """Base exception for fetching errors."""
    pass


class NetworkError(FetchingError):
    """Network-related errors during fetching."""
    pass


class RateLimitError(FetchingError):
    """Rate limiting errors from target servers."""
    pass


class TemporaryError(FetchingError):
    """Temporary errors that might resolve on retry."""
    pass


class RobotsError(FetchingError):
    """Robots.txt compliance errors."""
    pass


class ContentQualityError(FetchingError):
    """Content quality validation errors."""
    pass


class ConfigurationError(FetchingError):
    """Configuration-related errors."""
    pass
