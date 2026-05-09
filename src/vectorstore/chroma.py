"""
ChromaDB Vector Store Implementation

Provides ChromaDB implementation of the vector store abstraction
with collection management, duplicate prevention, and metadata indexing.
"""

import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import chromadb
import numpy as np
import structlog

from .abstraction import VectorStore, VectorSearchResult, CollectionInfo
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ChromaDBVectorStore(VectorStore):
    """ChromaDB implementation of vector store."""
    
    def __init__(self, collection_name: str, embedding_dim: int = 384, persist_directory: str = "data/index/chroma"):
        super().__init__(collection_name, embedding_dim)
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        self.client = None
        self.collection = None
    
    async def connect(self) -> bool:
        """Connect to ChromaDB."""
        try:
            logger.info(
                "Connecting to ChromaDB",
                collection_name=self.collection_name,
                persist_directory=str(self.persist_directory)
            )
            
            # Initialize ChromaDB client
            self.client = chromadb.PersistentClient(
                path=str(self.persist_directory)
            )
            
            # Get or create collection
            try:
                self.collection = self.client.get_collection(
                    name=self.collection_name
                )
                logger.info(
                    "Connected to existing collection",
                    collection_name=self.collection_name
                )
            except Exception:
                # Collection doesn't exist, create it
                self.collection = self.client.create_collection(
                    name=self.collection_name,
                    metadata={"embedding_dim": self.embedding_dim}
                )
                logger.info(
                    "Created new collection",
                    collection_name=self.collection_name
                )
            
            self.is_connected = True
            return True
            
        except Exception as e:
            logger.error(
                "Failed to connect to ChromaDB",
                collection_name=self.collection_name,
                error=str(e)
            )
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from ChromaDB."""
        try:
            if self.client:
                self.client = None
                self.collection = None
                self.is_connected = False
                logger.info(
                    "Disconnected from ChromaDB",
                    collection_name=self.collection_name
                )
        except Exception as e:
            logger.error(
                "Failed to disconnect from ChromaDB",
                collection_name=self.collection_name,
                error=str(e)
            )
    
    async def create_collection(self, metadata: Optional[Dict] = None) -> bool:
        """Create a new collection."""
        try:
            if not self.is_connected:
                await self.connect()
            
            # Delete existing collection if it exists
            try:
                self.client.delete_collection(name=self.collection_name)
                logger.info(
                    "Deleted existing collection",
                    collection_name=self.collection_name
                )
            except Exception:
                pass  # Collection doesn't exist
            
            # Create new collection
            collection_metadata = {"embedding_dim": self.embedding_dim}
            if metadata:
                collection_metadata.update(metadata)
            
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata=collection_metadata
            )
            
            logger.info(
                "Created new collection",
                collection_name=self.collection_name,
                metadata=collection_metadata
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "Failed to create collection",
                collection_name=self.collection_name,
                error=str(e)
            )
            return False
    
    async def delete_collection(self) -> bool:
        """Delete current collection."""
        try:
            if not self.is_connected:
                await self.connect()
            
            self.client.delete_collection(name=self.collection_name)
            self.collection = None
            
            logger.info(
                "Deleted collection",
                collection_name=self.collection_name
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "Failed to delete collection",
                collection_name=self.collection_name,
                error=str(e)
            )
            return False
    
    async def collection_exists(self) -> bool:
        """Check if collection exists."""
        try:
            if not self.is_connected:
                await self.connect()
            
            collections = self.client.list_collections()
            return any(col.name == self.collection_name for col in collections)
            
        except Exception as e:
            logger.error(
                "Failed to check collection existence",
                collection_name=self.collection_name,
                error=str(e)
            )
            return False
    
    async def get_collection_info(self) -> Optional[CollectionInfo]:
        """Get information about collection."""
        try:
            if not self.is_connected:
                await self.connect()
            
            if not self.collection:
                return None
            
            # Get collection metadata
            metadata = self.collection.metadata or {}
            
            # Get document count
            count = self.collection.count()
            
            # Get creation/update times from metadata
            created_at = metadata.get('created_at', datetime.now().isoformat())
            updated_at = metadata.get('updated_at', datetime.now().isoformat())
            
            return CollectionInfo(
                name=self.collection_name,
                count=count,
                dimension=self.embedding_dim,
                created_at=datetime.fromisoformat(created_at) if isinstance(created_at, str) else created_at,
                updated_at=datetime.fromisoformat(updated_at) if isinstance(updated_at, str) else updated_at,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(
                "Failed to get collection info",
                collection_name=self.collection_name,
                error=str(e)
            )
            return None
    
    async def add_embeddings(
        self,
        embeddings: List[List[float]],
        documents: List[str],
        metadatas: List[Dict],
        ids: List[str]
    ) -> List[str]:
        """Add embeddings to collection."""
        try:
            if not self.is_connected:
                await self.connect()
            
            # Validate inputs
            validation_result = await self.validate_embeddings(
                embeddings, documents, metadatas, ids
            )
            
            if not validation_result["is_valid"]:
                raise ValueError(f"Validation failed: {validation_result['errors']}")
            
            # Check for duplicates before adding
            duplicate_ids = await self._check_duplicates(embeddings, ids)
            if duplicate_ids:
                logger.warning(
                    "Found potential duplicates",
                    duplicate_ids=duplicate_ids
                )
            
            # Add embeddings to ChromaDB
            self.collection.add(
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            
            # Update collection metadata
            await self._update_collection_metadata()
            
            logger.info(
                "Added embeddings to collection",
                collection_name=self.collection_name,
                count=len(embeddings),
                duplicate_ids=len(duplicate_ids)
            )
            
            return ids
            
        except Exception as e:
            logger.error(
                "Failed to add embeddings",
                collection_name=self.collection_name,
                error=str(e)
            )
            raise
    
    async def update_embeddings(
        self,
        embeddings: List[List[float]],
        documents: List[str],
        metadatas: List[Dict],
        ids: List[str]
    ) -> List[str]:
        """Update embeddings in collection."""
        try:
            if not self.is_connected:
                await self.connect()
            
            # Delete existing embeddings
            await self.delete_embeddings(ids)
            
            # Add new embeddings
            return await self.add_embeddings(embeddings, documents, metadatas, ids)
            
        except Exception as e:
            logger.error(
                "Failed to update embeddings",
                collection_name=self.collection_name,
                error=str(e)
            )
            raise
    
    async def delete_embeddings(self, ids: List[str]) -> bool:
        """Delete embeddings by IDs."""
        try:
            if not self.is_connected:
                await self.connect()
            
            self.collection.delete(ids=ids)
            
            # Update collection metadata
            await self._update_collection_metadata()
            
            logger.info(
                "Deleted embeddings from collection",
                collection_name=self.collection_name,
                count=len(ids)
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "Failed to delete embeddings",
                collection_name=self.collection_name,
                error=str(e)
            )
            return False
    
    async def search(
        self,
        query_embedding: List[float],
        n_results: int = 10,
        where: Optional[Dict] = None,
        include: Optional[List[str]] = None
    ) -> List[VectorSearchResult]:
        """Search for similar vectors."""
        try:
            if not self.is_connected:
                await self.connect()
            
            # Perform similarity search
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where,
                include=include or ["metadatas", "documents", "distances"]
            )
            
            # Convert to VectorSearchResult format
            search_results = []
            
            if results and results['ids'] and results['ids'][0]:
                for i, doc_id in enumerate(results['ids'][0]):
                    search_results.append(VectorSearchResult(
                        chunk_id=doc_id,
                        scheme_id=results['metadatas'][0][i].get('scheme_id', ''),
                        section=results['metadatas'][0][i].get('section', ''),
                        text=results['documents'][0][i],
                        score=1.0 - results['distances'][0][i],  # Convert distance to similarity
                        metadata=results['metadatas'][0][i],
                        distance=results['distances'][0][i]
                    ))
            
            logger.info(
                "Vector search completed",
                collection_name=self.collection_name,
                n_results=len(search_results),
                query_embedding_dim=len(query_embedding)
            )
            
            return search_results
            
        except Exception as e:
            logger.error(
                "Failed to perform vector search",
                collection_name=self.collection_name,
                error=str(e)
            )
            return []
    
    async def search_by_text(
        self,
        query_text: str,
        n_results: int = 10,
        where: Optional[Dict] = None,
        include: Optional[List[str]] = None
    ) -> List[VectorSearchResult]:
        """Search by text (requires embedding model)."""
        try:
            # For text search, we need to embed the query first
            # This would require access to the embedding model
            # For now, use ChromaDB's built-in text search
            if not self.is_connected:
                await self.connect()
            
            results = self.collection.query(
                query_texts=[query_text],
                n_results=n_results,
                where=where,
                include=include or ["metadatas", "documents", "distances"]
            )
            
            # Convert to VectorSearchResult format
            search_results = []
            
            if results and results['ids'] and results['ids'][0]:
                for i, doc_id in enumerate(results['ids'][0]):
                    search_results.append(VectorSearchResult(
                        chunk_id=doc_id,
                        scheme_id=results['metadatas'][0][i].get('scheme_id', ''),
                        section=results['metadatas'][0][i].get('section', ''),
                        text=results['documents'][0][i],
                        score=1.0 - results['distances'][0][i],
                        metadata=results['metadatas'][0][i],
                        distance=results['distances'][0][i]
                    ))
            
            logger.info(
                "Text search completed",
                collection_name=self.collection_name,
                n_results=len(search_results),
                query_text=query_text[:50] + "..." if len(query_text) > 50 else query_text
            )
            
            return search_results
            
        except Exception as e:
            logger.error(
                "Failed to perform text search",
                collection_name=self.collection_name,
                error=str(e)
            )
            return []
    
    async def get_by_ids(self, ids: List[str]) -> List[Dict]:
        """Get documents by IDs."""
        try:
            if not self.is_connected:
                await self.connect()
            
            results = self.collection.get(
                ids=ids,
                include=["metadatas", "documents"]
            )
            
            documents = []
            if results['ids']:
                for i, doc_id in enumerate(results['ids']):
                    documents.append({
                        "id": doc_id,
                        "document": results['documents'][i],
                        "metadata": results['metadatas'][i]
                    })
            
            logger.info(
                "Retrieved documents by IDs",
                collection_name=self.collection_name,
                count=len(documents)
            )
            
            return documents
            
        except Exception as e:
            logger.error(
                "Failed to get documents by IDs",
                collection_name=self.collection_name,
                error=str(e)
            )
            return []
    
    async def count(self) -> int:
        """Get total count of documents in collection."""
        try:
            if not self.is_connected:
                await self.connect()
            
            return self.collection.count()
            
        except Exception as e:
            logger.error(
                "Failed to get document count",
                collection_name=self.collection_name,
                error=str(e)
            )
            return 0
    
    async def get_duplicate_ids(self, threshold: float = 0.95) -> List[str]:
        """Find potential duplicate documents."""
        try:
            if not self.is_connected:
                await self.connect()
            
            # Get all documents
            all_docs = self.collection.get(include=["metadatas", "embeddings"])
            
            if not all_docs['ids']:
                return []
            
            duplicates = []
            embeddings = all_docs['embeddings']
            ids = all_docs['ids']
            
            # Compare embeddings for similarity
            for i in range(len(embeddings)):
                for j in range(i + 1, len(embeddings)):
                    # Calculate cosine similarity
                    emb1 = np.array(embeddings[i])
                    emb2 = np.array(embeddings[j])
                    
                    # Normalize vectors
                    emb1_norm = emb1 / np.linalg.norm(emb1)
                    emb2_norm = emb2 / np.linalg.norm(emb2)
                    
                    # Calculate cosine similarity
                    similarity = np.dot(emb1_norm, emb2_norm)
                    
                    if similarity >= threshold:
                        duplicates.append(ids[j])  # Mark the later one as duplicate
                        break
            
            logger.info(
                "Duplicate detection completed",
                collection_name=self.collection_name,
                total_documents=len(ids),
                duplicates_found=len(set(duplicates))
            )
            
            return list(set(duplicates))
            
        except Exception as e:
            logger.error(
                "Failed to detect duplicates",
                collection_name=self.collection_name,
                error=str(e)
            )
            return []
    
    async def _check_duplicates(self, embeddings: List[List[float]], ids: List[str]) -> List[str]:
        """Check for duplicates in new embeddings."""
        try:
            # Get existing embeddings for comparison
            existing_docs = self.collection.get(include=["embeddings"])
            
            if not existing_docs['ids']:
                return []
            
            existing_embeddings = existing_docs['embeddings']
            existing_ids = existing_docs['ids']
            
            duplicates = []
            
            for i, new_embedding in enumerate(embeddings):
                new_emb = np.array(new_embedding)
                new_emb_norm = new_embedding / np.linalg.norm(new_emb)
                
                for j, existing_embedding in enumerate(existing_embeddings):
                    existing_emb = np.array(existing_embedding)
                    existing_emb_norm = existing_embedding / np.linalg.norm(existing_embedding)
                    
                    # Calculate cosine similarity
                    similarity = np.dot(new_emb_norm, existing_emb_norm)
                    
                    if similarity >= 0.95:  # High similarity threshold
                        duplicates.append(ids[i])
                        break
            
            return duplicates
            
        except Exception as e:
            logger.error(
                "Failed to check duplicates",
                collection_name=self.collection_name,
                error=str(e)
            )
            return []
    
    async def _update_collection_metadata(self) -> None:
        """Update collection metadata with current timestamp."""
        try:
            current_metadata = self.collection.metadata or {}
            current_metadata.update({
                "updated_at": datetime.now().isoformat(),
                "document_count": self.collection.count()
            })
            
            # ChromaDB doesn't support direct metadata update
            # This would require recreating the collection
            logger.debug(
                "Collection metadata updated",
                collection_name=self.collection_name,
                metadata=current_metadata
            )
            
        except Exception as e:
            logger.error(
                "Failed to update collection metadata",
                collection_name=self.collection_name,
                error=str(e)
            )
