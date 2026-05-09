"""
Cross-Encoder Reranker for Retrieval Layer

Implements BAAI/bge-reranker-base for reranking retrieved chunks
to improve retrieval precision.
"""

import asyncio
import time
from typing import Dict, List, Optional

try:
    from sentence_transformers import CrossEncoder
    CROSS_ENCODER_AVAILABLE = True
except ImportError:
    CROSS_ENCODER_AVAILABLE = False

from src.utils.logger import get_logger

logger = get_logger(__name__)


class CrossEncoderReranker:
    """Cross-encoder reranker for improving retrieval precision."""
    
    def __init__(self, model_name: str = "BAAI/bge-reranker-base"):
        self.model_name = model_name
        self.model = None
        self.is_initialized = False
        
        if not CROSS_ENCODER_AVAILABLE:
            logger.warning("sentence-transformers not available, reranking disabled")
            return
    
    async def initialize(self) -> bool:
        """Initialize the cross-encoder model."""
        try:
            if not CROSS_ENCODER_AVAILABLE:
                logger.error("Cross-encoder not available due to missing dependencies")
                return False
            
            logger.info(
                "Initializing cross-encoder reranker",
                model=self.model_name
            )
            
            # Load model (this might take some time)
            self.model = CrossEncoder(self.model_name)
            self.is_initialized = True
            
            logger.info("Cross-encoder reranker initialized successfully")
            return True
            
        except Exception as e:
            logger.error(
                "Cross-encoder initialization failed",
                model=self.model_name,
                error=str(e)
            )
            return False
    
    async def rerank(
        self,
        query: str,
        passages: List[Dict],
        top_k: int = 3
    ) -> List[Dict]:
        """
        Rerank passages using cross-encoder.
        
        Args:
            query: Original query
            passages: List of passage dictionaries with text and metadata
            top_k: Number of top passages to return
            
        Returns:
            Reranked passages with scores
        """
        if not self.is_initialized or not self.model:
            logger.warning("Cross-encoder not initialized, returning original passages")
            return passages[:top_k]
        
        try:
            logger.info(
                "Starting cross-encoder reranking",
                query=query[:50] + "..." if len(query) > 50 else query,
                passages_count=len(passages),
                top_k=top_k
            )
            
            start_time = time.time()
            
            # Prepare query-passage pairs
            pairs = []
            for passage in passages:
                passage_text = passage.get('text', '')
                pairs.append([query, passage_text])
            
            # Get scores from cross-encoder
            scores = self.model.predict(pairs)
            
            # Combine passages with scores
            scored_passages = []
            for i, passage in enumerate(passages):
                scored_passage = passage.copy()
                scored_passage['rerank_score'] = float(scores[i])
                scored_passage['rerank_rank'] = i + 1
                scored_passages.append(scored_passage)
            
            # Sort by rerank score (descending)
            scored_passages.sort(key=lambda x: x['rerank_score'], reverse=True)
            
            # Take top_k results
            reranked = scored_passages[:top_k]
            
            reranking_time = time.time() - start_time
            
            logger.info(
                "Cross-encoder reranking completed",
                original_count=len(passages),
                reranked_count=len(reranked),
                reranking_time_ms=reranking_time * 1000,
                top_score=reranked[0]['rerank_score'] if reranked else 0
            )
            
            return reranked
            
        except Exception as e:
            logger.error(
                "Cross-encoder reranking failed",
                query=query[:50],
                error=str(e)
            )
            # Fallback to original passages
            return passages[:top_k]
    
    def is_available(self) -> bool:
        """Check if cross-encoder is available and initialized."""
        return CROSS_ENCODER_AVAILABLE and self.is_initialized
    
    def get_model_info(self) -> Dict:
        """Get information about the cross-encoder model."""
        return {
            "model_name": self.model_name,
            "is_available": self.is_available(),
            "is_initialized": self.is_initialized,
            "has_dependencies": CROSS_ENCODER_AVAILABLE
        }


def create_reranker(model_name: str = "BAAI/bge-reranker-base") -> Optional[CrossEncoderReranker]:
    """Create cross-encoder reranker instance."""
    try:
        reranker = CrossEncoderReranker(model_name=model_name)
        return reranker
    except Exception as e:
        logger.error(
            "Failed to create reranker",
            model_name=model_name,
            error=str(e)
        )
        return None
