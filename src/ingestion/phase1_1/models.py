"""
Data models for Phase 1.1 URL ingestion and scraping.
"""

from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class FetchResult(BaseModel):
    """Result of a URL fetch operation."""
    
    url: str
    content: str
    status_code: int
    etag: Optional[str] = None
    content_hash: Optional[str] = None
    fetched_at: datetime
    fetcher_kind: str = "httpx"
    is_success: bool = False
    is_not_modified: bool = False
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class FetchMetadata(BaseModel):
    """Metadata for fetch operations."""
    
    url: str
    fetched_at: datetime
    http_status: int
    etag: Optional[str] = None
    content_hash_raw: str
    fetcher_kind: str
    is_success: bool
    is_not_modified: bool
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class RobotsCacheEntry(BaseModel):
    """Entry for robots.txt cache."""
    
    cached_time: float
    user_agent: str
    allowed_paths: List[str]
    disallowed_paths: List[str]


class FetchHealthReport(BaseModel):
    """Health report for fetch operations."""
    
    total_urls: int
    successful_fetches: int
    failed_fetches: List[str]
    total_content_size: int
    average_fetch_time: Optional[float] = None
    fetcher_kind_counts: Dict[str, int]
    health_status: str  # "ok", "partial", "failed"


class ContentQualityMetrics(BaseModel):
    """Metrics for content quality assessment."""
    
    content_length: int
    keyword_density: float
    has_required_keywords: bool
    keyword_matches: List[str]
    quality_score: float  # 0.0 to 1.0
    passes_threshold: bool
