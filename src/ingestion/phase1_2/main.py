"""
Main entry point for Phase 1.2 - HTML Cleaning & Normalization.
"""

import asyncio
import argparse
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ingestion.phase1_2.cleaner import Cleaner
from ingestion.phase1_2.models import CleanedDocument
from utils.config import config_manager
from utils.logger import get_logger

logger = get_logger(__name__)


async def main():
    """Main function for Phase 1.2 HTML cleaning."""
    
    # Get list of extracted files from Phase 1.1
    extracted_dir = Path("data/processed")
    if not extracted_dir.exists():
        logger.error(
            "Extracted data directory not found",
            directory=str(extracted_dir)
        )
        print("✗ Error: data/processed directory not found. Run Phase 1.1 first.")
        return
    
    # Find all extracted JSON files
    extracted_files = list(extracted_dir.glob("*/extracted.json"))
    
    if not extracted_files:
        logger.error("No extracted files found")
        print("✗ Error: No extracted files found in data/processed/")
        return
    
    logger.info(
        "Starting Phase 1.2 HTML cleaning",
        extracted_files_count=len(extracted_files)
    )
    
    # Initialize cleaner
    cleaner = Cleaner()
    
    # Process each extracted file
    cleaned_results = []
    
    for extracted_file in extracted_files:
        try:
            scheme_id = extracted_file.parent.name
            
            # Load extracted data
            with open(extracted_file, 'r', encoding='utf-8') as f:
                import json
                extracted_data = json.load(f)
            
            # Clean the document
            cleaned_document = cleaner.clean_document(extracted_data, scheme_id)
            
            # Save cleaned document
            cleaned_file = extracted_file.parent / "cleaned.json"
            with open(cleaned_file, 'w', encoding='utf-8') as f:
                json.dump(cleaned_document.dict(), f, indent=2, default=str)
            
            cleaned_results.append({
                "scheme_id": scheme_id,
                "extracted_file": str(extracted_file),
                "cleaned_file": str(cleaned_file),
                "health": cleaned_document.get("extraction_health", "unknown"),
                "sections_count": len(cleaned_document.get("sections", []))
            })
            
            logger.info(
                "Cleaned document",
                scheme_id=scheme_id,
                sections_count=len(cleaned_document.get("sections", [])),
                health=cleaned_document.get("extraction_health", "unknown")
            )
            
        except Exception as e:
            logger.error(
                "Failed to clean document",
                scheme_id=extracted_file.parent.name,
                file=str(extracted_file),
                error=str(e)
            )
            print(f"✗ Error cleaning {extracted_file}: {str(e)}")
    
    # Print summary
    print(f"\n=== Phase 1.2 HTML Cleaning Summary ===")
    print(f"Total extracted files: {len(extracted_files)}")
    print(f"Successfully cleaned: {len(cleaned_results)}")
    
    if cleaned_results:
        health_counts = {}
        for result in cleaned_results:
            health = result.get("health", "unknown")
            health_counts[health] = health_counts.get(health, 0) + 1
        
        print(f"\nHealth distribution:")
        for health, count in health_counts.items():
            print(f"  {health}: {count}")
        
        print(f"\n=== Phase 1.2 Complete ===")
        print("Ready for Phase 1.3: Structured Metadata Extraction")
    else:
        print("✗ No documents were successfully cleaned")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase 1.2 - HTML Cleaning & Normalization")
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
    
    args = parser.parse_args()
    
    if args.verbose:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)
    
    asyncio.run(main())
