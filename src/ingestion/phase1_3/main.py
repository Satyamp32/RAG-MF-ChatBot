"""
Main entry point for Phase 1.3 - Structured Mutual Fund Metadata Extraction.
"""

import asyncio
import argparse
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ingestion.phase1_3.extractor import MutualFundExtractor
from utils.config import config_manager
from utils.logger import get_logger

logger = get_logger(__name__)


async def main():
    """Main function for Phase 1.3 metadata extraction."""
    
    # Get list of cleaned files from Phase 1.2
    cleaned_dir = Path("data/processed")
    if not cleaned_dir.exists():
        logger.error(
            "Cleaned data directory not found",
            directory=str(cleaned_dir)
        )
        print("✗ Error: data/processed directory not found. Run Phase 1.2 first.")
        return
    
    # Find all cleaned JSON files
    cleaned_files = list(cleaned_dir.glob("*/cleaned.json"))
    
    if not cleaned_files:
        logger.error("No cleaned files found")
        print("✗ Error: No cleaned files found in data/processed/")
        return
    
    logger.info(
        "Starting Phase 1.3 metadata extraction",
        cleaned_files_count=len(cleaned_files)
    )
    
    # Initialize extractor
    extractor = MutualFundExtractor()
    
    # Process each cleaned file
    extracted_results = []
    
    for cleaned_file in cleaned_files:
        try:
            scheme_id = cleaned_file.parent.name
            
            # Load cleaned data
            with open(cleaned_file, 'r', encoding='utf-8') as f:
                import json
                cleaned_data = json.load(f)
            
            # Extract structured metadata
            metadata = extractor.extract_fund_metadata(cleaned_data, scheme_id)
            
            # Save structured metadata
            metadata_file = cleaned_file.parent / "structured_metadata.json"
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, default=str)
            
            extracted_results.append({
                "scheme_id": scheme_id,
                "cleaned_file": str(cleaned_file),
                "metadata_file": str(metadata_file),
                "health": metadata.get("extraction_health", "unknown"),
                "nav_found": bool(metadata.get("nav_details", {}).get("current_nav")),
                "expense_ratio_found": bool(metadata.get("financial_metrics", {}).get("expense_ratio")),
                "risk_level_found": metadata.get("risk_info", {}).get("risk_level") is not None,
                "category_found": metadata.get("category_info", {}).get("category") is not None,
                "manager_found": metadata.get("manager_info", {}).get("name") is not None,
                "sections_count": len(metadata.get("sections", [])),
                "extraction_stats": metadata.get("extraction_stats", {})
            })
            
            logger.info(
                "Metadata extracted",
                scheme_id=scheme_id,
                sections_count=len(metadata.get("sections", [])),
                health=metadata.get("extraction_health", "unknown")
            )
            
        except Exception as e:
            logger.error(
                "Failed to extract metadata",
                scheme_id=cleaned_file.parent.name,
                file=str(cleaned_file),
                error=str(e)
            )
            print(f"✗ Error extracting metadata from {cleaned_file}: {str(e)}")
    
    # Print summary
    print(f"\n=== Phase 1.3 Metadata Extraction Summary ===")
    print(f"Total cleaned files: {len(cleaned_files)}")
    print(f"Successfully extracted: {len(extracted_results)}")
    
    if extracted_results:
        health_counts = {}
        for result in extracted_results:
            health = result.get("health", "unknown")
            health_counts[health] = health_counts.get(health, 0) + 1
        
        print(f"\nHealth distribution:")
        for health, count in health_counts.items():
            print(f"  {health}: {count}")
        
        # Field extraction success rates
        success_rates = {
            "nav_extraction": sum(1 for r in extracted_results if r.get("nav_found")),
            "expense_ratio_extraction": sum(1 for r in extracted_results if r.get("expense_ratio_found")),
            "risk_extraction": sum(1 for r in extracted_results if r.get("risk_level_found")),
            "category_extraction": sum(1 for r in extracted_results if r.get("category_found")),
            "manager_extraction": sum(1 for r in extracted_results if r.get("manager_found"))
        }
        
        print(f"\nField extraction success rates:")
        for field, success_count in success_rates.items():
            success_rate = (success_count / len(extracted_results)) * 100
            print(f"  {field}: {success_count}/{len(extracted_results)} ({success_rate:.1f}%)")
        
        print(f"\n=== Phase 1.3 Complete ===")
        print("Structured metadata extraction completed successfully!")
        print("Ready for Phase 1.4: Chunking Strategy")
    else:
        print("✗ No metadata was successfully extracted")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase 1.3 - Structured Mutual Fund Metadata Extraction")
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
        "--validate-only",
        action="store_true",
        help="Only validate existing metadata files"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)
    
    asyncio.run(main())
