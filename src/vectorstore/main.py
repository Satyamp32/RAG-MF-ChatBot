"""
Main entry point for Phase 1.6 - Vector DB Persistence.
"""

import asyncio
import argparse
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from vectorstore.manager import VectorStoreManager
from utils.logger import get_logger

logger = get_logger(__name__)


async def main():
    """Main function for Phase 1.6 vector persistence."""
    
    # Get embeddings from Phase 1.5
    embeddings_file = Path("data/index/embeddings.parquet")
    if not embeddings_file.exists():
        logger.error(
            "Embeddings file not found",
            file=str(embeddings_file)
        )
        print("✗ Error: embeddings.parquet not found. Run Phase 1.5 first.")
        return
    
    # Load embeddings
    try:
        import pandas as pd
        df = pd.read_parquet(embeddings_file)
        chunks = df.to_dict('records')
        
        logger.info(
            "Loaded embeddings for Phase 1.6",
            total_chunks=len(chunks)
        )
        
    except Exception as e:
        logger.error(
            "Failed to load embeddings",
            file=str(embeddings_file),
            error=str(e)
        )
        print(f"✗ Error loading embeddings: {str(e)}")
        return
    
    logger.info(
        "Starting Phase 1.6 vector persistence",
        total_chunks=len(chunks)
    )
    
    # Initialize vector store manager
    manager = VectorStoreManager(collection_name="mutual_fund_chunks")
    
    try:
        # Initialize vector store
        initialized = await manager.initialize(persist_directory="data/index/chroma")
        if not initialized:
            print("✗ Failed to initialize vector store")
            return
        
        # Create or update collection
        collection_exists = await manager.vector_store.collection_exists()
        
        if collection_exists:
            print("⚠️  Collection already exists. Updating with new embeddings...")
            # For now, we'll recreate the collection
            # In production, you might want to do incremental updates
            await manager.delete_collection()
        
        # Create new collection
        collection_created = await manager.create_collection(
            metadata={
                "embedding_dim": 384,
                "created_by": "Phase 1.6",
                "description": "Mutual fund chunks with BAAI/bge-small-en embeddings"
            }
        )
        
        if not collection_created:
            print("✗ Failed to create collection")
            return
        
        # Add chunks to vector store
        added_ids = await manager.add_chunks(chunks)
        
        # Get collection statistics
        stats = await manager.get_collection_stats()
        
        # Run retrieval tests
        test_results = await manager.run_retrieval_tests()
        
        # Check for duplicates
        duplicate_cleanup = await manager.cleanup_duplicates(threshold=0.95)
        
        # Health check
        health = await manager.health_check()
        
        # Print summary
        print(f"\n=== Phase 1.6 Vector Persistence Summary ===")
        print(f"Total chunks processed: {len(chunks)}")
        print(f"Successfully added: {len(added_ids)}")
        print(f"Collection name: {stats.get('collection_name', 'unknown')}")
        print(f"Document count: {stats.get('document_count', 0)}")
        print(f"Embedding dimension: {stats.get('embedding_dimension', 0)}")
        print(f"Collection exists: {stats.get('collection_exists', False)}")
        
        print(f"\n=== Retrieval Test Results ===")
        print(f"Total tests: {test_results.get('total_tests', 0)}")
        print(f"Successful tests: {test_results.get('successful_tests', 0)}")
        print(f"Success rate: {test_results.get('success_rate', 0):.1f}%")
        
        # Show sample test results
        test_details = test_results.get('test_results', {})
        for query, result in list(test_details.items())[:3]:  # Show first 3
            if result.get('success', False):
                print(f"  ✓ '{query}': {result.get('results_count', 0)} results")
            else:
                print(f"  ✗ '{query}': {result.get('error', 'Unknown error')}")
        
        print(f"\n=== Duplicate Cleanup Results ===")
        print(f"Duplicates found: {duplicate_cleanup.get('duplicates_found', 0)}")
        print(f"Duplicates removed: {duplicate_cleanup.get('removed_count', 0)}")
        print(f"Similarity threshold: {duplicate_cleanup.get('threshold', 0.95)}")
        
        print(f"\n=== Health Check ===")
        print(f"Vector store status: {health.get('status', 'unknown')}")
        if health.get('status') == 'healthy':
            print("✅ Vector store is healthy")
        else:
            print(f"⚠️  Vector store issues: {health.get('message', 'Unknown')}")
        
        print(f"\n=== Phase 1.6 Complete ===")
        print("Vector persistence completed successfully!")
        print("Ready for Phase 1.7: Scheduler & Automated Refresh Pipeline")
        
    except Exception as e:
        logger.error(
            "Vector persistence failed",
            error=str(e)
        )
        print(f"✗ Error: {str(e)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase 1.6 - Vector DB Persistence")
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--collection-name",
        type=str,
        default="mutual_fund_chunks",
        help="Vector collection name"
    )
    parser.add_argument(
        "--persist-directory",
        type=str,
        default="data/index/chroma",
        help="ChromaDB persist directory"
    )
    parser.add_argument(
        "--test-only",
        action="store_true",
        help="Only run retrieval tests on existing collection"
    )
    parser.add_argument(
        "--cleanup-duplicates",
        action="store_true",
        help="Run duplicate cleanup"
    )
    parser.add_argument(
        "--export-collection",
        type=str,
        help="Export collection to specified file"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)
    
    asyncio.run(main())
