"""Inventory Tab - File scanning and browsing"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QCheckBox, QComboBox,
    QLineEdit, QSpinBox, QProgressBar, QMessageBox, QFrame
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from typing import List
from pathlib import Path

from core.scanner import DiskScanner
from db.database import Database
from db.models import FileInfo
from utils.config import Config
from utils.logger import setup_logger


class ScannerWorker(QThread):
    """Worker thread for disk scanning with real-time progress updates."""
    
    progress = Signal(dict)
    file_found = Signal(str)  # Emits current file being scanned
    finished = Signal(dict)
    error = Signal(str)
    
    def __init__(self, config: Config, paths: List[str]):
        super().__init__()
        self.config = config
        self.paths = paths
        self.scanner = None
        self._is_paused = False
        self._is_cancelled = False
    
    def run(self):
        """Execute scan in background thread."""
        try:
            db = Database()
            self.scanner = DiskScanner(db, self.config)
            
            # Connect scanner state to our controls
            self.scanner.is_cancelled = self._is_cancelled
            self.scanner.is_paused = self._is_paused
            
            stats = self.scanner.scan_paths(
                self.paths,
                progress_callback=self._on_progress,
                error_callback=self._on_error  # Filter errors before emitting
            )
            self.finished.emit(stats)
        except Exception as e:
            self.error.emit(str(e))
    
    def _on_error(self, error_msg: str):
        """Filter errors - only emit important ones to UI."""
        # Skip permission errors - these are handled silently
        if 'permiso denegado' in error_msg.lower() or 'permission denied' in error_msg.lower():
            return
        # Skip access denied
        if 'access denied' in error_msg.lower() or 'acceso denegado' in error_msg.lower():
            return
        # Emit other errors
        self.error.emit(error_msg)
    
    def _on_progress(self, data: dict):
        """Handle progress updates from scanner."""
        self.progress.emit(data)
        if 'current_path' in data:
            self.file_found.emit(data['current_path'])
    
    def pause(self):
        """Pause the scan."""
        self._is_paused = True
        if self.scanner:
            self.scanner.is_paused = True
    
    def resume(self):
        """Resume the scan."""
        self._is_paused = False
        if self.scanner:
            self.scanner.is_paused = False
    
    def cancel(self):
        """Cancel the scan."""
        self._is_cancelled = True
        if self.scanner:
            self.scanner.is_cancelled = True


class InventoryTab(QWidget):
    """Inventory tab with real-time scanning progress."""
    
    scan_finished = Signal(dict)
    
    def __init__(self, db: Database, config: Config):
        super().__init__()
        
        self.db = db
        self.config = config
        self.logger = setup_logger("InventoryTab", "logs/ui.log")
        self.scanner_worker = None
        self.is_paused = False
        
        self._create_ui()
    
    def _create_ui(self):
        """Build the inventory tab UI."""
        
        layout = QVBoxLayout()
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)
        self.setLayout(layout)
        
        # Control panel card
        control_card = QFrame()
        control_card.setObjectName("controlCard")
        control_card.setStyleSheet("""
            QFrame#controlCard {
                background-color: #181825;
                border-radius: 12px;
            }
        """)
        control_layout = QHBoxLayout(control_card)
        control_layout.setContentsMargins(16, 12, 16, 12)
        
        # Drive selection
        disk_label = QLabel("📀 Drives:")
        disk_label.setStyleSheet("font-weight: 600; color: #89b4fa;")
        control_layout.addWidget(disk_label)
        
        self.disk_c_check = QCheckBox("C:\\")
        self.disk_c_check.setChecked(True)
        control_layout.addWidget(self.disk_c_check)
        
        self.disk_d_check = QCheckBox("D:\\")
        control_layout.addWidget(self.disk_d_check)
        
        self.disk_e_check = QCheckBox("E:\\")
        control_layout.addWidget(self.disk_e_check)
        
        control_layout.addStretch()
        
        # Scan button
        self.scan_btn = QPushButton("▶  Start Scan")
        self.scan_btn.setMinimumWidth(140)
        self.scan_btn.setMinimumHeight(36)
        self.scan_btn.setCursor(Qt.PointingHandCursor)
        self.scan_btn.clicked.connect(self._start_scan)
        control_layout.addWidget(self.scan_btn)
        
        # Pause/Resume button
        self.pause_btn = QPushButton("⏸  Pause")
        self.pause_btn.setMinimumHeight(36)
        self.pause_btn.setEnabled(False)
        self.pause_btn.setCursor(Qt.PointingHandCursor)
        self.pause_btn.clicked.connect(self._toggle_pause)
        control_layout.addWidget(self.pause_btn)
        
        # Cancel button
        self.cancel_btn = QPushButton("✕  Cancel")
        self.cancel_btn.setMinimumHeight(36)
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setCursor(Qt.PointingHandCursor)
        self.cancel_btn.setStyleSheet("background-color: #f38ba8; color: #1e1e2e;")
        self.cancel_btn.clicked.connect(self._cancel_scan)
        control_layout.addWidget(self.cancel_btn)
        
        layout.addWidget(control_card)
        
        # Progress section (initially hidden)
        self.progress_card = QFrame()
        self.progress_card.setObjectName("progressCard")
        self.progress_card.setStyleSheet("""
            QFrame#progressCard {
                background-color: #181825;
                border-radius: 12px;
            }
        """)
        self.progress_card.setVisible(False)
        progress_layout = QVBoxLayout(self.progress_card)
        progress_layout.setContentsMargins(16, 12, 16, 12)
        
        # Progress header
        progress_header = QHBoxLayout()
        self.progress_title = QLabel("🔄 Scanning in progress...")
        self.progress_title.setStyleSheet("font-weight: 600; color: #89b4fa; font-size: 11pt;")
        progress_header.addWidget(self.progress_title)
        progress_header.addStretch()
        self.progress_percent = QLabel("0%")
        self.progress_percent.setStyleSheet("font-weight: bold; color: #a6e3a1; font-size: 14pt;")
        progress_header.addWidget(self.progress_percent)
        progress_layout.addLayout(progress_header)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimumHeight(12)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setRange(0, 0)  # Indeterminate initially
        progress_layout.addWidget(self.progress_bar)
        
        # Current file being scanned
        self.current_file_label = QLabel("Preparing scan...")
        self.current_file_label.setStyleSheet("color: #6c7086; font-size: 9pt;")
        self.current_file_label.setWordWrap(True)
        progress_layout.addWidget(self.current_file_label)
        
        # Stats during scan
        stats_layout = QHBoxLayout()
        self.files_scanned_label = QLabel("Files: 0")
        self.files_scanned_label.setStyleSheet("color: #cdd6f4;")
        stats_layout.addWidget(self.files_scanned_label)
        
        self.size_scanned_label = QLabel("Size: 0 MB")
        self.size_scanned_label.setStyleSheet("color: #cdd6f4;")
        stats_layout.addWidget(self.size_scanned_label)
        
        self.scan_speed_label = QLabel("Speed: -- files/sec")
        self.scan_speed_label.setStyleSheet("color: #6c7086;")
        stats_layout.addWidget(self.scan_speed_label)
        stats_layout.addStretch()
        progress_layout.addLayout(stats_layout)
        
        layout.addWidget(self.progress_card)
        
        # Filter panel
        filter_card = QFrame()
        filter_card.setObjectName("filterCard")
        filter_card.setStyleSheet("""
            QFrame#filterCard {
                background-color: #181825;
                border-radius: 12px;
            }
        """)
        filter_layout = QHBoxLayout(filter_card)
        filter_layout.setContentsMargins(16, 12, 16, 12)
        
        search_label = QLabel("🔍 Search:")
        search_label.setStyleSheet("font-weight: 600; color: #89b4fa;")
        filter_layout.addWidget(search_label)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filter by name or path...")
        self.search_input.setMinimumWidth(250)
        self.search_input.textChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.search_input)
        
        filter_layout.addSpacing(20)
        
        size_label = QLabel("📏 Min size (MB):")
        size_label.setStyleSheet("font-weight: 600; color: #89b4fa;")
        filter_layout.addWidget(size_label)
        
        self.size_spinbox = QSpinBox()
        self.size_spinbox.setValue(0)
        self.size_spinbox.setMaximum(1000000)
        self.size_spinbox.setMinimumWidth(100)
        self.size_spinbox.valueChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.size_spinbox)
        
        filter_layout.addStretch()
        layout.addWidget(filter_card)
        
        # Results table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "📄 Name", "📁 Path", "📊 Size", "📅 Modified", "🏷️ Type"
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.MultiSelection)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)
        
        # Status bar
        status_card = QFrame()
        status_card.setObjectName("statusCard")
        status_card.setStyleSheet("""
            QFrame#statusCard {
                background-color: #181825;
                border-radius: 8px;
            }
        """)
        status_layout = QHBoxLayout(status_card)
        status_layout.setContentsMargins(16, 10, 16, 10)
        
        self.status_label = QLabel("✨ Ready to scan your drives")
        self.status_label.setStyleSheet("color: #a6e3a1; font-weight: 500;")
        status_layout.addWidget(self.status_label)
        
        status_layout.addStretch()
        
        self.file_count_label = QLabel("")
        self.file_count_label.setStyleSheet("color: #6c7086;")
        status_layout.addWidget(self.file_count_label)
        
        layout.addWidget(status_card)
        
        # Timer for speed calculation
        self.scan_start_time = None
        self.last_file_count = 0
    
    def _start_scan(self):
        """Start disk scanning."""
        paths = []
        if self.disk_c_check.isChecked():
            paths.append("C:\\")
        if self.disk_d_check.isChecked():
            paths.append("D:\\")
        if self.disk_e_check.isChecked():
            paths.append("E:\\")
        
        if not paths:
            QMessageBox.warning(self, "Warning", "Please select at least one drive to scan.")
            return
        
        self.logger.info(f"Starting scan of: {paths}")
        
        # Update UI state
        self.scan_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.pause_btn.setText("⏸  Pause")
        self.pause_btn.setStyleSheet("background-color: #fab387; color: #1e1e2e;")
        self.cancel_btn.setEnabled(True)
        self.is_paused = False
        
        # Show progress section
        self.progress_card.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.progress_title.setText(f"🔄 Scanning {', '.join(paths)}...")
        self.progress_percent.setText("--")
        self.current_file_label.setText("Starting scan...")
        self.files_scanned_label.setText("Files: 0")
        self.size_scanned_label.setText("Size: 0 MB")
        self.scan_speed_label.setText("Speed: calculating...")
        
        self.status_label.setText("🔄 Scan in progress...")
        self.status_label.setStyleSheet("color: #89b4fa; font-weight: 500;")
        
        # Track timing
        import time
        self.scan_start_time = time.time()
        self.last_file_count = 0
        
        # Create and start worker
        self.scanner_worker = ScannerWorker(self.config, paths)
        self.scanner_worker.progress.connect(self._on_progress)
        self.scanner_worker.file_found.connect(self._on_file_found)
        self.scanner_worker.finished.connect(self._on_scan_finished)
        self.scanner_worker.error.connect(self._on_error)
        self.scanner_worker.start()
    
    def _toggle_pause(self):
        """Toggle pause/resume scan."""
        if not self.scanner_worker:
            return
        
        if self.is_paused:
            # Resume
            self.scanner_worker.resume()
            self.is_paused = False
            self.pause_btn.setText("⏸  Pause")
            self.pause_btn.setStyleSheet("background-color: #fab387; color: #1e1e2e;")
            self.progress_title.setText("🔄 Scanning resumed...")
            self.status_label.setText("🔄 Scan resumed")
        else:
            # Pause
            self.scanner_worker.pause()
            self.is_paused = True
            self.pause_btn.setText("▶  Resume")
            self.pause_btn.setStyleSheet("background-color: #a6e3a1; color: #1e1e2e;")
            self.progress_title.setText("⏸ Scan paused")
            self.status_label.setText("⏸ Scan paused - click Resume to continue")
    
    def _cancel_scan(self):
        """Cancel the current scan."""
        if self.scanner_worker:
            reply = QMessageBox.question(
                self, "Cancel Scan",
                "Are you sure you want to cancel the scan?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.scanner_worker.cancel()
                self.status_label.setText("❌ Scan cancelled")
                self.status_label.setStyleSheet("color: #f38ba8; font-weight: 500;")
                self._reset_ui_after_scan()
    
    def _on_progress(self, stats: dict):
        """Handle progress updates from scanner."""
        import time
        
        file_count = stats.get('file_count', 0)
        total_size = stats.get('total_size', 0)
        
        # Update labels
        self.files_scanned_label.setText(f"Files: {file_count:,}")
        size_mb = total_size / (1024 * 1024)
        if size_mb > 1024:
            self.size_scanned_label.setText(f"Size: {size_mb/1024:.2f} GB")
        else:
            self.size_scanned_label.setText(f"Size: {size_mb:.1f} MB")
        
        # Calculate speed
        if self.scan_start_time:
            elapsed = time.time() - self.scan_start_time
            if elapsed > 0:
                speed = file_count / elapsed
                self.scan_speed_label.setText(f"Speed: {speed:.0f} files/sec")
    
    def _on_file_found(self, file_path: str):
        """Update current file being scanned."""
        # Truncate path for display
        if len(file_path) > 80:
            display_path = file_path[:30] + "..." + file_path[-45:]
        else:
            display_path = file_path
        self.current_file_label.setText(f"📁 {display_path}")
    
    def _on_scan_finished(self, stats: dict):
        """Handle scan completion."""
        self._reset_ui_after_scan()
        
        status = stats.get('status', 'unknown')
        file_count = stats.get('file_count', 0)
        total_size = stats.get('total_size', 0)
        duration = stats.get('duration', 0)
        
        if status == 'completed':
            size_str = f"{total_size / (1024*1024):.1f} MB"
            if total_size > 1024*1024*1024:
                size_str = f"{total_size / (1024*1024*1024):.2f} GB"
            
            self.status_label.setText(
                f"✅ Scan completed: {file_count:,} files ({size_str}) in {duration:.1f}s"
            )
            self.status_label.setStyleSheet("color: #a6e3a1; font-weight: 500;")
            self.file_count_label.setText(f"{file_count:,} files indexed")
            
            # Load results into table
            self._load_files()
        elif status == 'cancelled':
            self.status_label.setText("❌ Scan was cancelled")
            self.status_label.setStyleSheet("color: #f38ba8; font-weight: 500;")
        else:
            self.status_label.setText(f"⚠️ Scan ended with status: {status}")
            self.status_label.setStyleSheet("color: #fab387; font-weight: 500;")
        
        self.scan_finished.emit(stats)
    
    def _reset_ui_after_scan(self):
        """Reset UI elements after scan ends."""
        self.scan_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.pause_btn.setText("⏸  Pause")
        self.cancel_btn.setEnabled(False)
        self.progress_card.setVisible(False)
        self.is_paused = False
    
    def _on_error(self, error: str):
        """Handle scan errors."""
        self.current_file_label.setText(f"⚠️ {error[:70]}")
        self.current_file_label.setStyleSheet("color: #f38ba8; font-size: 9pt;")
        self.logger.error(f"Scan error: {error}")
    
    def _load_files(self):
        """Carga archivos en tabla"""
        files = self.db.get_all_files(exclude_dirs=True)
        
        self.table.setRowCount(0)
        
        for file_info in files[:1000]:  # Limitar para performance
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            self.table.setItem(row, 0, QTableWidgetItem(file_info.name[:30]))
            self.table.setItem(row, 1, QTableWidgetItem(str(file_info.path)[:50]))
            self.table.setItem(row, 2, QTableWidgetItem(
                f"{file_info.size / 1024 / 1024:.2f} MB"
            ))
            self.table.setItem(row, 3, QTableWidgetItem(
                file_info.modified_time.strftime("%Y-%m-%d") if file_info.modified_time else ""
            ))
            self.table.setItem(row, 4, QTableWidgetItem(file_info.extension or ""))
    
    def _apply_filters(self):
        """Aplica filtros de búsqueda"""
        search_text = self.search_input.text().lower()
        min_size = self.size_spinbox.value() * 1024 * 1024
        
        for row in range(self.table.rowCount()):
            show = True
            
            # Filtro de búsqueda
            name_item = self.table.item(row, 0)
            if name_item and search_text and search_text not in name_item.text().lower():
                show = False
            
            # Filtro de tamaño
            size_item = self.table.item(row, 2)
            if size_item and min_size > 0:
                try:
                    size_mb = float(size_item.text().split()[0])
                    if size_mb * 1024 * 1024 < min_size:
                        show = False
                except:
                    pass
            
            self.table.setRowHidden(row, not show)
