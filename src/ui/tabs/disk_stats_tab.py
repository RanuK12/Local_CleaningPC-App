"""
Disk Statistics Tab: Shows detailed statistics per disk/drive.
Displays apps installed, space usage by category, and visual breakdown.
"""

import os
import string
import ctypes
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFrame, QScrollArea, QGridLayout, QProgressBar, QGroupBox,
    QDialog, QListWidget, QListWidgetItem, QDialogButtonBox
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont, QCursor

from utils.logger import setup_logger
from core.app_analyzer import AppAnalyzer, InstalledApp


@dataclass
class DriveStats:
    """Statistics for a single drive"""
    drive: str  # e.g., "C:"
    total_bytes: int = 0
    used_bytes: int = 0
    free_bytes: int = 0
    
    # Breakdown by category
    apps_count: int = 0
    apps_size: int = 0
    
    documents_size: int = 0
    images_size: int = 0
    videos_size: int = 0
    music_size: int = 0
    downloads_size: int = 0
    temp_size: int = 0
    system_size: int = 0
    other_size: int = 0
    
    # Lists for detail view
    apps_list: List[InstalledApp] = field(default_factory=list)
    documents_files: List[Dict] = field(default_factory=list)
    images_files: List[Dict] = field(default_factory=list)
    videos_files: List[Dict] = field(default_factory=list)
    music_files: List[Dict] = field(default_factory=list)
    downloads_files: List[Dict] = field(default_factory=list)
    temp_files: List[Dict] = field(default_factory=list)
    
    @property
    def used_percent(self) -> float:
        if self.total_bytes == 0:
            return 0
        return (self.used_bytes / self.total_bytes) * 100
    
    @property
    def free_percent(self) -> float:
        return 100 - self.used_percent


class DiskScanWorker(QThread):
    """Worker thread for scanning disk statistics"""
    progress = Signal(str)
    finished = Signal(list)  # List[DriveStats]
    error = Signal(str)
    
    def __init__(self):
        super().__init__()
        self.analyzer = AppAnalyzer()
    
    def run(self):
        try:
            drives = self._get_available_drives()
            stats_list: List[DriveStats] = []
            
            # Get installed apps first (we'll need this for per-drive breakdown)
            self.progress.emit("📦 Obteniendo aplicaciones instaladas...")
            apps = self.analyzer.get_installed_apps()
            
            for drive in drives:
                self.progress.emit(f"📊 Analizando disco {drive}...")
                stats = self._analyze_drive(drive, apps)
                if stats:
                    stats_list.append(stats)
            
            self.finished.emit(stats_list)
            
        except Exception as e:
            self.error.emit(str(e))
    
    def _get_available_drives(self) -> List[str]:
        """Get list of available drives on Windows"""
        drives = []
        bitmask = ctypes.windll.kernel32.GetLogicalDrives()
        
        for letter in string.ascii_uppercase:
            if bitmask & 1:
                drive = f"{letter}:"
                # Check if drive is ready
                try:
                    if os.path.exists(f"{drive}\\"):
                        drives.append(drive)
                except:
                    pass
            bitmask >>= 1
        
        return drives
    
    def _analyze_drive(self, drive: str, apps: List[InstalledApp]) -> Optional[DriveStats]:
        """Analyze a single drive"""
        try:
            drive_path = f"{drive}\\"
            
            # Get disk space info
            total, used, free = self._get_disk_space(drive_path)
            
            if total == 0:
                return None
            
            stats = DriveStats(
                drive=drive,
                total_bytes=total,
                used_bytes=used,
                free_bytes=free
            )
            
            # Count apps on this drive
            for app in apps:
                if app.install_drive.upper() == drive.upper():
                    stats.apps_count += 1
                    stats.apps_size += app.size_bytes
                    stats.apps_list.append(app)
            
            # Sort apps by size
            stats.apps_list.sort(key=lambda x: x.size_bytes, reverse=True)
            
            # Analyze common folders
            user_profile = os.environ.get('USERPROFILE', '')
            
            if user_profile.upper().startswith(drive.upper()):
                # Documents
                docs_path = os.path.join(user_profile, 'Documents')
                stats.documents_size, stats.documents_files = self._get_folder_size_with_files(docs_path)
                
                # Pictures  
                pics_path = os.path.join(user_profile, 'Pictures')
                stats.images_size, stats.images_files = self._get_folder_size_with_files(pics_path)
                
                # Videos
                vids_path = os.path.join(user_profile, 'Videos')
                stats.videos_size, stats.videos_files = self._get_folder_size_with_files(vids_path)
                
                # Music
                music_path = os.path.join(user_profile, 'Music')
                stats.music_size, stats.music_files = self._get_folder_size_with_files(music_path)
                
                # Downloads
                downloads_path = os.path.join(user_profile, 'Downloads')
                stats.downloads_size, stats.downloads_files = self._get_folder_size_with_files(downloads_path)
            
            # Temp folders
            temp_paths = [
                os.environ.get('TEMP', ''),
                os.environ.get('TMP', ''),
                os.path.join(drive_path, 'Windows', 'Temp') if drive.upper() == 'C:' else ''
            ]
            for temp_path in temp_paths:
                if temp_path and temp_path.upper().startswith(drive.upper()):
                    size, files = self._get_folder_size_with_files(temp_path, max_depth=2)
                    stats.temp_size += size
                    stats.temp_files.extend(files)
            
            # Sort temp files by size
            stats.temp_files.sort(key=lambda x: x['size'], reverse=True)
            
            # Windows system (only for C:)
            if drive.upper() == 'C:':
                windows_path = os.path.join(drive_path, 'Windows')
                stats.system_size = self._get_folder_size(windows_path, max_depth=1)  # Don't go too deep
            
            # Calculate other
            known_size = (
                stats.apps_size + stats.documents_size + stats.images_size +
                stats.videos_size + stats.music_size + stats.downloads_size +
                stats.temp_size + stats.system_size
            )
            stats.other_size = max(0, stats.used_bytes - known_size)
            
            return stats
            
        except Exception as e:
            return None
    
    def _get_disk_space(self, path: str) -> Tuple[int, int, int]:
        """Get disk space info (total, used, free)"""
        try:
            import shutil
            total, used, free = shutil.disk_usage(path)
            return total, used, free
        except:
            return 0, 0, 0
    
    def _get_folder_size(self, path: str, max_depth: int = 3) -> int:
        """Get total size of a folder (limited depth for performance)"""
        total_size = 0
        
        if not os.path.exists(path):
            return 0
        
        try:
            for entry in os.scandir(path):
                try:
                    if entry.is_file(follow_symlinks=False):
                        total_size += entry.stat().st_size
                    elif entry.is_dir(follow_symlinks=False) and max_depth > 0:
                        total_size += self._get_folder_size(entry.path, max_depth - 1)
                except (PermissionError, OSError):
                    continue
        except (PermissionError, OSError):
            pass
        
        return total_size
    
    def _get_folder_size_with_files(self, path: str, max_depth: int = 3, max_files: int = 50) -> Tuple[int, List[Dict]]:
        """Get total size of a folder and list of largest files"""
        total_size = 0
        files_list = []
        
        if not os.path.exists(path):
            return 0, []
        
        try:
            for entry in os.scandir(path):
                try:
                    if entry.is_file(follow_symlinks=False):
                        size = entry.stat().st_size
                        total_size += size
                        if size > 1024 * 1024:  # Only track files > 1MB
                            files_list.append({
                                'name': entry.name,
                                'path': entry.path,
                                'size': size
                            })
                    elif entry.is_dir(follow_symlinks=False) and max_depth > 0:
                        sub_size, sub_files = self._get_folder_size_with_files(entry.path, max_depth - 1, max_files)
                        total_size += sub_size
                        files_list.extend(sub_files)
                except (PermissionError, OSError):
                    continue
        except (PermissionError, OSError):
            pass
        
        # Sort by size and limit
        files_list.sort(key=lambda x: x['size'], reverse=True)
        return total_size, files_list[:max_files]


class DiskStatsTab(QWidget):
    """Tab showing disk statistics and breakdown"""
    
    def __init__(self):
        super().__init__()
        self.logger = setup_logger("DiskStatsTab", "logs/ui.log")
        self.drive_stats: List[DriveStats] = []
        
        self._create_ui()
    
    def _create_ui(self):
        """Build the UI"""
        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)
        self.setLayout(layout)
        
        # Header
        header = QLabel("💿 Estadísticas de Discos")
        header.setStyleSheet("font-size: 16pt; font-weight: bold; color: #89b4fa;")
        layout.addWidget(header)
        
        # Control bar
        control_frame = QFrame()
        control_frame.setObjectName("controlFrame")
        control_frame.setStyleSheet("""
            QFrame#controlFrame {
                background-color: #181825;
                border-radius: 10px;
                padding: 10px;
            }
        """)
        control_layout = QHBoxLayout(control_frame)
        
        self.scan_btn = QPushButton("🔍 Analizar Discos")
        self.scan_btn.setMinimumHeight(40)
        self.scan_btn.setCursor(Qt.PointingHandCursor)
        self.scan_btn.clicked.connect(self._scan_drives)
        control_layout.addWidget(self.scan_btn)
        
        control_layout.addStretch()
        
        self.status_label = QLabel("Haz clic en Analizar para ver estadísticas de tus discos")
        self.status_label.setStyleSheet("color: #6c7086;")
        control_layout.addWidget(self.status_label)
        
        layout.addWidget(control_frame)
        
        # Scroll area for drive cards
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: 1px solid #45475a;
                border-radius: 8px;
                background-color: #181825;
            }
        """)
        
        self.drives_container = QWidget()
        self.drives_layout = QVBoxLayout(self.drives_container)
        self.drives_layout.setSpacing(16)
        self.drives_layout.setAlignment(Qt.AlignTop)
        
        # Placeholder
        placeholder = QLabel("Las estadísticas de discos aparecerán aquí después del análisis")
        placeholder.setStyleSheet("color: #6c7086; padding: 40px;")
        placeholder.setAlignment(Qt.AlignCenter)
        self.drives_layout.addWidget(placeholder)
        
        self.scroll_area.setWidget(self.drives_container)
        layout.addWidget(self.scroll_area)
    
    def _scan_drives(self):
        """Start scanning drives"""
        self.scan_btn.setEnabled(False)
        self.status_label.setText("⏳ Analizando discos...")
        self.status_label.setStyleSheet("color: #89b4fa;")
        
        self.worker = DiskScanWorker()
        self.worker.progress.connect(lambda msg: self.status_label.setText(msg))
        self.worker.finished.connect(self._on_scan_finished)
        self.worker.error.connect(self._on_scan_error)
        self.worker.start()
    
    def _on_scan_finished(self, stats_list: List[DriveStats]):
        """Handle scan completion"""
        self.drive_stats = stats_list
        self.scan_btn.setEnabled(True)
        
        # Clear existing widgets safely
        for i in reversed(range(self.drives_layout.count())):
            item = self.drives_layout.itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()
        
        if not stats_list:
            self.status_label.setText("❌ No se encontraron discos")
            self.status_label.setStyleSheet("color: #f38ba8;")
            return
        
        total_space = sum(s.total_bytes for s in stats_list)
        total_used = sum(s.used_bytes for s in stats_list)
        
        self.status_label.setText(
            f"✅ {len(stats_list)} discos • "
            f"Total: {self._format_size(total_space)} • "
            f"Usado: {self._format_size(total_used)} ({(total_used/total_space*100):.1f}%)"
        )
        self.status_label.setStyleSheet("color: #a6e3a1;")
        
        # Create drive cards
        for stats in stats_list:
            card = self._create_drive_card(stats)
            self.drives_layout.addWidget(card)
        
        self.drives_layout.addStretch()
    
    def _on_scan_error(self, error: str):
        """Handle scan error"""
        self.scan_btn.setEnabled(True)
        self.status_label.setText(f"❌ Error: {error}")
        self.status_label.setStyleSheet("color: #f38ba8;")
    
    def _create_drive_card(self, stats: DriveStats) -> QFrame:
        """Create a card for a drive's statistics"""
        card = QFrame()
        card.setObjectName("driveCard")
        card.setStyleSheet("""
            QFrame#driveCard {
                background-color: #1e1e2e;
                border: 1px solid #45475a;
                border-radius: 10px;
                padding: 12px;
            }
        """)
        
        layout = QVBoxLayout(card)
        layout.setSpacing(12)
        
        # Header with drive info
        header_layout = QHBoxLayout()
        
        drive_icon = QLabel("💿")
        drive_icon.setStyleSheet("font-size: 28pt;")
        header_layout.addWidget(drive_icon)
        
        drive_info = QVBoxLayout()
        drive_name = QLabel(f"Unidad {stats.drive}")
        drive_name.setStyleSheet("font-size: 14pt; font-weight: bold; color: #cdd6f4;")
        drive_info.addWidget(drive_name)
        
        space_text = f"{self._format_size(stats.used_bytes)} usado de {self._format_size(stats.total_bytes)} • {self._format_size(stats.free_bytes)} libre"
        space_label = QLabel(space_text)
        space_label.setStyleSheet("color: #6c7086; font-size: 10pt;")
        drive_info.addWidget(space_label)
        
        header_layout.addLayout(drive_info)
        header_layout.addStretch()
        
        # Usage percentage badge
        percent_color = "#a6e3a1" if stats.used_percent < 70 else ("#fab387" if stats.used_percent < 90 else "#f38ba8")
        percent_badge = QLabel(f"{stats.used_percent:.1f}%")
        percent_badge.setStyleSheet(f"""
            background-color: {percent_color}20;
            color: {percent_color};
            padding: 8px 16px;
            border-radius: 6px;
            font-weight: bold;
            font-size: 12pt;
        """)
        header_layout.addWidget(percent_badge)
        
        layout.addLayout(header_layout)
        
        # Progress bar for overall usage
        progress = QProgressBar()
        progress.setMaximum(100)
        progress.setValue(int(stats.used_percent))
        progress.setTextVisible(False)
        progress.setFixedHeight(8)
        progress.setStyleSheet(f"""
            QProgressBar {{
                border: none;
                border-radius: 4px;
                background-color: #313244;
            }}
            QProgressBar::chunk {{
                background-color: {percent_color};
                border-radius: 4px;
            }}
        """)
        layout.addWidget(progress)
        
        # Category breakdown
        breakdown_frame = QFrame()
        breakdown_frame.setStyleSheet("background-color: #181825; border-radius: 8px; padding: 8px;")
        breakdown_grid = QGridLayout(breakdown_frame)
        breakdown_grid.setSpacing(8)
        
        # Categories with their data lists for detail view
        categories = [
            ("📦 Aplicaciones", stats.apps_size, f"{stats.apps_count} apps", "#89b4fa", "apps", stats.apps_list),
            ("📄 Documentos", stats.documents_size, None, "#a6e3a1", "documents", stats.documents_files),
            ("🖼️ Imágenes", stats.images_size, None, "#fab387", "images", stats.images_files),
            ("🎬 Videos", stats.videos_size, None, "#f38ba8", "videos", stats.videos_files),
            ("🎵 Música", stats.music_size, None, "#cba6f7", "music", stats.music_files),
            ("⬇️ Descargas", stats.downloads_size, None, "#94e2d5", "downloads", stats.downloads_files),
            ("🗑️ Temp/Cache", stats.temp_size, None, "#f9e2af", "temp", stats.temp_files),
            ("⚙️ Sistema", stats.system_size, None, "#6c7086", "system", None),
            ("📁 Otros", stats.other_size, None, "#9399b2", "other", None),
        ]
        
        for i, (name, size, extra, color, cat_type, data_list) in enumerate(categories):
            row = i // 3
            col = i % 3
            
            cat_widget = self._create_category_item(name, size, stats.used_bytes, extra, color, cat_type, data_list)
            breakdown_grid.addWidget(cat_widget, row, col)
        
        layout.addWidget(breakdown_frame)
        
        return card
    
    def _create_category_item(self, name: str, size: int, total_used: int, extra: Optional[str], color: str, cat_type: str, data_list) -> QWidget:
        """Create a clickable category item widget"""
        widget = QFrame()
        widget.setStyleSheet(f"""
            QFrame {{
                border-radius: 6px;
                padding: 4px;
            }}
            QFrame:hover {{
                background-color: #313244;
            }}
        """)
        widget.setCursor(QCursor(Qt.PointingHandCursor))
        
        layout = QVBoxLayout(widget)
        layout.setSpacing(2)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # Name
        name_label = QLabel(name)
        name_label.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 10pt;")
        layout.addWidget(name_label)
        
        # Size
        size_label = QLabel(self._format_size(size))
        size_label.setStyleSheet("color: #cdd6f4; font-size: 11pt; font-weight: bold;")
        layout.addWidget(size_label)
        
        # Percentage
        percent = (size / total_used * 100) if total_used > 0 else 0
        percent_text = f"{percent:.1f}%"
        if extra:
            percent_text += f" • {extra}"
        
        percent_label = QLabel(percent_text)
        percent_label.setStyleSheet("color: #6c7086; font-size: 9pt;")
        layout.addWidget(percent_label)
        
        # Click hint
        if data_list is not None:
            hint = QLabel("🔍 Click para ver detalle")
            hint.setStyleSheet("color: #45475a; font-size: 8pt;")
            layout.addWidget(hint)
        
        # Make clickable
        widget.mousePressEvent = lambda e: self._show_category_detail(name, cat_type, data_list, color)
        
        return widget
    
    def _show_category_detail(self, name: str, cat_type: str, data_list, color: str):
        """Show detail dialog for a category"""
        if data_list is None:
            return
        
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Detalle: {name}")
        dialog.setMinimumSize(600, 400)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #1e1e2e;
            }
            QListWidget {
                background-color: #181825;
                border: 1px solid #45475a;
                border-radius: 8px;
                color: #cdd6f4;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #313244;
            }
            QListWidget::item:hover {
                background-color: #313244;
            }
        """)
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(12)
        
        # Header
        header = QLabel(f"{name}")
        header.setStyleSheet(f"font-size: 14pt; font-weight: bold; color: {color};")
        layout.addWidget(header)
        
        # List widget
        list_widget = QListWidget()
        
        if cat_type == "apps":
            # Show apps list
            for app in data_list:
                size_str = self._format_size(app.size_bytes) if app.size_bytes > 0 else "Tamaño desconocido"
                item = QListWidgetItem(f"📦 {app.name}\n   {size_str} • {app.publisher[:30] if app.publisher else 'Editor desconocido'}")
                list_widget.addItem(item)
        else:
            # Show files list
            for file_info in data_list:
                size_str = self._format_size(file_info['size'])
                item = QListWidgetItem(f"📄 {file_info['name']}\n   {size_str} • {file_info['path'][:60]}...")
                list_widget.addItem(item)
        
        if list_widget.count() == 0:
            item = QListWidgetItem("No hay elementos para mostrar")
            item.setForeground(Qt.gray)
            list_widget.addItem(item)
        
        layout.addWidget(list_widget)
        
        # Summary
        total_items = len(data_list) if data_list else 0
        summary = QLabel(f"Total: {total_items} elementos")
        summary.setStyleSheet("color: #6c7086;")
        layout.addWidget(summary)
        
        # Close button
        btn_box = QDialogButtonBox(QDialogButtonBox.Close)
        btn_box.rejected.connect(dialog.close)
        btn_box.setStyleSheet("""
            QPushButton {
                background-color: #45475a;
                color: #cdd6f4;
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #89b4fa;
                color: #1e1e2e;
            }
        """)
        layout.addWidget(btn_box)
        
        dialog.exec()
    
    def _format_size(self, size_bytes: int) -> str:
        """Format bytes to human readable string"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} PB"
