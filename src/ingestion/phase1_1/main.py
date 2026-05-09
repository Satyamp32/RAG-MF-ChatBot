"""
Main entry point for Phase 1.1 - URL Ingestion & Scraping
"""

import asyncio
import argparse
import logging
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.ingestion.phase1_1.fetcher import Fetcher
from src.utils.config import config_manager
from src.utils.logger import get_logger

logger = get_logger(__name__)


async def main():
    """Main function for Phase 1.1 URL ingestion."""
    
    # Get whitelisted URLs
    sources = config_manager.load_sources()
    urls = []
    for scheme in sources.get('schemes', []):
        for source in scheme.get('sources', []):
            urls.append(source['url'])
    
    logger.info(
        "Starting Phase 1.1 URL ingestion",
        url_count=len(urls),
        schemes=len(sources.get('schemes', []))
    )
    
    # Initialize fetcher
    fetcher = Fetcher(timeout=30, max_retries=3)
    
    # Fetch all URLs
    results = await fetcher.fetch_all(urls)
    
    # Save results
    fetcher.save_results(results)
    
    # Print summary
    success_count = sum(1 for r in results if r.is_success)
    failed_urls = [r.url for r in results if not r.is_success]
    
    print(f"\n=== Phase 1.1 URL Ingestion Summary ===")
    print(f"Total URLs: {len(urls)}")
    print(f"Successful: {success_count}")
    print(f"Failed: {len(results) - success_count}")
    
    if failed_urls:
        print(f"\nFailed URLs:")
        for url in failed_urls:
            print(f"  - {url}")
    
    # Validate outputs
    print(f"\n=== Output Validation ===")
    
    # Check if data/raw directory was created
    raw_dir = Path("data/raw")
    if raw_dir.exists():
        print(f"✓ Raw data directory created: {raw_dir}")
        
        # Check for scheme directories
        for scheme in sources.get('schemes', []):
            scheme_dir = raw_dir / scheme['id']
            if scheme_dir.exists():
                html_files = list(scheme_dir.glob("*.html"))
                json_files = list(scheme_dir.glob("*.json"))
                
                if html_files and json_files:
                    print(f"✓ Scheme {scheme['id']}: {len(html_files)} HTML files, {len(json_files)} metadata files")
                else:
                    print(f"✗ Scheme {scheme['id']}: Missing files")
            else:
                print(f"✗ Scheme {scheme['id']}: Directory not created")
    else:
        print(f"✗ Raw data directory not created")
    
    # Check for ETag cache
    etag_file = raw_dir / "etags.json"
    if etag_file.exists():
        print(f"✓ ETag cache created: {etag_file}")
    else:
        print(f"✗ ETag cache not created")
    
    print(f"\n=== Phase 1.1 Complete ===")
    print("Ready for Phase 1.2: HTML Cleaning & Normalization")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase 1.1 - URL Ingestion & Scraping")
    parser.add_argument(
        "--force-refresh",
        action="store_true",
        help="Force refresh of all URLs regardless of ETags"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Request timeout in seconds (default: 30)"
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Maximum number of retries per URL (default: 3)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)
    
    asyncio.run(main())
