from typing import Dict, List, Tuple
from pathlib import Path
from dataclasses import dataclass


@dataclass
class CategoryStats:
    """Statistics for a category."""
    category_name: str
    total_files: int
    total_size_bytes: int
    percentage_of_disk: float
    
    @property
    def total_size_gb(self) -> float:
        return self.total_size_bytes / (1024 ** 3)


@dataclass
class FolderStats:
    """Statistics for a folder."""
    folder_path: str
    total_size_bytes: int
    file_count: int
    percentage_of_disk: float
    
    @property
    def total_size_gb(self) -> float:
        return self.total_size_bytes / (1024 ** 3)


class VisualizationEngine:
    """
    Generates visualization data: category breakdowns, top folders, disk usage stats.
    Used by UI for displaying treemaps, bar charts, and percentages.
    """
    
    def __init__(self, database):
        self.db = database
    
    def get_category_statistics(self, total_disk_bytes: int = None) -> List[CategoryStats]:
        """
        Aggregate statistics by category from indexed files.
        
        Returns list of CategoryStats sorted by size (descending).
        """
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # Get all files with their categories (if stored in DB)
        cursor.execute("""
            SELECT category, COUNT(*) as file_count, SUM(size) as total_size
            FROM files
            WHERE size > 0
            GROUP BY category
            ORDER BY total_size DESC
        """)
        
        results = cursor.fetchall()
        cursor.close()
        
        if not total_disk_bytes:
            # Calculate from query results
            total_disk_bytes = sum(row[2] for row in results if row[2])
        
        stats = []
        for category_name, file_count, total_size in results:
            if not total_size:
                continue
                
            percentage = (total_size / total_disk_bytes * 100) if total_disk_bytes > 0 else 0
            stats.append(CategoryStats(
                category_name=category_name or "Unknown",
                total_files=file_count,
                total_size_bytes=total_size,
                percentage_of_disk=percentage
            ))
        
        return stats
    
    def get_top_folders(self, limit: int = 20, min_size_mb: float = 0) -> List[FolderStats]:
        """
        Get top N largest folders in the index.
        
        Returns list of FolderStats sorted by size (descending).
        """
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        min_size_bytes = min_size_mb * (1024 ** 2)
        
        # Aggregate by parent directory
        cursor.execute("""
            SELECT parent_path, COUNT(*) as file_count, SUM(size) as total_size
            FROM files
            WHERE size > 0 AND parent_path IS NOT NULL
            GROUP BY parent_path
            HAVING total_size > ?
            ORDER BY total_size DESC
            LIMIT ?
        """, (min_size_bytes, limit))
        
        results = cursor.fetchall()
        
        # Get total disk usage for percentage calculation
        cursor.execute("SELECT SUM(size) as total FROM files WHERE size > 0")
        total_disk = cursor.fetchone()[0] or 1
        cursor.close()
        
        stats = []
        for folder_path, file_count, total_size in results:
            if not total_size:
                continue
                
            percentage = (total_size / total_disk * 100) if total_disk > 0 else 0
            stats.append(FolderStats(
                folder_path=folder_path,
                total_size_bytes=total_size,
                file_count=file_count,
                percentage_of_disk=percentage
            ))
        
        return stats
    
    def get_disk_summary(self) -> Dict:
        """
        Get overall disk usage summary (useful for dashboard).
        """
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # Total stats
        cursor.execute("""
            SELECT 
                COUNT(*) as total_files,
                SUM(size) as total_bytes,
                COUNT(DISTINCT parent_path) as total_dirs
            FROM files
        """)
        row = cursor.fetchone()
        total_files, total_bytes, total_dirs = row if row else (0, 0, 0)
        
        # Largest file
        cursor.execute("SELECT path, size FROM files ORDER BY size DESC LIMIT 1")
        largest = cursor.fetchone()
        
        cursor.close()
        
        return {
            "total_files": total_files,
            "total_bytes": total_bytes,
            "total_gb": (total_bytes or 0) / (1024 ** 3),
            "total_dirs": total_dirs,
            "largest_file": {
                "path": largest[0] if largest else None,
                "size_bytes": largest[1] if largest else 0,
                "size_gb": (largest[1] or 0) / (1024 ** 3)
            }
        }
    
    def get_duplicates_by_size_impact(self, limit: int = 10) -> List[Dict]:
        """
        Get duplicate groups with largest size impact (GB saved if cleaned).
        """
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # Groups by hash with multiple files
        cursor.execute("""
            SELECT full_hash, COUNT(*) as file_count, SUM(size) as total_size, 
                   SUM(size) * (COUNT(*) - 1) as recoverable_bytes
            FROM files
            WHERE full_hash IS NOT NULL
            GROUP BY full_hash
            HAVING COUNT(*) > 1
            ORDER BY recoverable_bytes DESC
            LIMIT ?
        """, (limit,))
        
        results = cursor.fetchall()
        cursor.close()
        
        duplicates = []
        for file_hash, count, total_size, recoverable in results:
            duplicates.append({
                "hash": file_hash,
                "duplicate_count": count,
                "total_size_bytes": total_size,
                "recoverable_bytes": recoverable,
                "recoverable_gb": (recoverable or 0) / (1024 ** 3)
            })
        
        return duplicates
    
    @staticmethod
    def format_bytes(size_bytes: int) -> str:
        """Convert bytes to human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.2f} PB"
