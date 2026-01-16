"""
Data models for the Local Cleaner application.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, List


@dataclass
class FileInfo:
    """
    Represents an indexed file with all metadata.
    """
    
    id: Optional[int] = None
    path: str = ""
    name: str = ""
    extension: str = ""
    size: int = 0
    created_time: Optional[datetime] = None
    modified_time: Optional[datetime] = None
    accessed_time: Optional[datetime] = None
    is_directory: bool = False
    parent_path: str = ""
    owner: str = ""
    quick_hash: Optional[str] = None
    full_hash: Optional[str] = None
    category: str = "Unknown"  # File category (System, Apps, Media, etc.)
    category_confidence: str = "Low"  # HIGH, MEDIUM, LOW
    
    @staticmethod
    def from_path(file_path: Path) -> 'FileInfo':
        """Create FileInfo from a filesystem path."""
        try:
            stat = file_path.stat()
            
            return FileInfo(
                path=str(file_path),
                name=file_path.name,
                extension=file_path.suffix.lower(),
                size=stat.st_size,
                created_time=datetime.fromtimestamp(stat.st_ctime),
                modified_time=datetime.fromtimestamp(stat.st_mtime),
                accessed_time=datetime.fromtimestamp(stat.st_atime),
                is_directory=file_path.is_dir(),
                parent_path=str(file_path.parent),
                owner=""
            )
        except Exception:
            return None
    
    def get_size_mb(self) -> float:
        """Return size in MB."""
        return self.size / (1024 * 1024)
    
    def get_size_gb(self) -> float:
        """Return size in GB."""
        return self.size / (1024 * 1024 * 1024)
    
    def format_size(self) -> str:
        """Return human-readable size string."""
        size = self.size
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f"{size:.2f} {unit}"
            size /= 1024
        return f"{size:.2f} PB"


@dataclass
class DuplicateGroup:
    """
    Represents a group of identical files (by hash).
    """
    
    hash_value: str
    file_count: int
    total_size: int
    files: list  # List of FileInfo objects
    
    def get_saved_space(self) -> int:
        """Space reclaimed if keeping only one copy."""
        return self.total_size - (self.files[0].size if self.files else 0)


@dataclass
class CleanupCandidate:
    """
    A file marked for potential cleanup with reasoning and risk assessment.
    """
    
    file_info: FileInfo
    detection_category: str  # 'duplicate', 'old', 'temp', 'large', 'archive'
    file_category: str  # 'System', 'Apps', 'Games', 'Media', etc.
    category_confidence: str  # 'High', 'Medium', 'Low'
    category_rules: List[str] = field(default_factory=list)  # Rules that triggered category
    risk_level: str = "Low"  # Low, Medium, High
    reason: str = ""  # Explanation
    estimated_saved_space: int = 0  # Bytes
    recommended_action: str = "review"  # 'move', 'delete', 'review'


@dataclass
class CleanupAction:
    """
    Represents a cleanup action to be executed or recorded.
    """
    
    id: str
    file_path: str
    action_type: str  # 'move', 'delete', 'quarantine', 'trash'
    target_path: Optional[str] = None

    dry_run: bool = True
    status: str = 'pending'  # 'pending', 'completed', 'failed'
    error_message: Optional[str] = None
    timestamp: Optional[datetime] = None
    
    def mark_completed(self):
        """Marca como completada"""
        self.status = 'completed'
        self.timestamp = datetime.now()
    
    def mark_failed(self, error: str):
        """Marca como fallida"""
        self.status = 'failed'
        self.error_message = error
        self.timestamp = datetime.now()
