"""
Disk Scanner: Scans and indexes files on disk
"""

import os
from pathlib import Path
from typing import List, Callable, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from db.models import FileInfo
from db.database import Database
from utils.config import Config
from utils.logger import setup_logger


class DiskScanner:
    """Scans disks and creates file index"""
    
    def __init__(self, db: Database = None, config: Config = None):
        self.db = db or Database()
        self.config = config or Config()
        self.logger = setup_logger("Scanner", "logs/scanner.log")
        self.is_cancelled = False
        self.is_paused = False
        self.file_count = 0
        self.total_size = 0
        self.start_time = None
    
    def scan_paths(
        self,
        paths: List[str],
        progress_callback: Optional[Callable] = None,
        error_callback: Optional[Callable] = None
    ) -> dict:
        """
        Scans multiple paths
        
        Args:
            paths: List of paths to scan
            progress_callback: Function to report progress
            error_callback: Function to report errors
        
        Returns:
            Dict with scan statistics
        """
        self.start_time = datetime.now()
        self.is_cancelled = False
        self.file_count = 0
        self.total_size = 0
        
        self.logger.info(f"Starting scan of: {paths}")
        
        # Clear previous scan
        self.db.clear_scan()
        
        all_files = []
        
        try:
            for path in paths:
                if self.is_cancelled:
                    break
                
                if not os.path.exists(path):
                    msg = f"Path not found: {path}"
                    self.logger.warning(msg)
                    if error_callback:
                        error_callback(msg)
                    continue
                
                self.logger.info(f"Scanning: {path}")
                files = self._scan_directory(path, progress_callback, error_callback)
                all_files.extend(files)
            
            # Insert into DB
            if all_files:
                self.logger.info(f"Inserting {len(all_files)} files into DB")
                self.db.bulk_insert_files(all_files)
            
            duration = (datetime.now() - self.start_time).total_seconds()
            
            stats = {
                'file_count': self.file_count,
                'total_size': self.total_size,
                'duration': duration,
                'status': 'cancelled' if self.is_cancelled else 'completed'
            }
            
            self.logger.info(
                f"Scan completed: {self.file_count} files, "
                f"{self._format_size(self.total_size)}, {duration:.2f}s"
            )
            
            return stats
        
        except Exception as e:
            self.logger.error(f"Scan error: {str(e)}", exc_info=True)
            if error_callback:
                error_callback(f"Fatal error: {str(e)}")
            return {'status': 'error', 'error': str(e)}
    
    def _scan_directory(
        self,
        root_path: str,
        progress_callback: Optional[Callable] = None,
        error_callback: Optional[Callable] = None
    ) -> List[FileInfo]:
        """
        Scan a directory recursively with intelligent permission handling.
        Uses os.walk with onerror to gracefully skip inaccessible folders.
        """
        
        files = []
        root = Path(root_path)
        permission_errors = 0
        max_permission_errors_logged = 5  # Limit logged permission errors
        
        def handle_walk_error(error):
            """Handle errors during os.walk - silently skip inaccessible dirs"""
            nonlocal permission_errors
            permission_errors += 1
            if permission_errors <= max_permission_errors_logged:
                self.logger.debug(f"Skipping inaccessible: {error.filename}")
        
        try:
            for dirpath, dirnames, filenames in os.walk(root, onerror=handle_walk_error):
                # Check for cancel
                if self.is_cancelled:
                    break
                
                # Handle pause - wait loop
                while self.is_paused and not self.is_cancelled:
                    import time
                    time.sleep(0.1)
                
                if self.is_cancelled:
                    break
                
                current_dir = Path(dirpath)
                
                # Filter out excluded directories from dirnames (prevents descending into them)
                dirnames[:] = [d for d in dirnames if not self._should_skip_dir(current_dir / d)]
                
                # Process files in current directory
                for filename in filenames:
                    if self.is_cancelled:
                        break
                    
                    try:
                        item = current_dir / filename
                        
                        # Skip excluded extensions
                        if self.config.is_extension_excluded(filename):
                            continue
                        
                        # Create FileInfo
                        file_info = FileInfo.from_path(item)
                        
                        if file_info:
                            files.append(file_info)
                            self.file_count += 1
                            self.total_size += file_info.size
                            
                            # Progress callback every 10 files
                            if progress_callback and self.file_count % 10 == 0:
                                elapsed = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
                                speed = self.file_count / elapsed if elapsed > 0 else 0
                                progress_callback({
                                    'file_count': self.file_count,
                                    'total_size': self.total_size,
                                    'current_path': str(item),
                                    'elapsed': elapsed,
                                    'speed': speed
                                })
                    
                    except PermissionError:
                        permission_errors += 1
                        # Silently skip - don't flood logs
                        continue
                    
                    except Exception as e:
                        # Log non-permission errors
                        self.logger.debug(f"Error processing {filename}: {str(e)}")
            
            if permission_errors > 0:
                self.logger.info(f"Skipped {permission_errors} items due to permission issues (normal for system folders)")
        
        except Exception as e:
            self.logger.error(f"Error scanning directory {root_path}: {str(e)}")
            if error_callback:
                error_callback(f"Error scanning {root_path}")
        
        return files
    
    def _should_skip_dir(self, dir_path: Path) -> bool:
        """Check if directory should be skipped (excluded or known problematic)"""
        dir_str = str(dir_path)
        
        # Check config exclusions
        if self.config.is_path_excluded(dir_str):
            return True
        
        # Skip known Windows problematic directories
        skip_names = {
            '$recycle.bin', 'system volume information', 'windowsapps',
            '$windows.~bt', '$windows.~ws', 'config.msi', 'msocache',
            'recovery', 'perflogs'
        }
        
        dir_name_lower = dir_path.name.lower()
        if dir_name_lower in skip_names:
            return True
        
        # Skip directories starting with $ (Windows system)
        if dir_path.name.startswith('$'):
            return True
        
        return False
    
    def cancel_scan(self):
        """Cancels the ongoing scan"""
        self.is_cancelled = True
        self.logger.info("Scan cancelled by user")
    
    def pause_scan(self):
        """Pauses the scan"""
        self.is_paused = True
        self.logger.info("Scan paused")
    
    def resume_scan(self):
        """Resumes the scan"""
        self.is_paused = False
        self.logger.info("Scan resumed")
    
    @staticmethod
    def _format_size(bytes_size: int) -> str:
        """Formats byte size to human readable"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_size < 1024.0:
                return f"{bytes_size:.2f} {unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.2f} PB"


class IncrementalScanner:
    """Incremental scanner: only updates changes"""
    
    def __init__(self, db: Database = None, config: Config = None):
        self.db = db or Database()
        self.config = config or Config()
        self.logger = setup_logger("IncrementalScanner", "logs/scanner.log")
    
    def rescan_path(self, path: str) -> dict:
        """
        Re-scans a path detecting only changes
        
        Args:
            path: Path to re-scan
        
        Returns:
            Change statistics
        """
        # TODO: Implement change detection using timestamp
        # For now, perform full scan
        scanner = DiskScanner(self.db, self.config)
        return scanner.scan_paths([path])
