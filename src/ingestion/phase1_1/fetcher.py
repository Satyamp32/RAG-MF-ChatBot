"""
Phase 1.1 - URL Ingestion & Scraping

Implements URL fetching with ETag support, robots.txt compliance, 
comprehensive error handling, and content quality validation.
"""

import asyncio
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx
import structlog
from playwright.async_api import async_playwright

from src.utils.config import config_manager
from src.utils.logger import get_logger
from src.utils.retry import NetworkError, RateLimitError, TemporaryError, http_retry

logger = get_logger(__name__)


class FetchResult:
    """Result of a URL fetch operation."""
    
    def __init__(
        self,
        url: str,
        content: str,
        status_code: int,
        etag: Optional[str] = None,
        content_hash: Optional[str] = None,
        fetched_at: Optional[datetime] = None,
        fetcher_kind: str = "httpx"
    ):
        self.url = url
        self.content = content
        self.status_code = status_code
        self.etag = etag
        self.content_hash = content_hash or self._compute_hash(content)
        self.fetched_at = fetched_at or datetime.now(timezone.utc)
        self.fetcher_kind = fetcher_kind
        self.is_success = 200 <= status_code < 300
        self.is_not_modified = status_code == 304
    
    def _compute_hash(self, content: str) -> str:
        """Compute SHA256 hash of content."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "url": self.url,
            "status_code": self.status_code,
            "etag": self.etag,
            "content_hash": self.content_hash,
            "fetched_at": self.fetched_at.isoformat(),
            "fetcher_kind": self.fetcher_kind,
            "is_success": self.is_success,
            "is_not_modified": self.is_not_modified
        }


class RobotsChecker:
    """Handles robots.txt compliance checking."""
    
    def __init__(self):
        self.cache = {}
        self.cache_ttl = 3600  # 1 hour
    
    def is_allowed(self, url: str, user_agent: str = "*") -> bool:
        """
        Check if URL is allowed by robots.txt.
        
        Args:
            url: URL to check
            user_agent: User agent string
            
        Returns:
            True if allowed, False if disallowed
        """
        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        
        # Check cache first
        if base_url in self.cache:
            cached_time, robots = self.cache[base_url]
            if time.time() - cached_time < self.cache_ttl:
                allowed = robots.can_fetch(user_agent, url)
                logger.info(
                    "Robots.txt check from cache",
                    url=url,
                    allowed=allowed
                )
                return allowed
        
        # Fetch robots.txt
        try:
            robots_url = f"{base_url}/robots.txt"
            rp = RobotFileParser()
            rp.set_url(robots_url)
            rp.read()
            
            # Cache result
            self.cache[base_url] = (time.time(), rp)
            
            allowed = rp.can_fetch(user_agent, url)
            logger.info(
                "Robots.txt check completed",
                url=url,
                allowed=allowed
            )
            
            return allowed
            
        except Exception as e:
            logger.warning(
                "Failed to check robots.txt, allowing by default",
                url=url,
                error=str(e)
            )
            return True


class Fetcher:
    """URL fetcher with ETag support and fallback mechanisms."""
    
    def __init__(self, timeout: int = 30, max_retries: int = 3):
        self.timeout = timeout
        self.max_retries = max_retries
        self.robots_checker = RobotsChecker()
        self.session = httpx.Client(
            timeout=httpx.Timeout(timeout),
            headers={
                "User-Agent": "MutualFund-FAQ-Assistant/1.0"
            }
        )
    
    async def _fetch_with_httpx(
        self,
        url: str,
        etag: Optional[str] = None
    ) -> FetchResult:
        """
        Fetch URL using httpx with ETag support.
        
        Args:
            url: URL to fetch
            etag: Previous ETag for conditional request
            
        Returns:
            FetchResult with content and metadata
        """
        headers = {}
        if etag:
            headers["If-None-Match"] = etag
        
        try:
            response = self.session.get(url, headers=headers, follow_redirects=False)
            
            # Handle redirects manually to enforce governance
            if response.status_code in (301, 302, 303, 307, 308):
                raise NetworkError(
                    f"Redirect detected for whitelisted URL: {url} -> {response.headers.get('location')}"
                )
            
            # Handle rate limiting
            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After", "60")
                raise RateLimitError(
                    f"Rate limited. Retry after {retry_after} seconds"
                )
            
            # Handle client errors
            if 400 <= response.status_code < 500:
                raise NetworkError(
                    f"Client error {response.status_code} for URL: {url}"
                )
            
            # Handle server errors
            if 500 <= response.status_code < 600:
                raise TemporaryError(
                    f"Server error {response.status_code} for URL: {url}"
                )
            
            return FetchResult(
                url=url,
                content=response.text,
                status_code=response.status_code,
                etag=response.headers.get("ETag"),
                fetcher_kind="httpx"
            )
            
        except httpx.TimeoutException:
            raise TemporaryError(f"Timeout fetching URL: {url}")
        except httpx.NetworkError as e:
            raise NetworkError(f"Network error fetching URL: {url} - {str(e)}")
    
    async def _fetch_with_playwright(self, url: str) -> FetchResult:
        """
        Fetch URL using Playwright for JavaScript-heavy content.
        
        Args:
            url: URL to fetch
            
        Returns:
            FetchResult with rendered content
        """
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                # Set viewport and user agent
                await page.set_viewport_size({"width": 1920, "height": 1080})
                await page.set_extra_http_headers({
                    "User-Agent": "MutualFund-FAQ-Assistant/1.0"
                })
                
                # Navigate to URL
                response = await page.goto(url, wait_until="networkidle")
                
                if not response:
                    raise TemporaryError("No response from Playwright")
                
                # Wait for content to load
                await page.wait_for_timeout(3000)
                
                # Expand any collapsed content
                await page.evaluate("""
                    // Expand accordions and tabs
                    document.querySelectorAll('[aria-expanded="false"]').forEach(el => {
                        el.click();
                    });
                """)
                
                # Wait a bit more for dynamic content
                await page.wait_for_timeout(2000)
                
                # Get content
                content = await page.content()
                status = response.status
                
                await browser.close()
                
                return FetchResult(
                    url=url,
                    content=content,
                    status_code=status,
                    fetcher_kind="playwright"
                )
                
        except Exception as e:
            logger.error(
                "Playwright fetch failed",
                url=url,
                error=str(e)
            )
            raise TemporaryError(f"Playwright fetch failed: {str(e)}")
    
    def _validate_content_quality(self, result: FetchResult) -> bool:
        """
        Validate if fetched content meets quality thresholds.
        
        Args:
            result: FetchResult to validate
            
        Returns:
            True if content quality is acceptable
        """
        content_length = len(result.content)
        
        # Minimum content length check
        if content_length < 1000:
            logger.warning(
                "Content too short, may be incomplete",
                url=result.url,
                length=content_length
            )
            return False
        
        # Check for must-have keywords (basic validation)
        must_have_keywords = ["mutual fund", "HDFC", "fund"]
        content_lower = result.content.lower()
        
        keyword_count = sum(1 for keyword in must_have_keywords 
                          if keyword.lower() in content_lower)
        
        if keyword_count < 2:
            logger.warning(
                "Content missing must-have keywords",
                url=result.url,
                keyword_count=keyword_count
            )
            return False
        
        return True
    
    @http_retry(max_attempts=3, operation_name="URL fetch")
    async def fetch_url(
        self,
        url: str,
        previous_etag: Optional[str] = None,
        force_refresh: bool = False
    ) -> FetchResult:
        """
        Fetch a single URL with comprehensive error handling.
        
        Args:
            url: URL to fetch
            previous_etag: Previous ETag for conditional request
            force_refresh: Force full refresh regardless of ETag
            
        Returns:
            FetchResult with content and metadata
        """
        logger.info(
            "Starting URL fetch",
            url=url,
            has_etag=previous_etag is not None,
            force_refresh=force_refresh
        )
        
        # Check robots.txt compliance
        if not self.robots_checker.is_allowed(url):
            raise NetworkError(f"URL disallowed by robots.txt: {url}")
        
        # Try httpx first
        try:
            result = await self._fetch_with_httpx(url, previous_etag)
            
            # If content quality is poor, try Playwright
            if result.is_success and not self._validate_content_quality(result):
                logger.info(
                    "Content quality poor, falling back to Playwright",
                    url=url
                )
                result = await self._fetch_with_playwright(url)
            
            logger.info(
                "URL fetch completed",
                url=url,
                status_code=result.status_code,
                content_length=len(result.content),
                fetcher_kind=result.fetcher_kind
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "All fetch methods failed",
                url=url,
                error=str(e),
                error_type=type(e).__name__
            )
            raise
    
    async def fetch_all(
        self,
        urls: List[str],
        force_refresh: bool = False
    ) -> List[FetchResult]:
        """
        Fetch multiple URLs concurrently.
        
        Args:
            urls: List of URLs to fetch
            force_refresh: Force full refresh regardless of ETags
            
        Returns:
            List of FetchResults
        """
        logger.info(
            "Starting batch fetch",
            url_count=len(urls),
            force_refresh=force_refresh
        )
        
        # Load previous ETags
        previous_etags = self._load_previous_etags()
        
        # Create fetch tasks
        tasks = []
        for url in urls:
            etag = None if force_refresh else previous_etags.get(url)
            task = self.fetch_url(url, etag, force_refresh)
            tasks.append(task)
        
        # Execute concurrently
        results = []
        for i, task in enumerate(tasks):
            try:
                result = await task
                results.append(result)
            except Exception as e:
                logger.error(
                    "Failed to fetch URL",
                    url=urls[i],
                    error=str(e)
                )
                # Create a failed result
                results.append(FetchResult(
                    url=urls[i],
                    content="",
                    status_code=500,
                    fetcher_kind="failed"
                ))
        
        # Save ETags for next run
        self._save_etags(results)
        
        success_count = sum(1 for r in results if r.is_success)
        logger.info(
            "Batch fetch completed",
            total=len(results),
            success=success_count,
            failed=len(results) - success_count
        )
        
        return results
    
    def _load_previous_etags(self) -> Dict[str, str]:
        """Load previous ETags from metadata."""
        etags = {}
        try:
            metadata_file = Path("data/raw/etags.json")
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    etags = json.load(f)
        except Exception as e:
            logger.warning(
                "Failed to load previous ETags",
                error=str(e)
            )
        return etags
    
    def _save_etags(self, results: List[FetchResult]) -> None:
        """Save ETags from successful fetches."""
        etags = {}
        for result in results:
            if result.is_success and result.etag:
                etags[result.url] = result.etag
        
        try:
            metadata_file = Path("data/raw")
            metadata_file.mkdir(parents=True, exist_ok=True)
            
            with open(metadata_file / "etags.json", 'w') as f:
                json.dump(etags, f, indent=2)
                
        except Exception as e:
            logger.error(
                "Failed to save ETags",
                error=str(e)
            )
    
    def save_results(self, results: List[FetchResult]) -> None:
        """
        Save fetch results to file system.
        
        Args:
            results: List of FetchResults to save
        """
        base_dir = Path("data/raw")
        base_dir.mkdir(parents=True, exist_ok=True)
        
        for result in results:
            if not result.is_success:
                continue
            
            # Extract scheme ID from URL
            scheme = config_manager.get_scheme_by_url(result.url)
            if not scheme:
                logger.warning(
                    "Unknown scheme URL",
                    url=result.url
                )
                continue
            
            scheme_dir = base_dir / scheme['id']
            scheme_dir.mkdir(exist_ok=True)
            
            # Save HTML content
            timestamp = result.fetched_at.strftime("%Y%m%d_%H%M%S")
            html_file = scheme_dir / f"{timestamp}.html"
            
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(result.content)
            
            # Save metadata
            meta_file = scheme_dir / f"{timestamp}.json"
            with open(meta_file, 'w', encoding='utf-8') as f:
                json.dump(result.to_dict(), f, indent=2)
            
            logger.info(
                "Saved fetch result",
                scheme=scheme['id'],
                html_file=str(html_file),
                meta_file=str(meta_file)
            )
