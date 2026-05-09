"""
Main entry point for Phase 1.4 - Chunking Strategy.
"""

import asyncio
import argparse
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ingestion.phase1_4.chunker import Chunker
from ingestion.phase1_4.models import ChunkingConfig
from utils.logger import get_logger

logger = get_logger(__name__)


async def main():
    """Main function for Phase 1.4 chunking."""
    
    # Get list of cleaned files from Phase 1.3
    cleaned_dir = Path("data/processed")
    if not cleaned_dir.exists():
        logger.error(
            "Cleaned data directory not found",
            directory=str(cleaned_dir)
        )
        print("✗ Error: data/processed directory not found. Run Phase 1.3 first.")
        return
    
    # Find all cleaned JSON files
    cleaned_files = list(cleaned_dir.glob("*/cleaned.json"))
    
    if not cleaned_files:
        logger.error("No cleaned files found")
        print("✗ Error: No cleaned files found in data/processed/")
        return
    
    logger.info(
        "Starting Phase 1.4 chunking",
        cleaned_files_count=len(cleaned_files)
    )
    
    # Initialize chunker with optimized configuration
    config = ChunkingConfig(
        soft_cap=250,
        hard_cap=400,
        overlap=30,
        preserve_financial_context=True,
        semantic_chunking=True,
        numeric_fact_protection=True,
        section_boundary_preservation=True
    )
    
    chunker = Chunker(config)
    
    # Load all cleaned documents
    cleaned_documents = []
    
    for cleaned_file in cleaned_files:
        try:
            scheme_id = cleaned_file.parent.name
            
            # Load cleaned data
            with open(cleaned_file, 'r', encoding='utf-8') as f:
                import json
                cleaned_data = json.load(f)
            
            cleaned_documents.append(cleaned_data)
            
        except Exception as e:
            logger.error(
                "Failed to load cleaned document",
                scheme_id=cleaned_file.parent.name,
                file=str(cleaned_file),
                error=str(e)
            )
            print(f"✗ Error loading {cleaned_file}: {str(e)}")
    
    # Process all documents
    chunks = chunker.chunk_documents(cleaned_documents)
    
    # Save chunks
    chunker.save_chunks(chunks)
    
    # Print summary
    print(f"\n=== Phase 1.4 Chunking Summary ===")
    print(f"Total documents: {len(cleaned_documents)}")
    print(f"Total chunks: {len(chunks)}")
    
    # Analyze chunking results
    if chunks:
        # Calculate statistics
        total_tokens = sum(chunk.get("token_count", 0) for chunk in chunks)
        avg_chunk_size = total_tokens / len(chunks) if chunks else 0
        
        # Size distribution
        size_distribution = {}
        for chunk in chunks:
            size_category = "small" if chunk.get("token_count", 0) < 100 else "medium" if chunk.get("token_count", 0) < 200 else "large"
            size_distribution[size_category] = size_distribution.get(size_category, 0) + 1
        
        print(f"\nChunk size distribution:")
        for size_cat, count in size_distribution.items():
            print(f"  {size_cat}: {count}")
        
        print(f"\nAverage chunk size: {avg_chunk_size:.1f} tokens")
        
        # Section coverage
        sections_processed = set()
        for chunk in chunks:
            sections_processed.add(chunk.get("section", ""))
        
        print(f"\nTotal unique sections: {len(sections_processed)}")
        
        # Validate chunking strategy
        oversized_chunks = [c for c in chunks if c.get("token_count", 0) > 400]
        undersized_chunks = [c for c in chunks if c.get("token_count", 0) < 20]
        
        if oversized_chunks:
            print(f"\n⚠️  Oversized chunks: {len(oversized_chunks)}")
        if undersized_chunks:
            print(f"\n⚠️  Undersized chunks: {len(undersized_chunks)}")
        
        if not oversized_chunks and not undersized_chunks:
            print("\n✅ Chunking strategy validated successfully")
    
    print(f"\n=== Phase 1.4 Complete ===")
    print("Chunking strategy completed successfully!")
    print("Ready for Phase 1.5: Embedding Generation")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase 1.4 - Chunking Strategy")
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--scheme-id",
        type=str,
        help="Process only specific scheme ID"
    )
    parser.add_argument(
        "--soft-cap",
        type=int,
        default=250,
        help="Soft chunk size cap in tokens"
    )
    parser.add_argument(
        "--hard-cap",
        type=int,
        default=400,
        help="Hard chunk size cap in tokens"
    )
    parser.add_argument(
        "--overlap",
        type=int,
        default=30,
        help="Chunk overlap in tokens"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)
    
    asyncio.run(main())
