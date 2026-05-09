#!/usr/bin/env python3
"""
Pipeline Runner Script for GitHub Actions

Handles pipeline execution with proper error handling and output parsing.
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ingestion.phase1_7.scheduler import PipelineOrchestrator

async def main():
    """Main pipeline execution function."""
    
    # Get environment variables
    run_id = os.getenv('RUN_ID')
    timestamp = os.getenv('TIMESTAMP')
    force_refresh = os.getenv('FORCE_REFRESH', 'false').lower() == 'true'
    dry_run = os.getenv('DRY_RUN', 'false').lower() == 'true'
    previous_run_json = os.getenv('PREVIOUS_RUN', '{}')
    
    if previous_run_json and previous_run_json != '{}':
        previous_run = json.loads(previous_run_json)
    else:
        previous_run = {}
    
    print(f"Starting pipeline with run_id: {run_id}")
    print(f"Force refresh: {force_refresh}")
    print(f"Dry run: {dry_run}")
    
    # Initialize orchestrator
    orchestrator = PipelineOrchestrator(
        force_refresh=force_refresh,
        dry_run=dry_run
    )
    
    # Run pipeline
    result = await orchestrator.run_pipeline()
    
    # Extract outputs for GitHub Actions
    phases = result.get('phases', {})
    completed_phases = sum(1 for phase in phases.values() if phase.get('status') == 'completed')
    
    # Count chunks
    chunk_count = 0
    if os.path.exists('data/processed/chunks.json'):
        with open('data/processed/chunks.json', 'r') as f:
            chunk_count = sum(1 for line in f if line.strip())
    
    # Check embeddings
    embeddings_generated = 0
    if os.path.exists('data/index/embeddings.parquet'):
        try:
            import pandas as pd
            df = pd.read_parquet('data/index/embeddings.parquet')
            embeddings_generated = len(df)
        except:
            embeddings_generated = 0
    
    # Output GitHub Actions variables
    print(f"phases_completed={completed_phases}")
    print(f"chunks_processed={chunk_count}")
    print(f"embeddings_generated={embeddings_generated}")
    print(f"pipeline_success={result.get('execution_summary', 'No summary') != 'No summary'}")
    print(f"execution_time={datetime.now(timezone.utc).isoformat()}")

if __name__ == "__main__":
    asyncio.run(main())
