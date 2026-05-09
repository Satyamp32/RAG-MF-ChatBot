"""
Data models for Phase 1.4 Chunking Strategy.
"""

from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class Chunk(BaseModel):
    """Represents a chunk of content."""
    
    chunk_id: str
    scheme_id: str
    scheme_name: Optional[str]
    doc_type: str = "Product_Page"
    source_url: str
    section: str
    section_source: str = "html_section"
    last_updated: datetime
    content_hash: str
    stable_content_hash: str
    text: str
    token_count: int
    chunk_index: int
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ChunkingStats(BaseModel):
    """Statistics for chunking operations."""
    
    total_chunks: int
    total_tokens: int
    average_chunk_size: float
    chunk_size_distribution: Dict[str, int]
    sections_processed: int
    chunks_per_section: Dict[str, int]
    soft_cap: int
    hard_cap: int
    overlap: int
    processing_time: Optional[float] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ChunkingConfig(BaseModel):
    """Configuration for chunking strategy."""
    
    soft_cap: int = 250
    hard_cap: int = 400
    overlap: int = 30
    preserve_financial_context: bool = True
    semantic_chunking: bool = True
    numeric_fact_protection: bool = True
    section_boundary_preservation: bool = True
