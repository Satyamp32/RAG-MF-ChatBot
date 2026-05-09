"""
Main entry point for Phase 1.5 - Embedding Generation.
"""

import asyncio
import argparse
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ingestion.phase1_5.embedder import Embedder
from ingestion.phase1_5.models import EmbeddingConfig
from utils.logger import get_logger

logger = get_logger(__name__)


async def main():
    """Main function for Phase 1.5 embedding generation."""
    
    # Get chunks from Phase 1.4
    chunks_file = Path("data/processed/chunks.jsonl")
    if not chunks_file.exists():
        logger.error(
            "Chunks file not found",
            file=str(chunks_file)
        )
        print("✗ Error: chunks.jsonl not found. Run Phase 1.4 first.")
        return
    
    # Load chunks
    chunks = []
    try:
        with open(chunks_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    chunks.append(json.loads(line))
    except Exception as e:
        logger.error(
            "Failed to load chunks",
            file=str(chunks_file),
            error=str(e)
        )
        print(f"✗ Error loading chunks: {str(e)}")
        return
    
    logger.info(
        "Starting Phase 1.5 embedding generation",
        total_chunks=len(chunks)
    )
    
    # Initialize embedder with optimized configuration
    config = EmbeddingConfig(
        model_name="BAAI/bge-small-en",
        embedding_dim=384,
        batch_size=32,
        normalize_embeddings=True,
        prepend_scheme_name=True,
        max_retries=3,
        retry_delay=1.0,
        retry_backoff=2.0
    )
    
    embedder = Embedder(
        model_name=config.model_name,
        batch_size=config.batch_size
    )
    
    try:
        # Generate embeddings
        embedded_chunks = embedder.embed_chunks(chunks)
        
        # Save embeddings
        embedder.save_embeddings(embedded_chunks)
        
        # Print summary
        print(f"\n=== Phase 1.5 Embedding Generation Summary ===")
        print(f"Total chunks: {len(chunks)}")
        print(f"Successfully embedded: {len(embedded_chunks)}")
        print(f"Embedding model: {config.model_name}")
        print(f"Embedding dimension: {config.embedding_dim}")
        print(f"Batch size: {config.batch_size}")
        
        # Calculate statistics
        if embedded_chunks:
            total_tokens = sum(chunk.get("token_count", 0) for chunk in embedded_chunks)
            avg_tokens_per_chunk = total_tokens / len(embedded_chunks)
            
            print(f"\nEmbedding Statistics:")
            print(f"  Total tokens processed: {total_tokens}")
            print(f"  Average tokens per chunk: {avg_tokens_per_chunk:.1f}")
            print(f"  Embeddings per batch: {config.batch_size}")
            print(f"  Total batches processed: {(len(embedded_chunks) + config.batch_size - 1) // config.batch_size}")
        
        print(f"\n=== Phase 1.5 Complete ===")
        print("Embedding generation completed successfully!")
        print("Ready for Phase 1.6: Vector DB Persistence")
        
    except Exception as e:
        logger.error(
            "Embedding generation failed",
            error=str(e)
        )
        print(f"✗ Error: {str(e)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase 1.5 - Embedding Generation")
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--model-name",
        type=str,
        default="BAAI/bge-small-en",
        help="Embedding model name"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Batch size for embedding generation"
    )
    parser.add_argument(
        "--embedding-dim",
        type=int,
        default=384,
        help="Embedding dimension"
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate existing embeddings"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)
    
    asyncio.run(main())
