"""
Cleanup Engine: Handles safe file cleanup operations
Provides multiple action modes: dry-run, quarantine, recycle bin, permanent delete
"""

import os
import shutil
import re
from pathlib import Path
from typing import List, Callable, Optional
from datetime import datetime
import uuid

# Try to import send2trash, fallback gracefully if not available
try:
    import send2trash
    HAS_SEND2TRASH = True
except ImportError:
    HAS_SEND2TRASH = False

from db.models import CleanupCandidate, CleanupAction, FileInfo
from db.database import Database
from utils.config import Config
from utils.logger import ActionLogger, setup_logger


# Constants for file operations
DEFAULT_QUARANTINE_PATH = "data/quarantine"
MAX_PATH_LENGTH = 260  # Windows MAX_PATH


class CleanupEngine:
    """
    Safe cleanup engine with confirmation workflow.
    Supports dry-run, quarantine, recycle bin, and permanent delete operations.
    """
    
    def __init__(self, db: Database = None, config: Config = None):
        self.db = db or Database()
        self.config = config or Config()
        self.logger = setup_logger("Cleaner", "logs/cleaner.log")
        self.action_logger = ActionLogger("logs/actions.log")
        
        # Safely get quarantine path with fallback
        quarantine_config = self.config.get('quarantine_path', DEFAULT_QUARANTINE_PATH)
        if quarantine_config:
            self.quarantine_path = Path(quarantine_config)
        else:
            self.quarantine_path = Path(DEFAULT_QUARANTINE_PATH)
        
        # Ensure quarantine directory exists
        self.quarantine_path.mkdir(parents=True, exist_ok=True)
    
    def _validate_path(self, path: str) -> bool:
        """
        Validates a file path for security (prevents path traversal attacks)
        
        Args:
            path: Path string to validate
            
        Returns:
            True if path is safe, False otherwise
        """
        if not path:
            return False
        
        try:
            # Normalize and resolve path
            resolved = Path(path).resolve()
            
            # Check for path traversal attempts
            if '..' in str(path):
                self.logger.warning(f"Path traversal attempt detected: {path}")
                return False
            
            # Check path length (Windows limit)
            if len(str(resolved)) > MAX_PATH_LENGTH:
                self.logger.warning(f"Path too long: {path}")
                return False
            
            return True
        except Exception as e:
            self.logger.error(f"Path validation error: {e}")
            return False
    
    def create_cleanup_plan(
        self,
        candidates: List[CleanupCandidate],
        action_type: str = 'move'
    ) -> List[CleanupAction]:
        """
        Creates a cleanup plan (without executing yet)
        
        Args:
            candidates: List of candidates to clean up
            action_type: Action type ('move', 'delete', 'quarantine')
        
        Returns:
            List of actions to execute
        """
        
        actions = []
        
        for candidate in candidates:
            action = CleanupAction(
                id=str(uuid.uuid4()),
                file_path=candidate.file_info.path,
                action_type=action_type,
                target_path=self._get_target_path(candidate),
                dry_run=True,
                status='pending'
            )
            actions.append(action)
        
        self.logger.info(f"Plan created with {len(actions)} actions")
        
        return actions
    
    def simulate_cleanup(self, actions: List[CleanupAction]) -> dict:
        """
        Simulates cleanup execution (dry-run)
        
        Args:
            actions: Actions to simulate
        
        Returns:
            Simulation results
        """
        
        self.logger.info(f"Starting simulation of {len(actions)} actions")
        
        results = {
            'successful': 0,
            'failed': 0,
            'total_freed': 0,
            'details': []
        }
        
        for action in actions:
            action.dry_run = True
            
            try:
                file_path = Path(action.file_path)
                
                if not file_path.exists():
                    action.mark_failed("File not found")
                    results['failed'] += 1
                    continue
                
                file_size = file_path.stat().st_size
                
                if action.action_type == 'move':
                    msg = f"[SIM] Would move {action.file_path} to {action.target_path}"
                elif action.action_type == 'delete':
                    msg = f"[SIM] Would delete {action.file_path}"
                elif action.action_type == 'quarantine':
                    msg = f"[SIM] Would quarantine: {action.file_path}"
                else:
                    msg = f"[SIM] Unknown action: {action.action_type}"
                
                self.logger.info(msg)
                action.mark_completed()
                results['successful'] += 1
                results['total_freed'] += file_size
                results['details'].append({
                    'path': action.file_path,
                    'action': action.action_type,
                    'size': file_size,
                    'status': 'simulated'
                })
            
            except Exception as e:
                self.logger.error(f"Simulation error: {str(e)}")
                action.mark_failed(str(e))
                results['failed'] += 1
        
        self.logger.info(
            f"Simulation completed: {results['successful']} ok, "
            f"{results['failed']} failed, {results['total_freed'] / 1024 / 1024:.2f} MB"
        )
        
        return results
    
    def execute_cleanup(
        self,
        actions: List[CleanupAction],
        progress_callback: Optional[Callable] = None,
        require_confirmation: bool = True
    ) -> dict:
        """
        Executes real cleanup operations
        
        Args:
            actions: Actions to execute
            progress_callback: Progress callback function
            require_confirmation: If explicit confirmation required
        
        Returns:
            Execution results
        """
        
        if require_confirmation:
            self.logger.warning("REAL CLEANUP REQUIRED - EXPLICIT CONFIRMATION MANDATORY")
        
        self.logger.info(f"Executing {len(actions)} cleanup actions")
        
        results = {
            'successful': 0,
            'failed': 0,
            'total_freed': 0,
            'details': []
        }
        
        for idx, action in enumerate(actions):
            action.dry_run = False
            
            try:
                file_path = Path(action.file_path)
                
                if not file_path.exists():
                    raise FileNotFoundError(f"File not found: {action.file_path}")
                
                file_size = file_path.stat().st_size
                
                # Ejecutar acción
                if action.action_type == 'move':
                    self._move_file(action, file_path)
                
                elif action.action_type == 'delete':
                    self._delete_file_to_trash(action, file_path)
                
                elif action.action_type == 'quarantine':
                    self._move_to_quarantine(action, file_path)
                
                else:
                    raise ValueError(f"Unknown action type: {action.action_type}")
                
                action.mark_completed()
                results['successful'] += 1
                results['total_freed'] += file_size
                
                self.action_logger.log_action(
                    action=action.action_type,
                    target=action.file_path,
                    status='success',
                    details=f"Size: {file_size / 1024 / 1024:.2f} MB"
                )
                
                results['details'].append({
                    'path': action.file_path,
                    'action': action.action_type,
                    'size': file_size,
                    'status': 'completed'
                })
            
            except Exception as e:
                self.logger.error(f"Error executing action: {str(e)}")
                action.mark_failed(str(e))
                results['failed'] += 1
                
                self.action_logger.log_action(
                    action=action.action_type,
                    target=action.file_path,
                    status='fail',
                    details=str(e)
                )
                
                results['details'].append({
                    'path': action.file_path,
                    'action': action.action_type,
                    'status': 'failed',
                    'error': str(e)
                })
            
            # Progress callback
            if progress_callback:
                progress_callback({
                    'current': idx + 1,
                    'total': len(actions),
                    'successful': results['successful'],
                    'failed': results['failed']
                })
        
        self.logger.info(
            f"Cleanup completed: {results['successful']} ok, "
            f"{results['failed']} failed, {results['total_freed'] / 1024 / 1024:.2f} MB freed"
        )
        
        return results
    
    def _move_file(self, action: CleanupAction, file_path: Path):
        """Moves file to destination with path validation"""
        if not self._validate_path(str(file_path)):
            raise ValueError(f"Invalid source path: {file_path}")
        if not self._validate_path(action.target_path):
            raise ValueError(f"Invalid target path: {action.target_path}")
            
        target = Path(action.target_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        
        shutil.move(str(file_path), str(target))
        self.logger.info(f"Moved: {file_path} -> {target}")
    
    def _delete_file_to_trash(self, action: CleanupAction, file_path: Path):
        """Sends file to recycle bin using send2trash or fallback to quarantine"""
        if not self._validate_path(str(file_path)):
            raise ValueError(f"Invalid path: {file_path}")
            
        if HAS_SEND2TRASH:
            send2trash.send2trash(str(file_path))
            self.logger.info(f"Sent to recycle bin: {file_path}")
        else:
            # Fallback: move to quarantine folder
            self.logger.warning("send2trash not available, moving to quarantine instead")
            self._move_to_quarantine(action, file_path)
    
    def _move_to_quarantine(self, action: CleanupAction, file_path: Path):
        """Moves file to quarantine preserving folder structure"""
        if not self._validate_path(str(file_path)):
            raise ValueError(f"Invalid path: {file_path}")
        
        # Create relative structure in quarantine
        try:
            relative_path = file_path.relative_to(file_path.drive)
        except ValueError:
            # If relative_to fails, use just the name
            relative_path = file_path.name
            
        quarantine_target = self.quarantine_path / relative_path
        
        quarantine_target.parent.mkdir(parents=True, exist_ok=True)
        
        shutil.move(str(file_path), str(quarantine_target))
        
        self.logger.info(f"Moved to quarantine: {file_path} -> {quarantine_target}")
        action.target_path = str(quarantine_target)
    
    def _get_target_path(self, candidate: CleanupCandidate) -> str:
        """Determines target path based on recommended action"""
        if candidate.recommended_action == 'move':
            return str(self.quarantine_path)
        return None
    
    def recover_from_quarantine(self, quarantine_path: str, original_path: str) -> bool:
        """
        Recovers file from quarantine
        
        Args:
            quarantine_path: Path in quarantine
            original_path: Original file path
        
        Returns:
            True if successful
        """
        try:
            q_path = Path(quarantine_path)
            orig_path = Path(original_path)
            
            if not q_path.exists():
                self.logger.warning(f"Not found in quarantine: {quarantine_path}")
                return False
            
            orig_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(q_path), str(orig_path))
            
            self.logger.info(f"Recovered: {quarantine_path} -> {original_path}")
            return True
        
        except Exception as e:
            self.logger.error(f"Recovery error: {str(e)}")
            return False
