"""
Phase 1.7 - Scheduler & Automated Refresh Pipeline

Main entry point for the scheduler and automated refresh pipeline.
Provides command-line interface for manual execution and serves as the
entry point for GitHub Actions workflow.
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.ingestion.phase1_7.scheduler import PipelineOrchestrator
from src.utils.logger import get_logger

logger = get_logger(__name__)


async def main():
    """Main function for Phase 1.7 scheduler and refresh pipeline."""
    
    logger.info(
        "Starting Phase 1.7 - Scheduler & Automated Refresh Pipeline"
    )
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Phase 1.7 - Scheduler & Automated Refresh Pipeline")
    parser.add_argument(
        "--force-refresh",
        action="store_true",
        help="Force full refresh (ignore incremental)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run (no changes, only validation)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--health-check",
        action="store_true",
        help="Run pipeline health check only"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Initialize orchestrator
        orchestrator = PipelineOrchestrator(
            force_refresh=args.force_refresh,
            dry_run=args.dry_run
        )
        
        if args.health_check:
            # Run health check only
            health = await orchestrator.get_pipeline_health()
            
            print(f"\n=== Pipeline Health Check ===")
            print(f"Overall Status: {health.get('overall_status', 'unknown')}")
            print(f"Timestamp: {health.get('timestamp', 'unknown')}")
            
            if health.get('overall_status') == 'healthy':
                print("✅ Pipeline is healthy")
            else:
                print("⚠️  Pipeline health issues detected")
                if 'error' in health:
                    print(f"Error: {health['error']}")
            
            # Show component status
            components = health.get('components', {})
            for component, status in components.items():
                status_icon = "✅" if status.get('exists', False) else "❌"
                print(f"{status_icon} {component}: {status}")
            
            return
        
        # Run full pipeline
        result = await orchestrator.run_full_pipeline()
        
        # Print results
        print(f"\n=== Phase 1.7 Pipeline Results ===")
        print(f"Run ID: {result['run_id']}")
        print(f"Timestamp: {result['timestamp']}")
        print(f"Trigger: {result['trigger']}")
        print(f"Force Refresh: {result['force_refresh']}")
        print(f"Dry Run: {result['dry_run']}")
        print(f"Overall Status: {result['overall_status']}")
        
        if result.get('total_duration_seconds'):
            print(f"Total Duration: {result['total_duration_seconds']:.2f} seconds")
        
        # Phase results
        print(f"\n=== Phase Results ===")
        for phase_result in result.get('phases', []):
            phase_name = phase_result.get('phase', 'unknown')
            status = phase_result.get('status', 'unknown')
            duration = phase_result.get('duration_seconds', 0)
            
            status_icon = "✅" if status == 'completed' else "⚠️" if status == 'skipped' else "❌"
            print(f"{status_icon} Phase {phase_name}: {status} ({duration:.2f}s)")
            
            if phase_result.get('error'):
                print(f"    Error: {phase_result['error']}")
            
            # Show output summary
            output_summary = phase_result.get('output_summary', {})
            if output_summary:
                for key, value in output_summary.items():
                    if key != 'error':
                        print(f"    {key}: {value}")
        
        # Drift detection
        drift_detection = result.get('drift_detection', {})
        print(f"\n=== Content Drift Detection ===")
        print(f"Drift Detected: {drift_detection.get('drift_detected', False)}")
        print(f"Drift Type: {drift_detection.get('drift_type', 'none')}")
        
        if drift_detection.get('changed_schemes'):
            print(f"Changed Schemes: {len(drift_detection['changed_schemes'])}")
            for scheme in drift_detection['changed_schemes'][:3]:  # Show first 3
                print(f"  - {scheme}")
        
        if drift_detection.get('unchanged_schemes'):
            print(f"Unchanged Schemes: {len(drift_detection['unchanged_schemes'])}")
        
        print(f"Reason: {drift_detection.get('reason', 'N/A')}")
        
        # Previous run info
        previous_run = result.get('previous_run_metadata', {})
        print(f"\n=== Previous Run Info ===")
        print(f"Previous Run ID: {previous_run.get('run_id', 'none')}")
        print(f"Last Run: {previous_run.get('last_run', 'none')}")
        
        # Overall success/failure
        if result['overall_status'] == 'completed':
            print(f"\n🎉 Pipeline completed successfully!")
            print(f"Run ID: {result['run_id']} is ready for production use")
        elif result['overall_status'] == 'partial':
            print(f"\n⚠️  Pipeline partially completed")
            print("Some phases may have failed - check logs above")
        else:
            print(f"\n❌ Pipeline failed")
            if result.get('error'):
                print(f"Error: {result['error']}")
            print("Check logs above for detailed failure information")
        
        print(f"\n=== Phase 1.7 Complete ===")
        print("Scheduler & Automated Refresh Pipeline execution completed!")
        
        # Next steps
        if result['overall_status'] == 'completed':
            print("\n📋 Next Steps:")
            print("1. Vector store is ready for Phase 2 (Retrieval Layer)")
            print("2. Monitor GitHub Actions for scheduled runs")
            print("3. Check refresh logs for incremental updates")
            print("4. Set up failure notifications if needed")
        
    except Exception as e:
        logger.error(
            "Phase 1.7 execution failed",
            error=str(e)
        )
        print(f"❌ Fatal Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
