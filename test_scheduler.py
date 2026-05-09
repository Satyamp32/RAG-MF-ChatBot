#!/usr/bin/env python3
"""
Simple scheduler test to validate Phase 1.7 implementation.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.ingestion.phase1_7.scheduler import PipelineOrchestrator

async def test_scheduler():
    """Test scheduler functionality."""
    print("=== Testing Phase 1.7 Scheduler ===")
    
    # Test with dry run
    orchestrator = PipelineOrchestrator(
        force_refresh=False,
        dry_run=True
    )
    
    print("✅ Scheduler initialized successfully")
    print(f"Run ID: {orchestrator.run_id}")
    print(f"Force refresh: {orchestrator.force_refresh}")
    print(f"Dry run: {orchestrator.dry_run}")
    
    # Test health check
    health = orchestrator.get_pipeline_health()
    print(f"Pipeline health: {health['status']}")
    print(f"Health message: {health['message']}")
    
    # Test pipeline execution (dry run)
    print("\n=== Running Pipeline (Dry Run) ===")
    result = await orchestrator.run_pipeline()
    
    if result:
        print("✅ Pipeline executed successfully")
        print(f"Execution summary: {result.get('execution_summary', 'No summary')}")
        print(f"Completed phases: {result['stats']['completed_phases']}")
        print(f"Total phases: {result['stats']['total_phases']}")
    else:
        print("❌ Pipeline execution failed")
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    asyncio.run(test_scheduler())
