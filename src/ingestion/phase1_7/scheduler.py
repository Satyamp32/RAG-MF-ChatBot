"""
Pipeline Orchestrator for Phase 1.7

Implements the PipelineOrchestrator class that orchestrates the complete
ingestion pipeline with incremental updates, failure handling,
and comprehensive logging.
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import logging

from src.utils.logger import get_logger
from src.utils.config import config_manager

logger = get_logger(__name__)


class PipelineOrchestrator:
    """Orchestrates the complete ingestion pipeline with incremental updates."""
    
    def __init__(self, force_refresh: bool = False, dry_run: bool = False):
        self.force_refresh = force_refresh
        self.dry_run = dry_run
        self.run_id = self._generate_run_id()
        self.start_time = datetime.now(timezone.utc)
        
        # Phase tracking
        self.phases = {
            '1.1': {'status': 'pending', 'start_time': None, 'end_time': None, 'duration': None, 'output_summary': None},
            '1.2': {'status': 'pending', 'start_time': None, 'end_time': None, 'duration': None, 'output_summary': None},
            '1.3': {'status': 'pending', 'start_time': None, 'end_time': None, 'duration': None, 'output_summary': None},
            '1.4': {'status': 'pending', 'start_time': None, 'end_time': None, 'duration': None, 'output_summary': None},
            '1.5': {'status': 'pending', 'start_time': None, 'end_time': None, 'duration': None, 'output_summary': None},
            '1.6': {'status': 'pending', 'start_time': None, 'end_time': None, 'duration': None, 'output_summary': None},
            '1.7': {'status': 'pending', 'start_time': None, 'end_time': None, 'duration': None, 'output_summary': None}
        }
        
        # Previous run metadata
        self.previous_run = self._load_previous_run_metadata()
        
        # Phase outputs
        self.phase_outputs = {}
        
        # Pipeline statistics
        self.stats = {
            'total_phases': 7,
            'completed_phases': 0,
            'failed_phases': 0,
            'total_duration': 0.0,
            'files_processed': 0,
            'data_size_mb': 0.0
        }
    
    def _generate_run_id(self) -> str:
        """Generate unique run identifier."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        return f"run_{timestamp}"
    
    def _load_previous_run_metadata(self) -> Optional[Dict[str, Any]]:
        """Load metadata from previous run."""
        try:
            refresh_log_path = Path("data/logs/refresh_log.json")
            if refresh_log_path.exists():
                with open(refresh_log_path, 'r') as f:
                    logs = json.load(f)
                    if logs:
                        return logs[-1]  # Return most recent run
        except Exception as e:
            logger.warning(f"Failed to load previous run metadata: {e}")
            return None
    
    def _save_refresh_log(self) -> None:
        """Save refresh log entry."""
        try:
            refresh_log_path = Path("data/logs")
            refresh_log_path.mkdir(parents=True, exist_ok=True)
            
            log_entry = {
                'run_id': self.run_id,
                'timestamp': self.start_time.isoformat(),
                'force_refresh': self.force_refresh,
                'dry_run': self.dry_run,
                'phases': self.phases,
                'stats': self.stats,
                'previous_run': self.previous_run
            }
            
            # Load existing logs
            logs = []
            if Path("data/logs/refresh_log.json").exists():
                with open("data/logs/refresh_log.json", 'r') as f:
                    logs = json.load(f)
            
            logs.append(log_entry)
            
            # Keep only last 100 runs
            logs = logs[-100:]
            
            with open("data/logs/refresh_log.json", 'w') as f:
                json.dump(logs, f, indent=2)
                
            logger.info(f"Refresh log saved: {self.run_id}")
            
        except Exception as e:
            logger.error(f"Failed to save refresh log: {e}")
    
    def _get_phase_command(self, phase_name: str, python_path: str) -> List[str]:
        """Get command to run a specific phase."""
        return [sys.executable, "-m", python_path, phase_name, "main.py"]
    
    def _run_phase(self, phase_name: str, phase_num: str) -> bool:
        """Run a single phase with error handling."""
        phase_start_time = datetime.now(timezone.utc)
        
        try:
            logger.info(f"Starting Phase {phase_num} ({phase_name})")
            
            # Update phase status
            self.phases[phase_num]['status'] = 'running'
            self.phases[phase_num]['start_time'] = phase_start_time.isoformat()
            
            # Get phase command
            python_path = f"src/ingestion/phase{phase_num}"
            command = self._get_phase_command(phase_name, python_path)
            
            # Run phase
            if not self.dry_run:
                import subprocess
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=1800  # 30 minutes timeout
                )
                
                if result.returncode == 0:
                    self.phases[phase_num]['status'] = 'completed'
                    self.phases[phase_num]['end_time'] = datetime.now(timezone.utc).isoformat()
                    duration = (datetime.now(timezone.utc) - phase_start_time).total_seconds()
                    self.phases[phase_num]['duration'] = duration
                    
                    # Parse output for summary
                    output_summary = self._parse_phase_output(result.stdout, phase_name)
                    self.phases[phase_num]['output_summary'] = output_summary
                    
                    logger.info(f"Phase {phase_num} ({phase_name}) completed successfully")
                    logger.info(f"Output summary: {output_summary}")
                    
                    return True
                else:
                    self.phases[phase_num]['status'] = 'failed'
                    self.phases[phase_num]['end_time'] = datetime.now(timezone.utc).isoformat()
                    self.phases[phase_num]['output_summary'] = f"Failed with return code {result.returncode}"
                    
                    logger.error(f"Phase {phase_num} ({phase_name}) failed: {result.stderr}")
                    return False
            else:
                # Dry run - just simulate
                self.phases[phase_num]['status'] = 'completed'
                self.phases[phase_num]['end_time'] = datetime.now(timezone.utc).isoformat()
                duration = (datetime.now(timezone.utc) - phase_start_time).total_seconds()
                self.phases[phase_num]['duration'] = duration
                self.phases[phase_num]['output_summary'] = "Dry run completed successfully"
                
                logger.info(f"Phase {phase_num} ({phase_name}) dry run completed")
                return True
                
        except Exception as e:
            self.phases[phase_num]['status'] = 'failed'
            self.phases[phase_num]['end_time'] = datetime.now(timezone.utc).isoformat()
            self.phases[phase_num]['output_summary'] = f"Exception: {str(e)}"
            
            logger.error(f"Phase {phase_num} ({phase_name}) failed with exception: {e}")
            return False
    
    def _parse_phase_output(self, output: str, phase_name: str) -> str:
        """Parse phase output for summary."""
        if not output:
            return "No output"
        
        # Extract key information based on phase
        lines = output.strip().split('\n')
        
        if phase_name == '1.1':
            return self._parse_phase_1_1_output(lines)
        elif phase_name == '1.2':
            return self._parse_phase_1_2_output(lines)
        elif phase_name == '1.3':
            return self._parse_phase_1_3_output(lines)
        elif phase_name == '1.4':
            return self._parse_phase_1_4_output(lines)
        elif phase_name == '1.5':
            return self._parse_phase_1_5_output(lines)
        elif phase_name == '1.6':
            return self._parse_phase_1_6_output(lines)
        elif phase_name == '1.7':
            return self._parse_phase_1_7_output(lines)
        else:
            return f"Phase {phase_name} output: {len(lines)} lines"
    
    def _parse_phase_1_1_output(self, lines: List[str]) -> str:
        """Parse Phase 1.1 (HTML Cleaning) output."""
        for line in lines:
            if 'cleaned' in line.lower():
                return f"HTML cleaning completed: {line}"
        return "HTML cleaning output parsed"
    
    def _parse_phase_1_2_output(self, lines: List[str]) -> str:
        """Parse Phase 1.2 (Markdown Conversion) output."""
        for line in lines:
            if 'converted' in line.lower():
                return f"Markdown conversion completed: {line}"
        return "Markdown conversion output parsed"
    
    def _parse_phase_1_3_output(self, lines: List[str]) -> str:
        """Parse Phase 1.3 (Metadata Extraction) output."""
        for line in lines:
            if 'extracted' in line.lower():
                return f"Metadata extraction completed: {line}"
        return "Metadata extraction output parsed"
    
    def _parse_phase_1_4_output(self, lines: List[str]) -> str:
        """Parse Phase 1.4 (Chunking) output."""
        for line in lines:
            if 'chunks' in line.lower():
                return f"Chunking completed: {line}"
        return "Chunking output parsed"
    
    def _parse_phase_1_5_output(self, lines: List[str]) -> str:
        """Parse Phase 1.5 (Embedding Generation) output."""
        for line in lines:
            if 'embeddings' in line.lower():
                return f"Embedding generation completed: {line}"
        return "Embedding generation output parsed"
    
    def _parse_phase_1_6_output(self, lines: List[str]) -> str:
        """Parse Phase 1.6 (Vector Store) output."""
        for line in lines:
            if 'chroma' in line.lower() or 'vector' in line.lower():
                return f"Vector store update completed: {line}"
        return "Vector store output parsed"
    
    def _parse_phase_1_7_output(self, lines: List[str]) -> str:
        """Parse Phase 1.7 (Scheduler) output."""
        for line in lines:
            if 'orchestrated' in line.lower():
                return f"Pipeline orchestration completed: {line}"
        return "Pipeline orchestration output parsed"
    
    def _update_stats(self) -> None:
        """Update pipeline statistics."""
        completed = sum(1 for phase in self.phases.values() if phase['status'] == 'completed')
        failed = sum(1 for phase in self.phases.values() if phase['status'] == 'failed')
        total_duration = sum(phase.get('duration', 0) for phase in self.phases.values())
        
        self.stats.update({
            'completed_phases': completed,
            'failed_phases': failed,
            'total_duration': total_duration
        })
    
    def _detect_content_drift(self) -> bool:
        """Detect if content has changed since last run."""
        if not self.previous_run:
            return True  # No previous run, assume content has changed
        
        try:
            # Check if key data files have been modified
            data_dir = Path("data/processed")
            if not data_dir.exists():
                return True
            
            # Get modification times
            last_run_time = datetime.fromisoformat(self.previous_run['timestamp'])
            
            for file_path in data_dir.rglob("*"):
                if file_path.stat().st_mtime > last_run_time.timestamp():
                    logger.info(f"Content drift detected: {file_path} modified since last run")
                    return True
            
            logger.info("No content drift detected")
            return False
            
        except Exception as e:
            logger.warning(f"Content drift detection failed: {e}")
            return True  # Assume content has changed on error
    
    async def run_pipeline(self) -> Dict[str, Any]:
        """Run the complete ingestion pipeline."""
        logger.info(f"Starting pipeline orchestration - Run ID: {self.run_id}")
        logger.info(f"Force refresh: {self.force_refresh}")
        logger.info(f"Dry run: {self.dry_run}")
        
        # Detect content drift
        content_drift = self._detect_content_drift()
        incremental_update = not self.force_refresh and not content_drift
        
        # Define phases to run
        phases_to_run = ['1.1', '1.2', '1.3', '1.4', '1.5', '1.6', '1.7']
        
        if incremental_update:
            # For incremental updates, we might skip some phases
            # For now, run all phases for simplicity
            pass
        
        try:
            # Run each phase
            for phase_num in phases_to_run:
                phase_name = {
                    '1.1': 'HTML Cleaning',
                    '1.2': 'Markdown Conversion', 
                    '1.3': 'Metadata Extraction',
                    '1.4': 'Chunking',
                    '1.5': 'Embedding Generation',
                    '1.6': 'Vector Store',
                    '1.7': 'Scheduler & Orchestration'
                }[phase_num]
                
                success = self._run_phase(phase_name, phase_num)
                
                if not success:
                    logger.error(f"Pipeline failed at Phase {phase_num}")
                    break
            
            # Update statistics
            self._update_stats()
            
            # Save refresh log
            self._save_refresh_log()
            
            # Prepare final result
            total_phases = len(self.phases)
            completed_phases = self.stats['completed_phases']
            failed_phases = self.stats['failed_phases']
            
            result = {
                'run_id': self.run_id,
                'timestamp': self.start_time.isoformat(),
                'force_refresh': self.force_refresh,
                'dry_run': self.dry_run,
                'incremental_update': incremental_update,
                'content_drift': content_drift,
                'phases': self.phases,
                'stats': {
                    **self.stats,
                    'total_phases': total_phases,
                    'success_rate': (completed_phases / total_phases * 100) if total_phases > 0 else 0
                }
            }
            
            if self.dry_run:
                logger.info("DRY RUN COMPLETED - No actual changes made")
                result['dry_run_summary'] = "Dry run completed successfully. No actual changes made."
            else:
                logger.info(f"PIPELINE COMPLETED - {completed_phases}/{total_phases} phases successful")
                result['execution_summary'] = f"Pipeline executed with {completed_phases}/{total_phases} phases successful"
            
            return result
            
        except Exception as e:
            logger.error(f"Pipeline orchestration failed: {e}")
            return {
                'run_id': self.run_id,
                'timestamp': self.start_time.isoformat(),
                'error': str(e),
                'phases': self.phases,
                'stats': self.stats
            }
    
    def get_pipeline_health(self) -> Dict[str, Any]:
        """Get pipeline health status."""
        try:
            # Check if data directory exists
            data_dir = Path("data/processed")
            if not data_dir.exists():
                return {
                    'status': 'unhealthy',
                    'message': 'Data directory does not exist',
                    'last_run': self.previous_run
                }
            
            # Check recent refresh logs
            refresh_log_path = Path("data/logs/refresh_log.json")
            if not refresh_log_path.exists():
                return {
                    'status': 'unhealthy',
                    'message': 'No refresh logs found',
                    'last_run': self.previous_run
                }
            
            # Load recent logs
            with open(refresh_log_path, 'r') as f:
                logs = json.load(f)
            
            if not logs:
                return {
                    'status': 'unhealthy',
                    'message': 'No refresh history found',
                    'last_run': self.previous_run
                }
            
            recent_runs = logs[-5:]  # Last 5 runs
            failed_runs = [run for run in recent_runs if run.get('phases', {}).get('1.7', {}).get('status') == 'failed']
            
            health_status = 'healthy' if len(failed_runs) == 0 else 'degraded'
            
            return {
                'status': health_status,
                'message': f'Pipeline status: {health_status}',
                'last_run': logs[-1] if logs else None,
                'recent_failures': len(failed_runs),
                'total_runs': len(logs),
                'recent_runs': recent_runs
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                'status': 'error',
                'message': f'Health check error: {str(e)}'
            }
