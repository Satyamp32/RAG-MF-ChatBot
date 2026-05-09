"""
Data models for Phase 1.5 Embedding Generation.
"""

from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class EmbeddingMetadata(BaseModel):
    """Metadata for embedding generation."""
    
    chunk_id: str
    scheme_id: str
    scheme_name: Optional[str]
    section: str
    text: str
    token_count: int
    content_hash: str
    stable_content_hash: str
    embedding_model: str
    embedding_dim: int
    embedding_generated_at: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class EmbeddedChunk(BaseModel):
    """Chunk with embedding data."""
    
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
    embedding: List[float]
    embedding_model: str
    embedding_dim: int
    embedding_normalized: bool
    embedding_generated_at: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class EmbeddingStats(BaseModel):
    """Statistics for embedding operations."""
    
    total_embeddings: int
    embedding_dimension: int
    mean_norm: float
    std_norm: float
    min_value: float
    max_value: float
    mean_value: float
    std_value: float
    model_name: str
    batch_size: int
    processing_time: Optional[float] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class EmbeddingConfig(BaseModel):
    """Configuration for embedding generation."""
    
    model_name: str = "BAAI/bge-small-en"
    embedding_dim: int = 384
    batch_size: int = 32
    normalize_embeddings: bool = True
    prepend_scheme_name: bool = True
    max_retries: int = 3
    retry_delay: float = 1.0
    retry_backoff: float = 2.0


class EmbeddingValidationResult(BaseModel):
    """Result of embedding validation."""
    
    is_valid: bool
    errors: List[str] = []
    warnings: List[str] = []
    statistics: Dict[str, float] = {}
    validation_time: Optional[float] = None
