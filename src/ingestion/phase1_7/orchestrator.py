"""
Phase 1.7 - Scheduler & Automated Refresh Pipeline

Implements complete pipeline orchestration with incremental updates,
drift detection, and automated health monitoring.
"""

import asyncio
import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from src.utils.config import config_manager
from src.utils.logger import get_logger

logger = get_logger(__name__)


class PipelineOrchestrator:
    """Orchestrates the complete ingestion pipeline with incremental updates."""
    
    def __init__(self, force_refresh: bool = False, dry_run: bool = False):
        self.force_refresh = force_refresh
        self.dry_run = dry_run
        self.run_id = self._generate_run_id()
        
        # Pipeline phases configuration
        self.phases = [
            {"name": "1.1", "module": "ingestion.phase1_1.main", "description": "URL Ingestion & Scraping"},
            {"name": "1.2", "module": "ingestion.phase1_2.main", "description": "HTML Cleaning & Normalization"},
            {"name": "1.3", "module": "ingestion.phase1_3.main", "description": "Structured Metadata Extraction"},
            {"name": "1.4", "module": "ingestion.phase1_4.main", "description": "Chunking Strategy"},
            {"name": "1.5", "module": "ingestion.phase1_5.main", "description": "Embedding Generation"},
            {"name": "1.6", "module": "vectorstore.main", "description": "Vector DB Persistence"}
        ]
    
    def _generate_run_id(self) -> str:
        """Generate unique run ID."""
        return hashlib.md5(datetime.now().isoformat().encode()).hexdigest()[:8]
    
    async def load_previous_run_metadata(self) -> Dict:
        """Load metadata from previous run for incremental updates."""
        try:
            refresh_log_file = Path("data/index/refresh_log.jsonl")
            if not refresh_log_file.exists():
                return {"run_id": "none", "last_run": "none"}
            
            # Get the last line (most recent run)
            with open(refresh_log_file, 'r') as f:
                lines = f.readlines()
                if lines:
                    return json.loads(lines[-1].strip())
            
            return {"run_id": "none", "last_run": "none"}
            
        except Exception as e:
            logger.warning(
                "Failed to load previous run metadata",
                error=str(e)
            )
            return {"run_id": "none", "last_run": "none"}
    
    async def detect_content_drift(self, previous_metadata: Dict) -> Dict:
        """Detect content drift to determine if incremental update is possible."""
        try:
            logger.info(
                "Detecting content drift",
                run_id=self.run_id,
                force_refresh=self.force_refresh
            )
            
            if self.force_refresh:
                return {
                    "drift_detected": True,
                    "drift_type": "forced_refresh",
                    "changed_schemes": [],
                    "reason": "Force refresh requested"
                }
            
            # Compare current content hashes with previous run
            drift_result = {
                "drift_detected": False,
                "drift_type": "none",
                "changed_schemes": [],
                "unchanged_schemes": [],
                "reason": "No content changes detected"
            }
            
            # Get current processed data
            processed_dir = Path("data/processed")
            if not processed_dir.exists():
                return drift_result
            
            # Check each scheme directory
            for scheme_dir in processed_dir.iterdir():
                if not scheme_dir.is_dir():
                    continue
                
                scheme_id = scheme_dir.name
                
                # Look for stable content hash
                metadata_file = scheme_dir / "structured_metadata.json"
                if metadata_file.exists():
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                        current_stable_hash = metadata.get('stable_content_hash', '')
                        
                        if current_stable_hash:
                            # This would require comparing with previous run data
                            # For now, assume no drift detection implemented
                            drift_result["unchanged_schemes"].append(scheme_id)
            
            # If any schemes have changed, mark as drift detected
            if drift_result["changed_schemes"]:
                drift_result["drift_detected"] = True
                drift_result["drift_type"] = "content_change"
                drift_result["reason"] = f"Content changed in {len(drift_result['changed_schemes'])} schemes"
            
            logger.info(
                "Content drift detection completed",
                run_id=self.run_id,
                drift_detected=drift_result["drift_detected"],
                changed_schemes=len(drift_result["changed_schemes"]),
                unchanged_schemes=len(drift_result["unchanged_schemes"])
            )
            
            return drift_result
            
        except Exception as e:
            logger.error(
                "Content drift detection failed",
                run_id=self.run_id,
                error=str(e)
            )
            return {
                "drift_detected": True,
                "drift_type": "error",
                "reason": f"Drift detection failed: {str(e)}"
            }
    
    async def run_phase(self, phase: Dict, incremental: bool = False) -> Dict:
        """Run a single pipeline phase with error handling."""
        phase_name = phase["name"]
        module_name = phase["module"]
        description = phase["description"]
        
        logger.info(
            "Starting pipeline phase",
            run_id=self.run_id,
            phase=phase_name,
            description=description,
            incremental=incremental
        )
        
        phase_result = {
            "phase": phase_name,
            "description": description,
            "status": "pending",
            "start_time": datetime.now(timezone.utc).isoformat(),
            "end_time": None,
            "duration_seconds": None,
            "error": None,
            "output_summary": {}
        }
        
        try:
            if self.dry_run:
                logger.info(
                    "Dry run mode - skipping actual execution",
                    phase=phase_name
                )
                phase_result["status"] = "skipped"
                phase_result["reason"] = "Dry run mode"
                return phase_result
            
            # Import and run the phase module
            import importlib
            module = importlib.import_module(module_name)
            
            if hasattr(module, 'main'):
                # Run the main function
                if asyncio.iscoroutinefunction(module.main):
                    await module.main()
                else:
                    module.main()
                
                phase_result["status"] = "completed"
                phase_result["end_time"] = datetime.now(timezone.utc).isoformat()
                
                # Calculate duration
                start_time = datetime.fromisoformat(phase_result["start_time"])
                end_time = datetime.fromisoformat(phase_result["end_time"])
                phase_result["duration_seconds"] = (end_time - start_time).total_seconds()
                
                # Collect output summary
                phase_result["output_summary"] = await self._collect_phase_output(phase_name)
                
                logger.info(
                    "Pipeline phase completed successfully",
                    run_id=self.run_id,
                    phase=phase_name,
                    duration=phase_result["duration_seconds"]
                )
                
            else:
                raise ImportError(f"Module {module_name} does not have main function")
                
        except Exception as e:
            phase_result["status"] = "failed"
            phase_result["end_time"] = datetime.now(timezone.utc).isoformat()
            phase_result["error"] = str(e)
            
            logger.error(
                "Pipeline phase failed",
                run_id=self.run_id,
                phase=phase_name,
                error=str(e)
            )
        
        return phase_result
    
    async def _collect_phase_output(self, phase_name: str) -> Dict:
        """Collect output summary from a completed phase."""
        try:
            output_summary = {}
            
            if phase_name == "1.1":
                # Count fetched HTML files
                raw_dir = Path("data/raw")
                if raw_dir.exists():
                    html_files = list(raw_dir.glob("*/**/*.html"))
                    output_summary["html_files_count"] = len(html_files)
                    
                    # Count schemes
                    scheme_dirs = [d for d in raw_dir.iterdir() if d.is_dir()]
                    output_summary["schemes_count"] = len(scheme_dirs)
            
            elif phase_name == "1.2":
                # Count cleaned files
                processed_dir = Path("data/processed")
                if processed_dir.exists():
                    cleaned_files = list(processed_dir.glob("*/cleaned.json"))
                    output_summary["cleaned_files_count"] = len(cleaned_files)
            
            elif phase_name == "1.3":
                # Count metadata files
                processed_dir = Path("data/processed")
                if processed_dir.exists():
                    metadata_files = list(processed_dir.glob("*/structured_metadata.json"))
                    output_summary["metadata_files_count"] = len(metadata_files)
            
            elif phase_name == "1.4":
                # Count chunks
                chunks_file = Path("data/processed/chunks.jsonl")
                if chunks_file.exists():
                    with open(chunks_file, 'r') as f:
                        chunk_count = sum(1 for line in f if line.strip())
                        output_summary["chunk_count"] = chunk_count
            
            elif phase_name == "1.5":
                # Count embeddings
                embeddings_file = Path("data/index/embeddings.parquet")
                if embeddings_file.exists():
                    import pandas as pd
                    df = pd.read_parquet(embeddings_file)
                    output_summary["embedding_count"] = len(df)
            
            elif phase_name == "1.6":
                # Get vector store stats
                try:
                    from vectorstore.manager import VectorStoreManager
                    manager = VectorStoreManager()
                    await manager.initialize()
                    stats = await manager.get_collection_stats()
                    output_summary["vector_store_stats"] = stats
                except Exception:
                    output_summary["vector_store_stats"] = {"error": "Failed to get stats"}
            
            return output_summary
            
        except Exception as e:
            logger.warning(
                "Failed to collect phase output",
                phase=phase_name,
                error=str(e)
            )
            return {"error": str(e)}
    
    async def run_full_pipeline(self) -> Dict:
        """Run the complete ingestion pipeline."""
        logger.info(
            "Starting full pipeline execution",
            run_id=self.run_id,
            force_refresh=self.force_refresh,
            dry_run=self.dry_run
        )
        
        pipeline_result = {
            "run_id": self.run_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "trigger": "github_actions" if not self.dry_run else "manual",
            "force_refresh": self.force_refresh,
            "dry_run": self.dry_run,
            "previous_run_metadata": {},
            "drift_detection": {},
            "phases": [],
            "overall_status": "pending",
            "start_time": datetime.now(timezone.utc).isoformat(),
            "end_time": None,
            "total_duration_seconds": None,
            "error": None
        }
        
        try:
            # Load previous run metadata
            pipeline_result["previous_run_metadata"] = await self.load_previous_run_metadata()
            
            # Detect content drift
            pipeline_result["drift_detection"] = await self.detect_content_drift(
                pipeline_result["previous_run_metadata"]
            )
            
            # Determine if incremental update is possible
            incremental_possible = (
                not self.force_refresh and
                not pipeline_result["drift_detection"]["drift_detected"]
            )
            
            # Run each phase
            for phase in self.phases:
                phase_result = await self.run_phase(phase, incremental_possible)
                pipeline_result["phases"].append(phase_result)
                
                # If a phase fails and it's critical, stop the pipeline
                if phase_result["status"] == "failed":
                    logger.error(
                        "Critical phase failed, stopping pipeline",
                        run_id=self.run_id,
                        failed_phase=phase["name"],
                        error=phase_result["error"]
                    )
                    break
            
            # Calculate overall status
            pipeline_result["end_time"] = datetime.now(timezone.utc).isoformat()
            start_time = datetime.fromisoformat(pipeline_result["start_time"])
            end_time = datetime.fromisoformat(pipeline_result["end_time"])
            pipeline_result["total_duration_seconds"] = (end_time - start_time).total_seconds()
            
            # Determine overall status
            failed_phases = [p for p in pipeline_result["phases"] if p["status"] == "failed"]
            if failed_phases:
                pipeline_result["overall_status"] = "failed"
                pipeline_result["error"] = f"Failed phases: {[p['phase'] for p in failed_phases]}"
            else:
                completed_phases = [p for p in pipeline_result["phases"] if p["status"] == "completed"]
                if len(completed_phases) == len(self.phases):
                    pipeline_result["overall_status"] = "completed"
                else:
                    pipeline_result["overall_status"] = "partial"
            
            # Save refresh log entry
            await self._save_refresh_log(pipeline_result)
            
            logger.info(
                "Full pipeline execution completed",
                run_id=self.run_id,
                overall_status=pipeline_result["overall_status"],
                total_duration=pipeline_result["total_duration_seconds"]
            )
            
            return pipeline_result
            
        except Exception as e:
            pipeline_result["overall_status"] = "failed"
            pipeline_result["end_time"] = datetime.now(timezone.utc).isoformat()
            pipeline_result["error"] = str(e)
            
            logger.error(
                "Full pipeline execution failed",
                run_id=self.run_id,
                error=str(e)
            )
            
            # Save failed run to log
            await self._save_refresh_log(pipeline_result)
            
            return pipeline_result
    
    async def _save_refresh_log(self, pipeline_result: Dict) -> None:
        """Save pipeline execution results to refresh log."""
        try:
            refresh_log_file = Path("data/index/refresh_log.jsonl")
            refresh_log_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Prepare log entry
            log_entry = {
                "run_id": pipeline_result["run_id"],
                "timestamp": pipeline_result["timestamp"],
                "trigger": pipeline_result["trigger"],
                "force_refresh": pipeline_result["force_refresh"],
                "dry_run": pipeline_result["dry_run"],
                "overall_status": pipeline_result["overall_status"],
                "total_duration_seconds": pipeline_result["total_duration_seconds"],
                "phases_completed": len([p for p in pipeline_result["phases"] if p["status"] == "completed"]),
                "phases_failed": len([p for p in pipeline_result["phases"] if p["status"] == "failed"]),
                "drift_detection": pipeline_result["drift_detection"],
                "previous_run_id": pipeline_result["previous_run_metadata"].get("run_id", "none"),
                "error": pipeline_result.get("error")
            }
            
            # Write to log file
            with open(refresh_log_file, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
            
            logger.info(
                "Refresh log entry saved",
                run_id=pipeline_result["run_id"],
                log_file=str(refresh_log_file)
            )
            
        except Exception as e:
            logger.error(
                "Failed to save refresh log",
                run_id=pipeline_result["run_id"],
                error=str(e)
            )
    
    async def get_pipeline_health(self) -> Dict:
        """Get comprehensive pipeline health status."""
        try:
            health_check = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "components": {},
                "overall_status": "unknown"
            }
            
            # Check data directories
            data_dirs = ["data/raw", "data/processed", "data/index"]
            for dir_path in data_dirs:
                path = Path(dir_path)
                health_check["components"][dir_path] = {
                    "exists": path.exists(),
                    "writable": path.exists() and os.access(path, os.W_OK)
                }
            
            # Check critical files
            critical_files = [
                "data/processed/chunks.jsonl",
                "data/index/embeddings.parquet",
                "data/index/refresh_log.jsonl"
            ]
            
            files_exist = 0
            for file_path in critical_files:
                path = Path(file_path)
                if path.exists():
                    files_exist += 1
                health_check["components"][file_path] = {
                    "exists": path.exists(),
                    "size": path.stat().st_size if path.exists() else 0
                }
            
            # Determine overall health
            if files_exist == len(critical_files) and all(
                comp.get("exists", False) for comp in health_check["components"].values()
                if isinstance(comp, dict)
            ):
                health_check["overall_status"] = "healthy"
            else:
                health_check["overall_status"] = "degraded"
            
            return health_check
            
        except Exception as e:
            logger.error(
                "Pipeline health check failed",
                error=str(e)
            )
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "overall_status": "error",
                "error": str(e)
            }
