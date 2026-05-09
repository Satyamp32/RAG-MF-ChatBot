"""
Data models for Phase 1.2 HTML Cleaning & Normalization.
"""

from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class ExtractedSection(BaseModel):
    """Represents a cleaned section from HTML."""
    
    name: str
    text: str
    source: str = "html_section"
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class CleanedDocument(BaseModel):
    """Represents a cleaned document with sections."""
    
    scheme_id: str
    source_url: str
    fetched_at: datetime
    sections: List[ExtractedSection]
    extraction_health: str = "ok"
    cleaning_stats: Dict[str, int] = {}
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class CleaningStats(BaseModel):
    """Statistics for cleaning operations."""
    
    original_length: int
    cleaned_length: int
    boilerplate_removed: int
    sections_found: int
    volatile_fields_removed: int
    processing_time: Optional[float] = None


class SectionCleaningRule(BaseModel):
    """Rule for section-specific cleaning."""
    
    section_name: str
    keep_patterns: List[str]
    remove_patterns: List[str]
    transformations: Dict[str, str]


class CleaningConfig(BaseModel):
    """Configuration for content cleaning."""
    
    boilerplate_phrases: List[str]
    volatile_field_patterns: List[str]
    currency_normalizations: Dict[str, str]
    percentage_normalizations: Dict[str, str]
    special_char_normalizations: Dict[str, str]
    section_rules: Dict[str, SectionCleaningRule]
