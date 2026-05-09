"""
Vector Store Abstraction

Provides abstract base class for vector storage implementations
with common interface and functionality.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime

import structlog

logger = get_logger(__name__)


@dataclass
class VectorSearchResult:
    """Result of a vector search operation."""
    
    chunk_id: str
    scheme_id: str
    section: str
    text: str
    score: float
    metadata: Dict[str, Any]
    distance: Optional[float] = None


@dataclass
class CollectionInfo:
    """Information about a vector collection."""
    
    name: str
    count: int
    dimension: int
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any]


class VectorStore(ABC):
    """Abstract base class for vector storage implementations."""
    
    def __init__(self, collection_name: str, embedding_dim: int = 384):
        self.collection_name = collection_name
        self.embedding_dim = embedding_dim
        self.is_connected = False
    
    @abstractmethod
    async def connect(self) -> bool:
        """Connect to the vector store."""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the vector store."""
        pass
    
    @abstractmethod
    async def create_collection(self, metadata: Optional[Dict] = None) -> bool:
        """Create a new collection."""
        pass
    
    @abstractmethod
    async def delete_collection(self) -> bool:
        """Delete the current collection."""
        pass
    
    @abstractmethod
    async def collection_exists(self) -> bool:
        """Check if collection exists."""
        pass
    
    @abstractmethod
    async def get_collection_info(self) -> Optional[CollectionInfo]:
        """Get information about the collection."""
        pass
    
    @abstractmethod
    async def add_embeddings(
        self,
        embeddings: List[List[float]],
        documents: List[str],
        metadatas: List[Dict],
        ids: List[str]
    ) -> List[str]:
        """Add embeddings to the collection."""
        pass
    
    @abstractmethod
    async def update_embeddings(
        self,
        embeddings: List[List[float]],
        documents: List[str],
        metadatas: List[Dict],
        ids: List[str]
    ) -> List[str]:
        """Update embeddings in the collection."""
        pass
    
    @abstractmethod
    async def delete_embeddings(self, ids: List[str]) -> bool:
        """Delete embeddings by IDs."""
        pass
    
    @abstractmethod
    async def search(
        self,
        query_embedding: List[float],
        n_results: int = 10,
        where: Optional[Dict] = None,
        include: Optional[List[str]] = None
    ) -> List[VectorSearchResult]:
        """Search for similar vectors."""
        pass
    
    @abstractmethod
    async def search_by_text(
        self,
        query_text: str,
        n_results: int = 10,
        where: Optional[Dict] = None,
        include: Optional[List[str]] = None
    ) -> List[VectorSearchResult]:
        """Search by text (requires embedding model)."""
        pass
    
    @abstractmethod
    async def get_by_ids(self, ids: List[str]) -> List[Dict]:
        """Get documents by IDs."""
        pass
    
    @abstractmethod
    async def count(self) -> int:
        """Get total count of documents in collection."""
        pass
    
    @abstractmethod
    async def get_duplicate_ids(self, threshold: float = 0.95) -> List[str]:
        """Find potential duplicate documents."""
        pass
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the vector store."""
        try:
            if not self.is_connected:
                return {"status": "error", "message": "Not connected"}
            
            # Basic operations test
            count = await self.count()
            collection_info = await self.get_collection_info()
            
            return {
                "status": "healthy",
                "collection_name": self.collection_name,
                "document_count": count,
                "collection_info": collection_info is not None,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(
                "Vector store health check failed",
                collection_name=self.collection_name,
                error=str(e)
            )
            return {
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def validate_embeddings(
        self,
        embeddings: List[List[float]],
        documents: List[str],
        metadatas: List[Dict],
        ids: List[str]
    ) -> Dict[str, Any]:
        """Validate inputs before adding to vector store."""
        validation_result = {
            "is_valid": True,
            "errors": [],
            "warnings": []
        }
        
        # Check lengths match
        if len(embeddings) != len(documents):
            validation_result["errors"].append(
                f"Embeddings count ({len(embeddings)}) != documents count ({len(documents)})"
            )
            validation_result["is_valid"] = False
        
        if len(embeddings) != len(metadatas):
            validation_result["errors"].append(
                f"Embeddings count ({len(embeddings)}) != metadatas count ({len(metadatas)})"
            )
            validation_result["is_valid"] = False
        
        if len(embeddings) != len(ids):
            validation_result["errors"].append(
                f"Embeddings count ({len(embeddings)}) != ids count ({len(ids)})"
            )
            validation_result["is_valid"] = False
        
        # Check embedding dimensions
        for i, embedding in enumerate(embeddings):
            if len(embedding) != self.embedding_dim:
                validation_result["errors"].append(
                    f"Embedding {i} dimension ({len(embedding)}) != expected ({self.embedding_dim})"
                )
                validation_result["is_valid"] = False
        
        # Check for empty documents
        for i, doc in enumerate(documents):
            if not doc or not doc.strip():
                validation_result["warnings"].append(f"Document {i} is empty")
        
        # Check for missing required metadata
        required_fields = ["chunk_id", "scheme_id", "section"]
        for i, metadata in enumerate(metadatas):
            for field in required_fields:
                if field not in metadata:
                    validation_result["warnings"].append(
                        f"Document {i} missing required metadata field: {field}"
                    )
        
        return validation_result
