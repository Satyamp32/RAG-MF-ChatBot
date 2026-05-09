"""
Backend Services

Service layer for integrating retrieval and generation components
with business logic and orchestration for the Mutual Fund RAG ChatBot.
"""

import time
import asyncio
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone

from retrieval.hybrid_retriever import HybridRetriever
from retrieval.query_processor import QueryProcessor
from reasoning.orchestrator import ReasoningOrchestrator
from reasoning.guardrails import Guardrails
from backend.config import config
from backend.schemas import (
    ChatRequest, ChatResponse, ChunkInfo, RetrievalMetadata,
    GenerationMetadata, QueryAnalysis, QueryType, GenerationMethod,
    ResponseStatus, create_success_response, create_blocked_response
)
from backend.logger import get_logger

logger = get_logger(__name__)


class RetrievalService:
    """Service for handling retrieval operations."""
    
    def __init__(self):
        self.retriever = None
        self.query_processor = QueryProcessor()
        self.is_initialized = False
    
    async def initialize(self) -> bool:
        """Initialize retrieval components."""
        try:
            logger.info("Initializing retrieval service")
            
            # Initialize hybrid retriever
            retrieval_config = config.get_retrieval_config()
            self.retriever = HybridRetriever(
                dense_weight=retrieval_config["dense_weight"],
                sparse_weight=retrieval_config["sparse_weight"],
                top_k=retrieval_config["top_k"],
                enable_reranking=retrieval_config["enable_reranking"],
                rerank_top_k=retrieval_config["rerank_top_k"]
            )
            
            # Initialize vector store
            initialized = await self.retriever.initialize(
                persist_directory=retrieval_config["persist_directory"]
            )
            
            if not initialized:
                logger.error("Failed to initialize retrieval service")
                return False
            
            self.is_initialized = True
            logger.info("Retrieval service initialized successfully")
            return True
            
        except Exception as e:
            logger.error("Retrieval service initialization failed", error=str(e))
            return False
    
    async def analyze_query(self, query: str) -> QueryAnalysis:
        """Analyze user query."""
        try:
            processed_query = self.query_processor.normalize_query(query)
            
            return QueryAnalysis(
                original_query=query,
                normalized_query=processed_query["normalized"],
                query_type=QueryType(processed_query["query_type"]),
                schemes=[s["scheme_id"] for s in processed_query["schemes"]],
                sections=processed_query["sections"],
                numerical_data=processed_query["numerical_data"],
                confidence=0.8  # Default confidence for query analysis
            )
            
        except Exception as e:
            logger.error("Query analysis failed", query=query, error=str(e))
            raise
    
    async def retrieve_chunks(
        self,
        query: str,
        query_analysis: QueryAnalysis,
        top_k: Optional[int] = None,
        scheme_filter: Optional[str] = None,
        section_filter: Optional[str] = None
    ) -> Tuple[List[ChunkInfo], RetrievalMetadata]:
        """Retrieve relevant chunks for query."""
        if not self.is_initialized:
            raise RuntimeError("Retrieval service not initialized")
        
        start_time = time.time()
        
        try:
            logger.info(
                "Starting chunk retrieval",
                query=query[:100],
                query_type=query_analysis.query_type,
                top_k=top_k or config.top_k,
                scheme_filter=scheme_filter,
                section_filter=section_filter
            )
            
            # Perform retrieval
            retrieved_chunks = await self.retriever.retrieve(
                query=query,
                top_k=top_k or config.top_k,
                scheme_filter=scheme_filter,
                section_filter=section_filter
            )
            
            # Convert to schema objects
            chunk_infos = []
            for chunk in retrieved_chunks:
                chunk_info = ChunkInfo(
                    chunk_id=chunk.get("chunk_id", ""),
                    scheme_id=chunk.get("scheme_id", ""),
                    section=chunk.get("section", ""),
                    text=chunk.get("text", ""),
                    score=chunk.get("score", 0.0),
                    confidence=chunk.get("confidence", 0.0),
                    source=chunk.get("source", "unknown"),
                    rerank_score=chunk.get("rerank_score"),
                    rerank_rank=chunk.get("rerank_rank")
                )
                chunk_infos.append(chunk_info)
            
            # Create metadata
            retrieval_time = time.time() - start_time
            
            metadata = RetrievalMetadata(
                query=query,
                query_type=query_analysis.query_type,
                chunks_used=len(chunk_infos),
                retrieval_time_ms=retrieval_time * 1000,
                dense_results=0,  # Would be populated from actual retrieval
                sparse_results=0,  # Would be populated from actual retrieval
                fused_results=len(chunk_infos),
                final_results=len(chunk_infos)
            )
            
            logger.info(
                "Chunk retrieval completed",
                chunks_count=len(chunk_infos),
                retrieval_time_ms=retrieval_time * 1000,
                top_score=chunk_infos[0].score if chunk_infos else 0
            )
            
            return chunk_infos, metadata
            
        except Exception as e:
            logger.error("Chunk retrieval failed", query=query, error=str(e))
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """Check retrieval service health."""
        health = {
            "status": "healthy" if self.is_initialized else "unhealthy",
            "initialized": self.is_initialized,
            "components": {}
        }
        
        if self.is_initialized:
            # Check retriever health
            try:
                # Test a simple query
                test_chunks = await self.retriever.retrieve("test query", top_k=1)
                health["components"]["retriever"] = {
                    "status": "healthy",
                    "test_query_success": True
                }
            except Exception as e:
                health["components"]["retriever"] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
        else:
            health["components"]["retriever"] = {
                "status": "not_initialized"
            }
        
        return health


class GenerationService:
    """Service for handling response generation."""
    
    def __init__(self):
        self.orchestrator = None
        self.guardrails = Guardrails()
        self.is_initialized = False
    
    async def initialize(self) -> bool:
        """Initialize generation components."""
        try:
            logger.info("Initializing generation service")
            
            # Initialize orchestrator
            generation_config = config.get_generation_config()
            self.orchestrator = ReasoningOrchestrator(
                use_groq=generation_config["use_groq"]
            )
            
            self.is_initialized = True
            logger.info("Generation service initialized successfully")
            return True
            
        except Exception as e:
            logger.error("Generation service initialization failed", error=str(e))
            return False
    
    async def generate_response(
        self,
        query: str,
        chunks: List[ChunkInfo],
        query_analysis: QueryAnalysis,
        use_groq: Optional[str] = None
    ) -> Tuple[Optional[str], Optional[str], Optional[str], GenerationMetadata]:
        """Generate response from retrieved chunks."""
        if not self.is_initialized:
            raise RuntimeError("Generation service not initialized")
        
        start_time = time.time()
        
        try:
            logger.info(
                "Starting response generation",
                query=query[:100],
                chunks_count=len(chunks),
                use_groq=use_groq or config.use_groq
            )
            
            # Convert chunks to dict format
            chunk_dicts = []
            for chunk in chunks:
                chunk_dict = {
                    "chunk_id": chunk.chunk_id,
                    "scheme_id": chunk.scheme_id,
                    "section": chunk.section,
                    "text": chunk.text,
                    "score": chunk.score,
                    "confidence": chunk.confidence,
                    "source": chunk.source,
                    "metadata": {}
                }
                chunk_dicts.append(chunk_dict)
            
            # Generate response
            response = await self.orchestrator.generate_response(
                query=query,
                retrieved_chunks=chunk_dicts,
                query_type=query_analysis.query_type.value
            )
            
            generation_time = time.time() - start_time
            
            if response.get("success"):
                # Extract response content
                content = response.get("response", {})
                answer = content.get("content", "")
                source_url = response.get("metadata", {}).get("source_url")
                last_updated = response.get("metadata", {}).get("last_updated")
                confidence = response.get("confidence", 0.0)
                
                # Determine generation method
                method = response.get("metadata", {}).get("generation_method", "extractive")
                generation_method = GenerationMethod.GROQ if method == "groq" else GenerationMethod.EXTRACTIVE
                
                # Create metadata
                metadata = GenerationMetadata(
                    generation_method=generation_method,
                    confidence=confidence,
                    generation_time_ms=generation_time * 1000,
                    source_url=source_url,
                    last_updated=last_updated,
                    guardrails_applied=True,
                    guardrails_passed=True
                )
                
                logger.info(
                    "Response generation completed",
                    generation_method=generation_method,
                    confidence=confidence,
                    generation_time_ms=generation_time * 1000
                )
                
                return answer, source_url, last_updated, metadata
            else:
                # Handle blocked or failed generation
                error_reason = response.get("reason", "Unknown error")
                logger.warning(
                    "Response generation blocked/failed",
                    reason=error_reason,
                    generation_time_ms=generation_time * 1000
                )
                
                metadata = GenerationMetadata(
                    generation_method=GenerationMethod.EXTRACTIVE,
                    confidence=0.0,
                    generation_time_ms=generation_time * 1000,
                    guardrails_applied=True,
                    guardrails_passed=False
                )
                
                return None, None, None, metadata
                
        except Exception as e:
            logger.error("Response generation failed", query=query, error=str(e))
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """Check generation service health."""
        health = {
            "status": "healthy" if self.is_initialized else "unhealthy",
            "initialized": self.is_initialized,
            "components": {}
        }
        
        if self.is_initialized:
            # Check orchestrator health
            try:
                # Test with a simple query and fake chunks
                test_chunks = [{
                    "chunk_id": "test",
                    "scheme_id": "test",
                    "section": "test",
                    "text": "test content",
                    "score": 1.0,
                    "confidence": 1.0,
                    "source": "test",
                    "metadata": {}
                }]
                
                response = await self.orchestrator.generate_response(
                    query="test",
                    retrieved_chunks=test_chunks
                )
                
                health["components"]["orchestrator"] = {
                    "status": "healthy",
                    "test_generation_success": response.get("success", False)
                }
            except Exception as e:
                health["components"]["orchestrator"] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
        else:
            health["components"]["orchestrator"] = {
                "status": "not_initialized"
            }
        
        return health


class ChatService:
    """Main service for chat functionality."""
    
    def __init__(self):
        self.retrieval_service = RetrievalService()
        self.generation_service = GenerationService()
        self.is_initialized = False
    
    async def initialize(self) -> bool:
        """Initialize all services."""
        try:
            logger.info("Initializing chat service")
            
            # Initialize retrieval service
            retrieval_initialized = await self.retrieval_service.initialize()
            if not retrieval_initialized:
                logger.error("Failed to initialize retrieval service")
                return False
            
            # Initialize generation service
            generation_initialized = await self.generation_service.initialize()
            if not generation_initialized:
                logger.error("Failed to initialize generation service")
                return False
            
            self.is_initialized = True
            logger.info("Chat service initialized successfully")
            return True
            
        except Exception as e:
            logger.error("Chat service initialization failed", error=str(e))
            return False
    
    async def process_chat_request(self, request: ChatRequest) -> ChatResponse:
        """Process chat request and generate response."""
        if not self.is_initialized:
            raise RuntimeError("Chat service not initialized")
        
        start_time = time.time()
        
        try:
            logger.info(
                "Processing chat request",
                query=request.query[:100],
                use_groq=request.use_groq,
                top_k=request.top_k
            )
            
            # Analyze query
            query_analysis = await self.retrieval_service.analyze_query(request.query)
            
            # Retrieve chunks
            chunks, retrieval_metadata = await self.retrieval_service.retrieve_chunks(
                query=request.query,
                query_analysis=query_analysis,
                top_k=request.top_k,
                scheme_filter=request.scheme_filter,
                section_filter=request.section_filter
            )
            
            # Generate response
            answer, source_url, last_updated, generation_metadata = await self.generation_service.generate_response(
                query=request.query,
                chunks=chunks,
                query_analysis=query_analysis,
                use_groq=request.use_groq
            )
            
            # Create response
            if answer and generation_metadata.guardrails_passed:
                response = create_success_response(
                    answer=answer,
                    source=source_url,
                    last_updated=last_updated,
                    confidence=generation_metadata.confidence,
                    chunks=chunks if request.include_metadata else None,
                    retrieval_metadata=retrieval_metadata if request.include_metadata else None,
                    generation_metadata=generation_metadata if request.include_metadata else None
                )
            else:
                # Response was blocked by guardrails
                response = create_blocked_response(
                    reason="Response blocked by safety filters",
                    details="The response was blocked due to safety policy violations"
                )
            
            # Log completion
            total_time = time.time() - start_time
            logger.info(
                "Chat request processed",
                success=response.status == ResponseStatus.SUCCESS,
                total_time_ms=total_time * 1000,
                chunks_count=len(chunks),
                confidence=generation_metadata.confidence
            )
            
            return response
            
        except Exception as e:
            logger.error("Chat request processing failed", query=request.query, error=str(e))
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """Check chat service health."""
        retrieval_health = await self.retrieval_service.health_check()
        generation_health = await self.generation_service.health_check()
        
        overall_status = "healthy"
        if retrieval_health["status"] != "healthy" or generation_health["status"] != "healthy":
            overall_status = "unhealthy"
        
        return {
            "status": overall_status,
            "initialized": self.is_initialized,
            "components": {
                "retrieval": retrieval_health,
                "generation": generation_health
            }
        }
