"""
Hybrid Retriever for Retrieval Layer

Implements dense vector search, sparse BM25 search, metadata filtering,
and adaptive weighted reciprocal rank fusion for optimal mutual fund retrieval.
"""

import asyncio
import time
from typing import Dict, List, Optional, Tuple

import numpy as np

from src.utils.logger import get_logger
from vectorstore.manager import VectorStoreManager
from retrieval.reranker import create_reranker

logger = get_logger(__name__)


class HybridRetriever:
    """Hybrid retriever with dense, sparse, and metadata-aware retrieval."""
    
    def __init__(
        self,
        dense_weight: float = 0.4,
        sparse_weight: float = 0.6,
        top_k: int = 10,
        min_score: float = 0.1,
        enable_reranking: bool = True,
        rerank_top_k: int = 3
    ):
        self.dense_weight = dense_weight
        self.sparse_weight = sparse_weight
        self.top_k = top_k
        self.min_score = min_score
        self.enable_reranking = enable_reranking
        self.rerank_top_k = rerank_top_k
        
        # Validate weights
        if abs(dense_weight + sparse_weight - 1.0) > 0.01:
            raise ValueError("Dense and sparse weights must sum to 1.0")
        
        self.vector_store = None
        self.reranker = None
    
    async def initialize(self, persist_directory: str = "data/index/chroma") -> bool:
        """Initialize vector store connection and reranker."""
        try:
            logger.info(
                "Initializing hybrid retriever",
                dense_weight=self.dense_weight,
                sparse_weight=self.sparse_weight,
                top_k=self.top_k,
                enable_reranking=self.enable_reranking
            )
            
            # Initialize vector store
            self.vector_store = VectorStoreManager()
            initialized = await self.vector_store.initialize(persist_directory)
            
            if not initialized:
                logger.error("Failed to initialize vector store")
                return False
            
            # Initialize reranker if enabled
            if self.enable_reranking:
                self.reranker = create_reranker()
                if self.reranker:
                    reranker_initialized = await self.reranker.initialize()
                    if not reranker_initialized:
                        logger.warning("Reranker initialization failed, continuing without reranking")
                        self.enable_reranking = False
                    else:
                        logger.info("Reranker initialized successfully")
                else:
                    logger.warning("Reranker creation failed, continuing without reranking")
                    self.enable_reranking = False
            
            logger.info("Hybrid retriever initialized successfully")
            return True
                
        except Exception as e:
            logger.error(
                "Hybrid retriever initialization failed",
                error=str(e)
            )
            return False
    
    async def retrieve(
        self,
        query: str,
        processed_query: Optional[Dict] = None,
        scheme_filter: Optional[str] = None,
        section_filter: Optional[str] = None,
        top_k: Optional[int] = None
    ) -> List[Dict]:
        """
        Perform hybrid retrieval with adaptive weighting and filtering.
        
        Args:
            query: User query string
            processed_query: Pre-processed query (optional)
            scheme_filter: Filter by specific scheme ID
            section_filter: Filter by specific section
            top_k: Override default top_k
            
        Returns:
            List of retrieved documents with scores
        """
        start_time = time.time()
        
        try:
            logger.info(
                "Starting hybrid retrieval",
                query=query[:100] + "..." if len(query) > 100 else query,
                scheme_filter=scheme_filter,
                section_filter=section_filter,
                top_k=top_k or self.top_k
            )
            
            # Use processed query if provided, otherwise process query
            if not processed_query:
                from retrieval.query_processor import QueryProcessor
                processor = QueryProcessor()
                processed_query = processor.normalize_query(query)
            
            # Determine adaptive weights based on query type
            query_type = processed_query.get('query_type', 'general')
            dense_weight, sparse_weight = self._get_adaptive_weights(query_type)
            
            # Prepare filters
            where_filter = {}
            if scheme_filter:
                where_filter['scheme_id'] = scheme_filter
            if section_filter:
                where_filter['section'] = section_filter
            
            # Get section boosts
            section_boosts = processor.get_section_boosts(
                query, processed_query.get('sections', [])
            )
            
            # Perform dense retrieval
            dense_results = []
            if dense_weight > 0:
                dense_results = await self._dense_retrieve(
                    query, where_filter, top_k
                )
            
            # Perform sparse retrieval
            sparse_results = []
            if sparse_weight > 0:
                sparse_results = await self._sparse_retrieve(
                    query, where_filter, top_k
                )
            
            # Fuse results with adaptive weighting
            fused_results = self._fuse_results(
                dense_results, sparse_results,
                dense_weight, sparse_weight
            )
            
            # Apply section boosts
            if section_boosts:
                fused_results = self._apply_section_boosts(
                    fused_results, section_boosts
                )
            
            # Apply confidence scoring
            scored_results = self._calculate_confidence_scores(
                fused_results, processed_query
            )
            
            # Filter by minimum score
            filtered_results = [
                result for result in scored_results
                if result.get('score', 0) >= self.min_score
            ]
            
            # Sort by final score
            filtered_results.sort(key=lambda x: x.get('final_score', 0), reverse=True)
            
            # Apply cross-encoder reranking if enabled
            if self.enable_reranking and self.reranker and self.reranker.is_available():
                reranked_results = await self.reranker.rerank(
                    query=query,
                    passages=filtered_results[:min(20, len(filtered_results))],  # Limit for reranking
                    top_k=self.rerank_top_k
                )
                final_results = reranked_results
            else:
                # Limit to top_k without reranking
                final_results = filtered_results[:top_k or self.top_k]
            
            retrieval_time = time.time() - start_time
            
            logger.info(
                "Hybrid retrieval completed",
                query_type=query_type,
                dense_results=len(dense_results),
                sparse_results=len(sparse_results),
                fused_results=len(fused_results),
                final_results=len(final_results),
                retrieval_time_ms=retrieval_time * 1000,
                top_k_used=len(final_results)
            )
            
            return final_results
            
        except Exception as e:
            logger.error(
                "Hybrid retrieval failed",
                query=query[:100],
                error=str(e)
            )
            return []
    
    async def _dense_retrieve(
        self,
        query: str,
        where_filter: Dict,
        top_k: int
    ) -> List[Dict]:
        """Perform dense vector search."""
        try:
            results = await self.vector_store.search_chunks(
                query_text=query,
                n_results=top_k,
                where=where_filter
            )
            
            # Convert to standard format
            dense_results = []
            for result in results:
                dense_results.append({
                    'chunk_id': result.get('chunk_id'),
                    'scheme_id': result.get('scheme_id'),
                    'section': result.get('section'),
                    'text': result.get('text'),
                    'score': result.get('score', 0),
                    'distance': result.get('distance', 1.0),
                    'source': 'dense',
                    'metadata': result.get('metadata', {})
                })
            
            return dense_results
            
        except Exception as e:
            logger.error(
                "Dense retrieval failed",
                query=query[:50],
                error=str(e)
            )
            return []
    
    async def _sparse_retrieve(
        self,
        query: str,
        where_filter: Dict,
        top_k: int
    ) -> List[Dict]:
        """Perform sparse BM25 search."""
        try:
            # For now, use vector store's text search as BM25 proxy
            # In production, this would use a proper BM25 index
            results = await self.vector_store.search_chunks(
                query_text=query,
                n_results=top_k,
                where=where_filter
            )
            
            # Convert to standard format with BM25 scoring
            sparse_results = []
            for i, result in enumerate(results):
                # Simulate BM25 score (lower is better for exact matches)
                text = result.get('text', '')
                query_lower = query.lower()
                text_lower = text.lower()
                
                # Simple BM25-like scoring
                score = 0.0
                if query_lower in text_lower:
                    score = 1.0  # Exact match
                else:
                    # Partial match scoring
                    query_words = query_lower.split()
                    text_words = text_lower.split()
                    matches = sum(1 for qw in query_words if qw in text_words)
                    score = matches / len(query_words)
                
                sparse_results.append({
                    'chunk_id': result.get('chunk_id'),
                    'scheme_id': result.get('scheme_id'),
                    'section': result.get('section'),
                    'text': result.get('text'),
                    'score': score,
                    'source': 'sparse',
                    'metadata': result.get('metadata', {})
                })
            
            # Sort by BM25 score
            sparse_results.sort(key=lambda x: x['score'], reverse=True)
            
            return sparse_results[:top_k]
            
        except Exception as e:
            logger.error(
                "Sparse retrieval failed",
                query=query[:50],
                error=str(e)
            )
            return []
    
    def _get_adaptive_weights(self, query_type: str) -> Tuple[float, float]:
        """Get adaptive weights based on query type."""
        
        # Default weights
        dense_weight = self.dense_weight
        sparse_weight = self.sparse_weight
        
        # Adjust weights based on query type
        if query_type == 'numerical_heavy':
            # Increase sparse weight for numerical queries
            dense_weight = max(0.2, dense_weight)
            sparse_weight = min(0.8, sparse_weight)
        elif query_type == 'section_specific':
            # Increase dense weight for section-specific queries
            dense_weight = min(0.6, dense_weight)
            sparse_weight = max(0.4, sparse_weight)
        elif query_type == 'semantic':
            # Increase dense weight for conceptual queries
            dense_weight = min(0.7, dense_weight)
            sparse_weight = max(0.3, sparse_weight)
        
        # Normalize to sum to 1.0
        total_weight = dense_weight + sparse_weight
        if total_weight > 0:
            dense_weight = dense_weight / total_weight
            sparse_weight = sparse_weight / total_weight
        
        logger.debug(
            "Adaptive weights calculated",
            query_type=query_type,
            dense_weight=dense_weight,
            sparse_weight=sparse_weight
        )
        
        return dense_weight, sparse_weight
    
    def _fuse_results(
        self,
        dense_results: List[Dict],
        sparse_results: List[Dict],
        dense_weight: float,
        sparse_weight: float
    ) -> List[Dict]:
        """Fuse dense and sparse results using weighted reciprocal rank fusion."""
        
        # Create result lookup
        all_results = {}
        
        # Add dense results
        for i, result in enumerate(dense_results):
            result_id = f"dense_{result['chunk_id']}"
            all_results[result_id] = {
                **result,
                'rank': i + 1,
                'source': 'dense'
            }
        
        # Add sparse results
        for i, result in enumerate(sparse_results):
            result_id = f"sparse_{result['chunk_id']}"
            all_results[result_id] = {
                **result,
                'rank': i + 1,
                'source': 'sparse'
            }
        
        # Weighted Reciprocal Rank Fusion (WRRF)
        fused_results = []
        
        for result_id, result_data in all_results.items():
            score = 0.0
            
            # Calculate reciprocal rank score
            rank = result_data['rank']
            reciprocal_rank = 1.0 / rank
            
            # Weight by source
            if result_data['source'] == 'dense':
                score += dense_weight * reciprocal_rank
            else:
                score += sparse_weight * reciprocal_rank
            
            fused_results.append({
                'chunk_id': result_data['chunk_id'],
                'scheme_id': result_data['scheme_id'],
                'section': result_data['section'],
                'text': result_data['text'],
                'score': score,
                'source': 'fused',
                'dense_rank': result_data['rank'] if result_data['source'] == 'dense' else None,
                'sparse_rank': result_data['rank'] if result_data['source'] == 'sparse' else None,
                'metadata': result_data.get('metadata', {})
            })
        
        # Sort by fused score
        fused_results.sort(key=lambda x: x['score'], reverse=True)
        
        return fused_results
    
    def _apply_section_boosts(
        self,
        results: List[Dict],
        section_boosts: Dict[str, float]
    ) -> List[Dict]:
        """Apply section-based score boosts."""
        
        boosted_results = []
        
        for result in results:
            section = result.get('section', '')
            boost = section_boosts.get(section, 0.0)
            
            boosted_result = result.copy()
            boosted_result['score'] = result.get('score', 0) * (1.0 + boost)
            boosted_result['section_boost'] = boost
            
            boosted_results.append(boosted_result)
        
        return boosted_results
    
    def _calculate_confidence_scores(
        self,
        results: List[Dict],
        processed_query: Dict
    ) -> List[Dict]:
        """Calculate confidence scores based on multiple factors."""
        
        query_type = processed_query.get('query_type', 'general')
        schemes = processed_query.get('schemes', [])
        sections = processed_query.get('sections', [])
        
        scored_results = []
        
        for result in results:
            base_score = result.get('score', 0)
            
            # Multi-factor confidence calculation
            confidence_factors = []
            
            # Factor 1: Base score (0-1)
            confidence_factors.append(min(base_score, 1.0))
            
            # Factor 2: Query type alignment
            if query_type == 'numerical_heavy' and 'numerical_data' in processed_query:
                confidence_factors.append(0.8)  # High confidence for numerical queries
            elif query_type == 'section_specific' and result.get('section') in sections:
                confidence_factors.append(0.7)  # High confidence for section matches
            elif query_type == 'semantic':
                confidence_factors.append(0.6)  # Medium confidence for semantic queries
            else:
                confidence_factors.append(0.5)  # Default confidence
            
            # Factor 3: Scheme confidence
            scheme_confidence = 0.5  # Default
            for scheme in schemes:
                if scheme.get('scheme_id') == result.get('scheme_id'):
                    scheme_confidence = scheme.get('confidence', 0.5)
                    break
            confidence_factors.append(scheme_confidence)
            
            # Factor 4: Score normalization
            max_score = max([r.get('score', 0) for r in results]) if results else 1.0
            if max_score > 0:
                normalized_score = base_score / max_score
                confidence_factors.append(normalized_score)
            else:
                confidence_factors.append(0.5)
            
            # Calculate final confidence score (geometric mean)
            final_confidence = np.prod(confidence_factors) ** (1.0 / len(confidence_factors))
            
            scored_result = result.copy()
            scored_result['final_score'] = base_score
            scored_result['confidence'] = final_confidence
            scored_result['confidence_factors'] = confidence_factors
            
            scored_results.append(scored_result)
        
        return scored_results
