"""
API Schemas

Pydantic models for request/response validation and serialization
for the Mutual Fund RAG ChatBot API.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, validator
from enum import Enum


class QueryType(str, Enum):
    """Query type enumeration."""
    NUMERICAL_HEAVY = "numerical_heavy"
    SECTION_SPECIFIC = "section_specific"
    SEMANTIC = "semantic"
    GENERAL = "general"


class GenerationMethod(str, Enum):
    """Generation method enumeration."""
    EXTRACTIVE = "extractive"
    GROQ = "groq"


class ResponseStatus(str, Enum):
    """Response status enumeration."""
    SUCCESS = "success"
    ERROR = "error"
    BLOCKED = "blocked"


# Request Schemas
class ChatRequest(BaseModel):
    """Chat request schema."""
    query: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="User query about mutual funds"
    )
    use_groq: Optional[str] = Field(
        default="auto",
        description="Use Groq LLM (auto, true, false)"
    )
    top_k: Optional[int] = Field(
        default=10,
        ge=1,
        le=50,
        description="Number of top chunks to retrieve"
    )
    scheme_filter: Optional[str] = Field(
        default=None,
        description="Filter by specific scheme ID"
    )
    section_filter: Optional[str] = Field(
        default=None,
        description="Filter by specific section"
    )
    include_metadata: Optional[bool] = Field(
        default=False,
        description="Include retrieval metadata in response"
    )
    
    @validator('query')
    def validate_query(cls, v):
        """Validate query content."""
        if not v.strip():
            raise ValueError("Query cannot be empty")
        return v.strip()
    
    @validator('use_groq')
    def validate_use_groq(cls, v):
        """Validate use_groq parameter."""
        if v not in ["auto", "true", "false"]:
            raise ValueError("use_groq must be one of: auto, true, false")
        return v


# Response Schemas
class ChunkInfo(BaseModel):
    """Retrieved chunk information."""
    chunk_id: str = Field(..., description="Chunk identifier")
    scheme_id: str = Field(..., description="Scheme identifier")
    section: str = Field(..., description="Section name")
    text: str = Field(..., description="Chunk text content")
    score: float = Field(..., description="Retrieval score")
    confidence: float = Field(..., description="Confidence score")
    source: str = Field(..., description="Retrieval source")
    rerank_score: Optional[float] = Field(default=None, description="Reranking score")
    rerank_rank: Optional[int] = Field(default=None, description="Reranking rank")


class RetrievalMetadata(BaseModel):
    """Retrieval metadata."""
    query: str = Field(..., description="Original query")
    query_type: QueryType = Field(..., description="Query type")
    chunks_used: int = Field(..., description="Number of chunks used")
    retrieval_time_ms: float = Field(..., description="Retrieval time in milliseconds")
    dense_results: int = Field(..., description="Number of dense results")
    sparse_results: int = Field(..., description="Number of sparse results")
    fused_results: int = Field(..., description="Number of fused results")
    final_results: int = Field(..., description="Number of final results")


class GenerationMetadata(BaseModel):
    """Generation metadata."""
    generation_method: GenerationMethod = Field(..., description="Generation method")
    confidence: float = Field(..., description="Response confidence")
    generation_time_ms: float = Field(..., description="Generation time in milliseconds")
    source_url: Optional[str] = Field(default=None, description="Source URL")
    last_updated: Optional[str] = Field(default=None, description="Last updated date")
    guardrails_applied: bool = Field(..., description="Whether guardrails were applied")
    guardrails_passed: bool = Field(..., description="Whether guardrails passed")


class ChatResponse(BaseModel):
    """Chat response schema."""
    status: ResponseStatus = Field(..., description="Response status")
    answer: Optional[str] = Field(default=None, description="Generated answer")
    source: Optional[str] = Field(default=None, description="Source attribution")
    last_updated: Optional[str] = Field(default=None, description="Last updated date")
    confidence: Optional[float] = Field(default=None, description="Response confidence")
    chunks: Optional[List[ChunkInfo]] = Field(default=None, description="Retrieved chunks")
    retrieval_metadata: Optional[RetrievalMetadata] = Field(default=None, description="Retrieval metadata")
    generation_metadata: Optional[GenerationMetadata] = Field(default=None, description="Generation metadata")
    error: Optional[str] = Field(default=None, description="Error message if status is error")
    blocked_reason: Optional[str] = Field(default=None, description="Reason if response was blocked")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


# Health and Metadata Schemas
class HealthCheck(BaseModel):
    """Health check response."""
    status: str = Field(..., description="Health status")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Check timestamp")
    version: str = Field(..., description="API version")
    uptime_seconds: float = Field(..., description="Server uptime in seconds")
    components: Dict[str, Dict[str, Any]] = Field(..., description="Component health status")


class ComponentHealth(BaseModel):
    """Component health status."""
    name: str = Field(..., description="Component name")
    status: str = Field(..., description="Component status")
    message: Optional[str] = Field(default=None, description="Status message")
    response_time_ms: Optional[float] = Field(default=None, description="Response time in milliseconds")
    last_check: datetime = Field(default_factory=datetime.utcnow, description="Last check timestamp")


class APIInfo(BaseModel):
    """API information response."""
    title: str = Field(..., description="API title")
    description: str = Field(..., description="API description")
    version: str = Field(..., description="API version")
    docs_url: str = Field(..., description="API documentation URL")
    health_url: str = Field(..., description="Health check URL")
    endpoints: List[str] = Field(..., description="Available endpoints")
    features: List[str] = Field(..., description="Available features")


class ErrorResponse(BaseModel):
    """Error response schema."""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
    request_id: Optional[str] = Field(default=None, description="Request identifier")


# Validation and Utility Schemas
class ValidationResult(BaseModel):
    """Validation result."""
    is_valid: bool = Field(..., description="Whether validation passed")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")


class QueryAnalysis(BaseModel):
    """Query analysis result."""
    original_query: str = Field(..., description="Original query")
    normalized_query: str = Field(..., description="Normalized query")
    query_type: QueryType = Field(..., description="Detected query type")
    schemes: List[str] = Field(default_factory=list, description="Detected schemes")
    sections: List[str] = Field(default_factory=list, description="Detected sections")
    numerical_data: Dict[str, List[float]] = Field(default_factory=dict, description="Extracted numerical data")
    confidence: float = Field(..., description="Analysis confidence")


class Metrics(BaseModel):
    """API metrics."""
    total_requests: int = Field(..., description="Total number of requests")
    successful_requests: int = Field(..., description="Number of successful requests")
    failed_requests: int = Field(..., description="Number of failed requests")
    blocked_requests: int = Field(..., description="Number of blocked requests")
    average_response_time_ms: float = Field(..., description="Average response time in milliseconds")
    requests_per_minute: float = Field(..., description="Requests per minute")
    uptime_percentage: float = Field(..., description="Uptime percentage")
    last_updated: datetime = Field(default_factory=datetime.utcnow, description="Metrics last updated")


# Streaming Schemas (for future streaming support)
class StreamingChunk(BaseModel):
    """Streaming response chunk."""
    type: str = Field(..., description="Chunk type")
    content: Optional[str] = Field(default=None, description="Chunk content")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Chunk metadata")
    is_final: bool = Field(default=False, description="Whether this is the final chunk")
    chunk_index: int = Field(..., description="Chunk index")


class StreamingRequest(BaseModel):
    """Streaming request schema."""
    query: str = Field(..., description="User query")
    stream: bool = Field(default=True, description="Enable streaming")
    chunk_size: Optional[int] = Field(default=100, description="Chunk size for streaming")


# Utility functions for schema validation
def validate_chat_request(request: ChatRequest) -> ValidationResult:
    """Validate chat request."""
    errors = []
    warnings = []
    
    # Check query length
    if len(request.query) < 3:
        errors.append("Query too short (minimum 3 characters)")
    
    if len(request.query) > 1000:
        warnings.append("Query is very long, may affect performance")
    
    # Check for potential PII
    pii_indicators = ["pan", "aadhaar", "email", "phone", "otp"]
    query_lower = request.query.lower()
    for indicator in pii_indicators:
        if indicator in query_lower:
            warnings.append(f"Potential PII detected: {indicator}")
    
    # Check top_k value
    if request.top_k and (request.top_k < 1 or request.top_k > 50):
        errors.append("top_k must be between 1 and 50")
    
    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings
    )


def create_error_response(error_type: str, message: str, details: Optional[Dict] = None) -> ErrorResponse:
    """Create standardized error response."""
    return ErrorResponse(
        error=error_type,
        message=message,
        details=details
    )


def create_success_response(
    answer: str,
    source: Optional[str] = None,
    last_updated: Optional[str] = None,
    confidence: Optional[float] = None,
    chunks: Optional[List[ChunkInfo]] = None,
    retrieval_metadata: Optional[RetrievalMetadata] = None,
    generation_metadata: Optional[GenerationMetadata] = None
) -> ChatResponse:
    """Create successful chat response."""
    return ChatResponse(
        status=ResponseStatus.SUCCESS,
        answer=answer,
        source=source,
        last_updated=last_updated,
        confidence=confidence,
        chunks=chunks,
        retrieval_metadata=retrieval_metadata,
        generation_metadata=generation_metadata
    )


def create_blocked_response(reason: str, details: Optional[str] = None) -> ChatResponse:
    """Create blocked response."""
    return ChatResponse(
        status=ResponseStatus.BLOCKED,
        blocked_reason=reason,
        error=details
    )
