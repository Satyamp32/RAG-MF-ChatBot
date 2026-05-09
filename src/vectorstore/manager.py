"""
Vector Store Manager

Provides high-level management for vector store operations
including collection management, testing utilities, and health monitoring.
"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

import structlog

from .abstraction import VectorStore
from .chroma import ChromaDBVectorStore
from src.utils.logger import get_logger

logger = get_logger(__name__)


class VectorStoreManager:
    """Manager for vector store operations."""
    
    def __init__(self, collection_name: str = "mutual_fund_chunks"):
        self.collection_name = collection_name
        self.vector_store: Optional[VectorStore] = None
        self.embedding_dim = 384
    
    async def initialize(self, persist_directory: str = "data/index/chroma") -> bool:
        """Initialize vector store connection."""
        try:
            logger.info(
                "Initializing vector store manager",
                collection_name=self.collection_name,
                persist_directory=persist_directory
            )
            
            # Initialize ChromaDB vector store
            self.vector_store = ChromaDBVectorStore(
                collection_name=self.collection_name,
                embedding_dim=self.embedding_dim,
                persist_directory=persist_directory
            )
            
            # Connect to vector store
            connected = await self.vector_store.connect()
            
            if connected:
                logger.info(
                    "Vector store manager initialized successfully",
                    collection_name=self.collection_name
                )
                return True
            else:
                logger.error(
                    "Failed to initialize vector store manager",
                    collection_name=self.collection_name
                )
                return False
                
        except Exception as e:
            logger.error(
                "Vector store manager initialization failed",
                collection_name=self.collection_name,
                error=str(e)
            )
            return False
    
    async def create_collection(self, metadata: Optional[Dict] = None) -> bool:
        """Create a new collection."""
        if not self.vector_store:
            return False
        
        return await self.vector_store.create_collection(metadata)
    
    async def delete_collection(self) -> bool:
        """Delete current collection."""
        if not self.vector_store:
            return False
        
        return await self.vector_store.delete_collection()
    
    async def add_chunks(self, chunks: List[Dict]) -> List[str]:
        """Add chunks to vector store."""
        if not self.vector_store:
            raise RuntimeError("Vector store not initialized")
        
        try:
            logger.info(
                "Adding chunks to vector store",
                chunk_count=len(chunks)
            )
            
            # Prepare data for vector store
            embeddings = []
            documents = []
            metadatas = []
            ids = []
            
            for chunk in chunks:
                embeddings.append(chunk['embedding'])
                documents.append(chunk['text'])
                
                # Prepare metadata
                metadata = {
                    'chunk_id': chunk['chunk_id'],
                    'scheme_id': chunk['scheme_id'],
                    'scheme_name': chunk.get('scheme_name', ''),
                    'section': chunk['section'],
                    'section_source': chunk.get('section_source', 'html_section'),
                    'token_count': chunk.get('token_count', 0),
                    'content_hash': chunk['content_hash'],
                    'stable_content_hash': chunk['stable_content_hash'],
                    'chunk_index': chunk.get('chunk_index', 0),
                    'last_updated': chunk.get('last_updated', datetime.now().isoformat()),
                    'doc_type': chunk.get('doc_type', 'Product_Page'),
                    'source_url': chunk.get('source_url', '')
                }
                metadatas.append(metadata)
                ids.append(chunk['chunk_id'])
            
            # Add to vector store
            added_ids = await self.vector_store.add_embeddings(
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            
            logger.info(
                "Chunks added to vector store",
                collection_name=self.collection_name,
                added_count=len(added_ids),
                total_requested=len(chunks)
            )
            
            return added_ids
            
        except Exception as e:
            logger.error(
                "Failed to add chunks to vector store",
                collection_name=self.collection_name,
                error=str(e)
            )
            raise
    
    async def search_chunks(
        self,
        query_text: str,
        n_results: int = 10,
        where: Optional[Dict] = None,
        include: Optional[List[str]] = None
    ) -> List[Dict]:
        """Search chunks by text."""
        if not self.vector_store:
            raise RuntimeError("Vector store not initialized")
        
        try:
            results = await self.vector_store.search_by_text(
                query_text=query_text,
                n_results=n_results,
                where=where,
                include=include
            )
            
            # Convert to dictionary format
            search_results = []
            for result in results:
                search_results.append({
                    'chunk_id': result.chunk_id,
                    'scheme_id': result.scheme_id,
                    'section': result.section,
                    'text': result.text,
                    'score': result.score,
                    'distance': result.distance,
                    'metadata': result.metadata
                })
            
            logger.info(
                "Chunk search completed",
                collection_name=self.collection_name,
                query_text=query_text[:50] + "..." if len(query_text) > 50 else query_text,
                results_count=len(search_results)
            )
            
            return search_results
            
        except Exception as e:
            logger.error(
                "Failed to search chunks",
                collection_name=self.collection_name,
                query_text=query_text,
                error=str(e)
            )
            raise
    
    async def get_chunk_by_id(self, chunk_id: str) -> Optional[Dict]:
        """Get a specific chunk by ID."""
        if not self.vector_store:
            raise RuntimeError("Vector store not initialized")
        
        try:
            documents = await self.vector_store.get_by_ids([chunk_id])
            
            if documents:
                doc = documents[0]
                return {
                    'chunk_id': doc['id'],
                    'text': doc['document'],
                    'metadata': doc['metadata']
                }
            
            return None
            
        except Exception as e:
            logger.error(
                "Failed to get chunk by ID",
                collection_name=self.collection_name,
                chunk_id=chunk_id,
                error=str(e)
            )
            return None
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get collection statistics."""
        if not self.vector_store:
            raise RuntimeError("Vector store not initialized")
        
        try:
            collection_info = await self.vector_store.get_collection_info()
            count = await self.vector_store.count()
            
            stats = {
                'collection_name': self.collection_name,
                'document_count': count,
                'embedding_dimension': self.embedding_dim,
                'collection_exists': collection_info is not None,
                'created_at': collection_info.created_at.isoformat() if collection_info else None,
                'updated_at': collection_info.updated_at.isoformat() if collection_info else None,
                'metadata': collection_info.metadata if collection_info else {}
            }
            
            return stats
            
        except Exception as e:
            logger.error(
                "Failed to get collection stats",
                collection_name=self.collection_name,
                error=str(e)
            )
            return {}
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check."""
        if not self.vector_store:
            return {
                'status': 'error',
                'message': 'Vector store not initialized'
            }
        
        try:
            # Basic health check
            health = await self.vector_store.health_check()
            
            # Add additional checks
            stats = await self.get_collection_stats()
            health.update({
                'collection_stats': stats,
                'manager_initialized': self.vector_store is not None
            })
            
            return health
            
        except Exception as e:
            logger.error(
                "Vector store health check failed",
                collection_name=self.collection_name,
                error=str(e)
            )
            return {
                'status': 'error',
                'message': str(e)
            }
    
    async def run_retrieval_tests(self) -> Dict[str, Any]:
        """Run retrieval tests to validate vector store performance."""
        if not self.vector_store:
            raise RuntimeError("Vector store not initialized")
        
        try:
            logger.info(
                "Starting retrieval tests",
                collection_name=self.collection_name
            )
            
            test_queries = [
                "expense ratio",
                "fund manager",
                "minimum investment",
                "exit load",
                "risk level",
                "scheme details",
                "fund returns"
            ]
            
            test_results = {}
            
            for query in test_queries:
                try:
                    # Search for each test query
                    results = await self.search_chunks(query, n_results=5)
                    
                    test_results[query] = {
                        'success': True,
                        'results_count': len(results),
                        'top_score': results[0]['score'] if results else 0,
                        'sections_found': list(set(r['section'] for r in results)),
                        'schemes_found': list(set(r['scheme_id'] for r in results))
                    }
                    
                except Exception as e:
                    test_results[query] = {
                        'success': False,
                        'error': str(e)
                    }
            
            # Calculate overall test statistics
            successful_tests = sum(1 for r in test_results.values() if r.get('success', False))
            total_tests = len(test_results)
            
            test_summary = {
                'total_tests': total_tests,
                'successful_tests': successful_tests,
                'success_rate': (successful_tests / total_tests) * 100 if total_tests > 0 else 0,
                'test_results': test_results,
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(
                "Retrieval tests completed",
                collection_name=self.collection_name,
                success_rate=test_summary['success_rate']
            )
            
            return test_summary
            
        except Exception as e:
            logger.error(
                "Retrieval tests failed",
                collection_name=self.collection_name,
                error=str(e)
            )
            return {
                'success': False,
                'error': str(e)
            }
    
    async def cleanup_duplicates(self, threshold: float = 0.95) -> Dict[str, Any]:
        """Find and remove duplicate documents."""
        if not self.vector_store:
            raise RuntimeError("Vector store not initialized")
        
        try:
            logger.info(
                "Starting duplicate cleanup",
                collection_name=self.collection_name,
                threshold=threshold
            )
            
            # Find duplicates
            duplicate_ids = await self.vector_store.get_duplicate_ids(threshold)
            
            if not duplicate_ids:
                return {
                    'duplicates_found': 0,
                    'removed_count': 0,
                    'threshold': threshold
                }
            
            # Remove duplicates
            removed = await self.vector_store.delete_embeddings(duplicate_ids)
            
            cleanup_result = {
                'duplicates_found': len(duplicate_ids),
                'removed_count': len(duplicate_ids) if removed else 0,
                'threshold': threshold,
                'duplicate_ids': duplicate_ids,
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(
                "Duplicate cleanup completed",
                collection_name=self.collection_name,
                duplicates_found=cleanup_result['duplicates_found'],
                removed_count=cleanup_result['removed_count']
            )
            
            return cleanup_result
            
        except Exception as e:
            logger.error(
                "Duplicate cleanup failed",
                collection_name=self.collection_name,
                error=str(e)
            )
            return {
                'success': False,
                'error': str(e)
            }
    
    async def export_collection(self, export_path: str) -> bool:
        """Export collection data to file."""
        if not self.vector_store:
            raise RuntimeError("Vector store not initialized")
        
        try:
            logger.info(
                "Starting collection export",
                collection_name=self.collection_name,
                export_path=export_path
            )
            
            # Get all documents
            collection_info = await self.vector_store.get_collection_info()
            count = await self.vector_store.count()
            
            # This would need to be implemented based on specific vector store
            # For now, just export metadata
            export_data = {
                'collection_name': self.collection_name,
                'export_timestamp': datetime.now().isoformat(),
                'document_count': count,
                'collection_info': collection_info.__dict__ if collection_info else None
            }
            
            export_file = Path(export_path)
            export_file.parent.mkdir(parents=True, exist_ok=True)
            
            import json
            with open(export_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, default=str)
            
            logger.info(
                "Collection export completed",
                collection_name=self.collection_name,
                export_path=str(export_file)
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "Collection export failed",
                collection_name=self.collection_name,
                export_path=export_path,
                error=str(e)
            )
            return False
