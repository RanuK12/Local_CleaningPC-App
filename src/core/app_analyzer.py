"""
App Analyzer: Detects installed applications, their data, cache, and provides cleanup options.
Similar to Windows Settings > Apps functionality.
"""

import os
import winreg
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

from utils.logger import setup_logger


@dataclass
class InstalledApp:
    """Represents an installed application"""
    name: str
    publisher: str = ""
    version: str = ""
    install_location: str = ""
    install_date: str = ""
    uninstall_string: str = ""
    size_bytes: int = 0
    install_drive: str = ""  # Drive letter where app is installed (e.g., "C:", "D:")
    
    # Calculated fields
    data_size: int = 0  # Size of app data in AppData
    cache_size: int = 0  # Size of cache files
    temp_size: int = 0  # Size of temp files
    total_size: int = 0  # Total size including data
    
    data_paths: List[str] = field(default_factory=list)
    cache_paths: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        self.total_size = self.size_bytes + self.data_size + self.cache_size + self.temp_size
        # Auto-detect drive from install location or uninstall string
        if not self.install_drive:
            drive = self._extract_drive(self.install_location)
            if not drive:
                drive = self._extract_drive(self.uninstall_string)
            self.install_drive = drive or ""
    
    def _extract_drive(self, path_str: str) -> str:
        """Extract drive letter from a path string"""
        if not path_str:
            return ""
        # Remove quotes if present
        path_str = path_str.strip('"').strip("'")
        # Handle paths like "C:\Program Files\..." or with MsiExec
        import re
        match = re.search(r'([A-Za-z]):[\\\/]', path_str)
        if match:
            return f"{match.group(1).upper()}:"
        return ""


@dataclass 
class CleanupGroup:
    """A group of files that can be cleaned up"""
    name: str
    category: str  # 'temp', 'cache', 'logs', 'downloads', 'app_data'
    description: str
    files: List[Dict] = field(default_factory=list)
    total_size: int = 0
    file_count: int = 0
    is_safe: bool = True  # Safe to delete without affecting system
    icon: str = "📁"


class AppAnalyzer:
    """
    Analyzes installed applications and their associated data.
    Provides cleanup recommendations and uninstall capabilities.
    """
    
    def __init__(self):
        self.logger = setup_logger("AppAnalyzer", "logs/app_analyzer.log")
        self.apps: List[InstalledApp] = []
        self.cleanup_groups: List[CleanupGroup] = []
        self.user_profile = os.environ.get('USERPROFILE', 'C:\\Users\\Default')
        
    def get_installed_apps(self) -> List[InstalledApp]:
        """Get list of installed applications from Windows Registry"""
        self.apps = []
        
        # Registry paths for installed programs
        reg_paths = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        ]
        
        seen_apps = set()
        
        for hkey, path in reg_paths:
            try:
                with winreg.OpenKey(hkey, path) as key:
                    for i in range(winreg.QueryInfoKey(key)[0]):
                        try:
                            subkey_name = winreg.EnumKey(key, i)
                            with winreg.OpenKey(key, subkey_name) as subkey:
                                app = self._parse_app_registry(subkey)
                                if app and app.name and app.name not in seen_apps:
                                    seen_apps.add(app.name)
                                    self.apps.append(app)
                        except (WindowsError, OSError):
                            continue
            except (WindowsError, OSError) as e:
                self.logger.debug(f"Could not access registry path {path}: {e}")
        
        # Sort by name
        self.apps.sort(key=lambda x: x.name.lower())
        self.logger.info(f"Found {len(self.apps)} installed applications")
        
        return self.apps
    
    def _parse_app_registry(self, key) -> Optional[InstalledApp]:
        """Parse application info from registry key"""
        try:
            name = self._get_reg_value(key, "DisplayName")
            if not name or name.startswith("KB") or "Update" in name:
                return None  # Skip Windows updates
            
            return InstalledApp(
                name=name,
                publisher=self._get_reg_value(key, "Publisher") or "",
                version=self._get_reg_value(key, "DisplayVersion") or "",
                install_location=self._get_reg_value(key, "InstallLocation") or "",
                install_date=self._get_reg_value(key, "InstallDate") or "",
                uninstall_string=self._get_reg_value(key, "UninstallString") or "",
                size_bytes=self._get_reg_value(key, "EstimatedSize", 0) * 1024,
            )
        except Exception:
            return None
    
    def _get_reg_value(self, key, name, default=None):
        """Safely get registry value"""
        try:
            value, _ = winreg.QueryValueEx(key, name)
            return value
        except (WindowsError, OSError):
            return default
    
    def analyze_app_data(self, app: InstalledApp) -> InstalledApp:
        """Analyze an app's data folders (AppData, cache, etc.)"""
        app_name_lower = app.name.lower()
        app_name_parts = app_name_lower.replace(" ", "").split()
        
        # Common app data locations
        appdata_paths = [
            Path(self.user_profile) / "AppData" / "Local",
            Path(self.user_profile) / "AppData" / "Roaming",
            Path(self.user_profile) / "AppData" / "LocalLow",
        ]
        
        for appdata in appdata_paths:
            if not appdata.exists():
                continue
            
            try:
                for folder in appdata.iterdir():
                    if not folder.is_dir():
                        continue
                    
                    folder_lower = folder.name.lower()
                    
                    # Check if folder matches app name
                    if any(part in folder_lower for part in app_name_parts if len(part) > 3):
                        size = self._get_folder_size(folder)
                        app.data_size += size
                        app.data_paths.append(str(folder))
                        
                        # Check for cache subfolders
                        for sub in folder.rglob("*"):
                            if sub.is_dir() and 'cache' in sub.name.lower():
                                cache_size = self._get_folder_size(sub)
                                app.cache_size += cache_size
                                app.cache_paths.append(str(sub))
            except PermissionError:
                continue
        
        app.total_size = app.size_bytes + app.data_size + app.cache_size
        return app
    
    def get_cleanup_groups(self) -> List[CleanupGroup]:
        """Get organized cleanup groups like Windows Disk Cleanup"""
        self.cleanup_groups = []
        
        # 1. Windows Temp Files
        self.cleanup_groups.append(self._analyze_windows_temp())
        
        # 2. Browser Cache (each browser separate)
        self.cleanup_groups.extend(self._analyze_browser_cache())
        
        # 3. Windows Update Cleanup
        self.cleanup_groups.append(self._analyze_windows_update())
        
        # 4. Recycle Bin
        self.cleanup_groups.append(self._analyze_recycle_bin())
        
        # 5. Crash Dumps
        self.cleanup_groups.append(self._analyze_crash_dumps())
        
        # 6. Thumbnail Cache
        self.cleanup_groups.append(self._analyze_thumbnails())
        
        # 7. Log Files
        self.cleanup_groups.append(self._analyze_logs())
        
        # 8. Downloaded Program Files
        self.cleanup_groups.append(self._analyze_downloads_temp())
        
        # Filter out empty groups
        self.cleanup_groups = [g for g in self.cleanup_groups if g.file_count > 0]
        
        # Sort by size
        self.cleanup_groups.sort(key=lambda x: x.total_size, reverse=True)
        
        return self.cleanup_groups
    
    def _analyze_windows_temp(self) -> CleanupGroup:
        """Analyze Windows temporary files"""
        group = CleanupGroup(
            name="Archivos Temporales de Windows",
            category="temp",
            description="Archivos temporales del sistema y aplicaciones",
            icon="🗑️",
            is_safe=True
        )
        
        temp_paths = [
            Path(os.environ.get('TEMP', '')),
            Path(os.environ.get('TMP', '')),
            Path(self.user_profile) / "AppData" / "Local" / "Temp",
            Path("C:/Windows/Temp"),
        ]
        
        for temp_path in temp_paths:
            if temp_path.exists():
                self._scan_folder_for_group(group, temp_path)
        
        return group
    
    def _analyze_browser_cache(self) -> List[CleanupGroup]:
        """Analyze browser caches separately"""
        groups = []
        
        browsers = {
            "Google Chrome": {
                "path": Path(self.user_profile) / "AppData" / "Local" / "Google" / "Chrome" / "User Data",
                "cache_folders": ["Default/Cache", "Default/Code Cache", "Default/GPUCache"],
                "icon": "🌐"
            },
            "Microsoft Edge": {
                "path": Path(self.user_profile) / "AppData" / "Local" / "Microsoft" / "Edge" / "User Data",
                "cache_folders": ["Default/Cache", "Default/Code Cache", "Default/GPUCache"],
                "icon": "🔷"
            },
            "Mozilla Firefox": {
                "path": Path(self.user_profile) / "AppData" / "Local" / "Mozilla" / "Firefox" / "Profiles",
                "cache_folders": ["*/cache2"],
                "icon": "🦊"
            },
            "Brave Browser": {
                "path": Path(self.user_profile) / "AppData" / "Local" / "BraveSoftware" / "Brave-Browser" / "User Data",
                "cache_folders": ["Default/Cache", "Default/Code Cache"],
                "icon": "🦁"
            },
            "Opera": {
                "path": Path(self.user_profile) / "AppData" / "Local" / "Opera Software" / "Opera Stable",
                "cache_folders": ["Cache"],
                "icon": "🔴"
            }
        }
        
        for browser_name, config in browsers.items():
            group = CleanupGroup(
                name=f"Caché de {browser_name}",
                category="browser_cache",
                description=f"Archivos de caché del navegador {browser_name}",
                icon=config["icon"],
                is_safe=True
            )
            
            base_path = config["path"]
            if base_path.exists():
                for cache_pattern in config["cache_folders"]:
                    if "*" in cache_pattern:
                        # Handle wildcard patterns
                        for match in base_path.glob(cache_pattern):
                            self._scan_folder_for_group(group, match)
                    else:
                        cache_path = base_path / cache_pattern
                        if cache_path.exists():
                            self._scan_folder_for_group(group, cache_path)
            
            if group.file_count > 0:
                groups.append(group)
        
        return groups
    
    def _analyze_windows_update(self) -> CleanupGroup:
        """Analyze Windows Update cleanup files"""
        group = CleanupGroup(
            name="Archivos de Windows Update",
            category="windows_update",
            description="Archivos de instalación de actualizaciones antiguas",
            icon="🔄",
            is_safe=True
        )
        
        update_paths = [
            Path("C:/Windows/SoftwareDistribution/Download"),
            Path(self.user_profile) / "AppData" / "Local" / "Microsoft" / "Windows" / "DeliveryOptimization",
        ]
        
        for path in update_paths:
            if path.exists():
                self._scan_folder_for_group(group, path)
        
        return group
    
    def _analyze_recycle_bin(self) -> CleanupGroup:
        """Analyze Recycle Bin"""
        group = CleanupGroup(
            name="Papelera de Reciclaje",
            category="recycle_bin",
            description="Archivos eliminados en la papelera",
            icon="🗑️",
            is_safe=True
        )
        
        # Get recycle bin size using shell
        try:
            import ctypes
            from ctypes import wintypes
            
            # This is a simplified approach - get size from known recycle bin paths
            for drive in ['C', 'D', 'E']:
                recycle_path = Path(f"{drive}:/$Recycle.Bin")
                if recycle_path.exists():
                    try:
                        for user_folder in recycle_path.iterdir():
                            if user_folder.is_dir():
                                size = self._get_folder_size(user_folder)
                                group.total_size += size
                                group.file_count += sum(1 for _ in user_folder.rglob("*") if _.is_file())
                    except PermissionError:
                        continue
        except Exception as e:
            self.logger.debug(f"Could not analyze recycle bin: {e}")
        
        return group
    
    def _analyze_crash_dumps(self) -> CleanupGroup:
        """Analyze crash dump files"""
        group = CleanupGroup(
            name="Volcados de Memoria (Crash Dumps)",
            category="crash_dumps",
            description="Archivos de diagnóstico de errores del sistema",
            icon="💥",
            is_safe=True
        )
        
        dump_paths = [
            Path(self.user_profile) / "AppData" / "Local" / "CrashDumps",
            Path("C:/Windows/Minidump"),
            Path("C:/Windows/MEMORY.DMP"),
        ]
        
        for path in dump_paths:
            if path.exists():
                if path.is_file():
                    group.files.append({
                        'path': str(path),
                        'name': path.name,
                        'size': path.stat().st_size
                    })
                    group.total_size += path.stat().st_size
                    group.file_count += 1
                else:
                    self._scan_folder_for_group(group, path)
        
        return group
    
    def _analyze_thumbnails(self) -> CleanupGroup:
        """Analyze thumbnail cache"""
        group = CleanupGroup(
            name="Caché de Miniaturas",
            category="thumbnails",
            description="Miniaturas de imágenes y videos en caché",
            icon="🖼️",
            is_safe=True
        )
        
        thumb_path = Path(self.user_profile) / "AppData" / "Local" / "Microsoft" / "Windows" / "Explorer"
        if thumb_path.exists():
            for f in thumb_path.glob("thumbcache_*.db"):
                try:
                    size = f.stat().st_size
                    group.files.append({
                        'path': str(f),
                        'name': f.name,
                        'size': size
                    })
                    group.total_size += size
                    group.file_count += 1
                except PermissionError:
                    continue
        
        return group
    
    def _analyze_logs(self) -> CleanupGroup:
        """Analyze log files"""
        group = CleanupGroup(
            name="Archivos de Registro (Logs)",
            category="logs",
            description="Archivos de registro de aplicaciones y sistema",
            icon="📝",
            is_safe=True
        )
        
        log_paths = [
            Path(self.user_profile) / "AppData" / "Local",
            Path("C:/Windows/Logs"),
        ]
        
        for base_path in log_paths:
            if base_path.exists():
                try:
                    for log_file in base_path.rglob("*.log"):
                        try:
                            size = log_file.stat().st_size
                            if size > 1024:  # Only log files > 1KB
                                group.files.append({
                                    'path': str(log_file),
                                    'name': log_file.name,
                                    'size': size
                                })
                                group.total_size += size
                                group.file_count += 1
                        except PermissionError:
                            continue
                except PermissionError:
                    continue
        
        return group
    
    def _analyze_downloads_temp(self) -> CleanupGroup:
        """Analyze temporary download files"""
        group = CleanupGroup(
            name="Descargas Temporales",
            category="downloads_temp",
            description="Archivos parciales y temporales de descargas",
            icon="📥",
            is_safe=True
        )
        
        downloads = Path(self.user_profile) / "Downloads"
        if downloads.exists():
            temp_extensions = ['.tmp', '.crdownload', '.partial', '.download', '.!ut']
            for ext in temp_extensions:
                for f in downloads.glob(f"*{ext}"):
                    try:
                        size = f.stat().st_size
                        group.files.append({
                            'path': str(f),
                            'name': f.name,
                            'size': size
                        })
                        group.total_size += size
                        group.file_count += 1
                    except PermissionError:
                        continue
        
        return group
    
    def _scan_folder_for_group(self, group: CleanupGroup, folder: Path, max_depth: int = 3):
        """Scan a folder and add files to cleanup group"""
        try:
            for item in folder.rglob("*"):
                if item.is_file():
                    try:
                        size = item.stat().st_size
                        group.files.append({
                            'path': str(item),
                            'name': item.name,
                            'size': size
                        })
                        group.total_size += size
                        group.file_count += 1
                    except (PermissionError, OSError):
                        continue
        except (PermissionError, OSError):
            pass
    
    def _get_folder_size(self, folder: Path) -> int:
        """Calculate total size of a folder"""
        total = 0
        try:
            for item in folder.rglob("*"):
                if item.is_file():
                    try:
                        total += item.stat().st_size
                    except (PermissionError, OSError):
                        continue
        except (PermissionError, OSError):
            pass
        return total
    
    def uninstall_app(self, app: InstalledApp) -> Tuple[bool, str]:
        """Attempt to uninstall an application"""
        if not app.uninstall_string:
            return False, "No se encontró comando de desinstalación"
        
        try:
            self.logger.info(f"Attempting to uninstall: {app.name}")
            
            # Parse uninstall string
            uninstall_cmd = app.uninstall_string
            
            # Handle MsiExec
            if "msiexec" in uninstall_cmd.lower():
                # Add /quiet for silent uninstall attempt, but use /passive for UI
                if "/I" in uninstall_cmd:
                    uninstall_cmd = uninstall_cmd.replace("/I", "/X")
                subprocess.Popen(uninstall_cmd, shell=True)
            else:
                # Run the uninstaller
                subprocess.Popen(uninstall_cmd, shell=True)
            
            return True, f"Desinstalador iniciado para {app.name}"
        except Exception as e:
            self.logger.error(f"Uninstall error for {app.name}: {e}")
            return False, f"Error: {str(e)}"
    
    def clean_group(self, group: CleanupGroup, dry_run: bool = True) -> Tuple[int, int, List[str]]:
        """
        Clean files in a cleanup group.
        Returns: (files_deleted, bytes_freed, errors)
        """
        files_deleted = 0
        bytes_freed = 0
        errors = []
        
        for file_info in group.files:
            file_path = Path(file_info['path'])
            try:
                if dry_run:
                    self.logger.info(f"[DRY RUN] Would delete: {file_path}")
                else:
                    if file_path.exists():
                        size = file_path.stat().st_size
                        file_path.unlink()
                        files_deleted += 1
                        bytes_freed += size
                        self.logger.info(f"Deleted: {file_path}")
            except PermissionError:
                errors.append(f"Permiso denegado: {file_path.name}")
            except Exception as e:
                errors.append(f"Error {file_path.name}: {str(e)}")
        
        return files_deleted, bytes_freed, errors
    
    @staticmethod
    def format_size(bytes_size: int) -> str:
        """Format bytes to human readable"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_size < 1024.0:
                return f"{bytes_size:.1f} {unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.1f} PB"
