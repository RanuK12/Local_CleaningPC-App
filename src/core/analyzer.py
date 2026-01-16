"""
Analysis engine: identifies unnecessary files using intelligent categorization.
Detects duplicates, large files, old files, temp files, etc.
"""

from typing import List, Dict
from datetime import datetime, timedelta
from collections import defaultdict

from db.models import FileInfo, CleanupCandidate, DuplicateGroup
from db.database import Database
from utils.config import Config
from utils.hash_utils import HashCalculator
from utils.logger import setup_logger
from core.categorizer import FileCategorizer, Category, CategoryConfidence


class AnalysisEngine:
    """
    Analyzes indexed files to identify cleanup candidates.
    Categorizes files and applies intelligent detection rules.
    """
    
    def __init__(self, db: Database = None, config: Config = None, categorizer: FileCategorizer = None):
        self.db = db or Database()
        self.config = config or Config()
        self.categorizer = categorizer or FileCategorizer()
        self.logger = setup_logger("Analyzer", "logs/analyzer.log")
        self.candidates: List[CleanupCandidate] = []
    
    def analyze(self, rules: Dict = None) -> Dict:
        """
        Execute complete analysis on indexed files.
        
        Args:
            rules: Dict of enabled/disabled detection rules
        
        Returns:
            Statistics dict with count and saved_space for each rule
        """
        if rules is None:
            rules = {
                'duplicates': True,
                'large_files': True,
                'old_files': True,
                'temp_files': True,
                'compressed_archives': True,
            }
        
        self.candidates = []
        self.logger.info("Starting comprehensive analysis...")
        
        stats = {
            'duplicates': {'count': 0, 'saved_space': 0},
            'large_files': {'count': 0, 'saved_space': 0},
            'old_files': {'count': 0, 'saved_space': 0},
            'temp_files': {'count': 0, 'saved_space': 0},
            'compressed_archives': {'count': 0, 'saved_space': 0},
            'total_candidates': 0,
            'total_saved_space': 0,
        }
        
        try:
            if rules.get('duplicates', False):
                dup_stats = self._analyze_duplicates()
                stats['duplicates'] = dup_stats
            
            if rules.get('large_files', False):
                large_stats = self._analyze_large_files()
                stats['large_files'] = large_stats
            
            if rules.get('old_files', False):
                old_stats = self._analyze_old_files()
                stats['old_files'] = old_stats
            
            if rules.get('temp_files', False):
                temp_stats = self._analyze_temp_files()
                stats['temp_files'] = temp_stats
            
            if rules.get('compressed_archives', False):
                arch_stats = self._analyze_archives()
                stats['compressed_archives'] = arch_stats
            
            stats['total_candidates'] = len(self.candidates)
            stats['total_saved_space'] = sum(c.estimated_saved_space for c in self.candidates)
            
            self.logger.info(f"Analysis complete: {len(self.candidates)} cleanup candidates identified")
            
            return stats
        
        except Exception as e:
            self.logger.error(f"Analysis error: {str(e)}", exc_info=True)
            return {'status': 'error', 'error': str(e)}
    
    def _analyze_duplicates(self) -> Dict:
        """
        Find identical files using quick hash (pre-filter) and full hash (verification).
        Only keeps duplicates if multiple copies exist.
        """
        
        files = self.db.get_all_files(exclude_dirs=True)
        hash_groups = defaultdict(list)
        
        self.logger.info(f"Scanning {len(files)} files for duplicates...")
        
        # Group by quick hash for fast pre-filtering
        for file_info in files:
            quick_hash = HashCalculator.quick_hash(file_info.path)
            if quick_hash:
                file_info.quick_hash = quick_hash
                hash_groups[quick_hash].append(file_info)
        
        count = 0
        saved_space = 0
        
        # Find groups with multiple files (potential duplicates)
        for hash_value, file_list in hash_groups.items():
            if len(file_list) > 1:
                # Mark duplicates (keep first copy, mark rest as candidates)
                for file_info in file_list[1:]:
                    category, confidence, rules_fired = self.categorizer.categorize(file_info.path)
                    
                    candidate = CleanupCandidate(
                        file_info=file_info,
                        detection_category='duplicate',
                        file_category=category.value,
                        category_confidence=confidence.value,
                        category_rules=rules_fired,
                        risk_level='Low',
                        reason=f'Duplicate (found {len(file_list)} copies)',
                        estimated_saved_space=file_info.size,
                        recommended_action='move'
                    )
                    self.candidates.append(candidate)
                    count += 1
                    saved_space += file_info.size
        
        self.logger.info(f"Duplicates: {count} files, {saved_space / 1024 / 1024:.2f} MB can be saved")
        
        return {'count': count, 'saved_space': saved_space}
    
    def _analyze_large_files(self, min_size: int = 500 * 1024 * 1024) -> Dict:
        """
        Identify very large files (default >500MB).
        Large files often indicate ISOs, backups, or unused data.
        """
        
        large_files = self.db.get_large_files(min_size, limit=1000)
        
        self.logger.info(f"Found {len(large_files)} large files for review")
        
        count = 0
        saved_space = 0
        
        for file_info in large_files:
            # Categorize and check risk
            category, confidence, rules_fired = self.categorizer.categorize(file_info.path)
            
            # Skip critical system files
            if category == Category.SYSTEM:
                continue
            
            candidate = CleanupCandidate(
                file_info=file_info,
                detection_category='large_file',
                file_category=category.value,
                category_confidence=confidence.value,
                category_rules=rules_fired,
                risk_level='Medium',
                reason=f'Large file ({file_info.size / 1024 / 1024:.0f} MB)',
                estimated_saved_space=file_info.size,
                recommended_action='review'
            )
            self.candidates.append(candidate)
            count += 1
            saved_space += file_info.size
        
        self.logger.info(f"Large files: {count} candidates")
        return {'count': count, 'saved_space': saved_space}
    
    def _analyze_old_files(self, days: int = None) -> Dict:
        """
        Find files not accessed in specified days (default 180 days).
        Conservative: only flags files in Downloads folder to minimize risk.
        """
        
        if days is None:
            days = self.config.get('old_files_days', 180)
        
        cutoff_date = datetime.now() - timedelta(days=days)
        all_files = self.db.get_all_files(exclude_dirs=True)
        
        count = 0
        saved_space = 0
        
        for file_info in all_files:
            # Conservative: only mark old files in Downloads
            if (file_info.accessed_time and 
                file_info.accessed_time < cutoff_date and
                'download' in file_info.path.lower()):
                
                category, confidence, rules_fired = self.categorizer.categorize(file_info.path)
                
                candidate = CleanupCandidate(
                    file_info=file_info,
                    detection_category='old_file',
                    file_category=category.value,
                    category_confidence=confidence.value,
                    category_rules=rules_fired,
                    risk_level='Low',
                    reason=f'Not accessed in {days}+ days (in Downloads)',
                    estimated_saved_space=file_info.size,
                    recommended_action='move'
                )
                self.candidates.append(candidate)
                count += 1
                saved_space += file_info.size
        
        self.logger.info(f"Old files: {count} in Downloads, {saved_space / 1024 / 1024:.2f} MB")
        
        return {'count': count, 'saved_space': saved_space}
    
    def _analyze_temp_files(self) -> Dict:
        """
        Detect temporary files including:
        - Files with temp extensions (.tmp, .temp, .bak, .log, .dmp, etc.)
        - Files in temp folders (Temp, Cache, INetCache, etc.)
        - Browser cache files
        - Windows temporary files
        These files are typically safe to delete.
        """
        
        all_files = self.db.get_all_files(exclude_dirs=True)
        
        count = 0
        saved_space = 0
        
        for file_info in all_files:
            # Skip protected paths
            if self.config.is_protected_path(file_info.path):
                continue
            
            is_temp = False
            reason = ""
            
            # Check 1: Temp file pattern (by filename)
            if self.config.is_temp_file(file_info.name):
                is_temp = True
                reason = f'Temporary file pattern ({file_info.extension or file_info.name})'
            
            # Check 2: File is in a temp/cache folder
            elif self.config.is_temp_folder(file_info.path):
                is_temp = True
                # Determine which type of temp folder
                path_lower = file_info.path.lower()
                if 'cache' in path_lower:
                    reason = 'Browser/Application cache file'
                elif 'temp' in path_lower:
                    reason = 'Windows temporary file'
                elif 'inetcache' in path_lower or 'temporary internet' in path_lower:
                    reason = 'Internet cache file'
                elif 'crashdump' in path_lower or 'crash report' in path_lower:
                    reason = 'Crash dump file'
                else:
                    reason = 'Temporary folder file'
            
            # Check 3: Safe-to-delete extension
            elif self.config.is_safe_to_delete(file_info.path, file_info.name):
                is_temp = True
                reason = f'Safe to delete ({file_info.extension})'
            
            if is_temp:
                category, confidence, rules_fired = self.categorizer.categorize(file_info.path)
                
                # Determine risk level based on location
                risk_level = 'Low'
                if 'appdata' not in file_info.path.lower() and 'temp' not in file_info.path.lower():
                    risk_level = 'Medium'  # Files outside typical temp locations
                
                candidate = CleanupCandidate(
                    file_info=file_info,
                    detection_category='temp_file',
                    file_category=category.value,
                    category_confidence=confidence.value,
                    category_rules=rules_fired,
                    risk_level=risk_level,
                    reason=reason,
                    estimated_saved_space=file_info.size,
                    recommended_action='delete'
                )
                self.candidates.append(candidate)
                count += 1
                saved_space += file_info.size
        
        self.logger.info(f"Temp files: {count} found, {saved_space / 1024 / 1024:.2f} MB")
        
        return {'count': count, 'saved_space': saved_space}
    
    def _analyze_archives(self) -> Dict:
        """
        Find redundant compressed files and disk images.
        Flags old ISO, zip, rar files when newer versions exist.
        """
        
        archive_extensions = ['.zip', '.rar', '.7z', '.tar', '.gz', '.iso', '.dmg']
        all_files = self.db.get_all_files(exclude_dirs=True)
        
        count = 0
        saved_space = 0
        
        for file_info in all_files:
            if file_info.extension in archive_extensions:
                # Check if newer version of same file exists
                newer_version = False
                for other in all_files:
                    if (other.extension == file_info.extension and
                        other.name.split('_')[0] == file_info.name.split('_')[0] and
                        other.modified_time and file_info.modified_time and
                        other.modified_time > file_info.modified_time):
                        newer_version = True
                        break
                
                if newer_version:
                    category, confidence, rules_fired = self.categorizer.categorize(file_info.path)
                    
                    candidate = CleanupCandidate(
                        file_info=file_info,
                        detection_category='compressed_archive',
                        file_category=category.value,
                        category_confidence=confidence.value,
                        category_rules=rules_fired,
                        risk_level='Medium',
                        reason='Old version (newer copy exists)',
                        estimated_saved_space=file_info.size,
                        recommended_action='move'
                    )
                    self.candidates.append(candidate)
                    count += 1
                    saved_space += file_info.size
        
        self.logger.info(f"Old archives: {count} found, {saved_space / 1024 / 1024:.2f} MB")
        return {'count': count, 'saved_space': saved_space}
