"""
Analysis Tab - Smart file analysis with professional UX/UI
Analyzes files for duplicates, large files, old files, and temp files
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QCheckBox, QLabel, QProgressBar, QFrame, QHeaderView,
    QMenu, QGroupBox, QGridLayout, QSizePolicy, QMessageBox
)
from PySide6.QtCore import Qt, QThread, Signal, QSize
from PySide6.QtGui import QColor, QIcon, QAction, QCursor
import os
from datetime import datetime, timedelta


class StatCard(QFrame):
    """Visual card component for displaying statistics"""
    
    def __init__(self, title: str, value: str = "0", icon: str = "📊", color: str = "#89b4fa"):
        super().__init__()
        self.color = color
        self.setup_ui(title, value, icon)
        
    def setup_ui(self, title: str, value: str, icon: str):
        self.setStyleSheet(f"""
            StatCard {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #313244, stop:1 #1e1e2e);
                border: 1px solid {self.color}40;
                border-radius: 12px;
                padding: 8px;
            }}
            StatCard:hover {{
                border: 1px solid {self.color}80;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3a3a4e, stop:1 #252536);
            }}
        """)
        self.setMinimumSize(140, 90)
        self.setMaximumHeight(100)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)
        
        # Header with icon
        header = QHBoxLayout()
        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 18px; background: transparent; border: none;")
        title_label = QLabel(title)
        title_label.setStyleSheet(f"color: #a6adc8; font-size: 11px; font-weight: 500; background: transparent; border: none;")
        header.addWidget(icon_label)
        header.addWidget(title_label)
        header.addStretch()
        
        # Value
        self.value_label = QLabel(value)
        self.value_label.setStyleSheet(f"color: {self.color}; font-size: 24px; font-weight: bold; background: transparent; border: none;")
        
        layout.addLayout(header)
        layout.addWidget(self.value_label)
        layout.addStretch()
        
    def set_value(self, value: str):
        self.value_label.setText(value)


class AnalysisWorker(QThread):
    """Background worker for file analysis"""
    progress = Signal(int, str)  # percentage, message
    finished = Signal(list)
    
    def __init__(self, db, rules: dict):
        super().__init__()
        self.db = db
        self.rules = rules
        self._is_cancelled = False
        
    def cancel(self):
        self._is_cancelled = True
        
    def run(self):
        results = []
        try:
            cursor = self.db.conn.cursor()
            total_rules = sum(1 for v in self.rules.values() if v)
            current_rule = 0
            
            # Duplicate files analysis
            if self.rules.get('duplicates') and not self._is_cancelled:
                self.progress.emit(int((current_rule / max(total_rules, 1)) * 100), "Searching for duplicates...")
                cursor.execute("""
                    SELECT path, size, hash FROM files 
                    WHERE hash IN (
                        SELECT hash FROM files 
                        WHERE hash IS NOT NULL AND hash != ''
                        GROUP BY hash HAVING COUNT(*) > 1
                    )
                    ORDER BY hash, size DESC
                """)
                for row in cursor.fetchall():
                    if self._is_cancelled:
                        break
                    results.append({
                        'path': row[0],
                        'size': row[1],
                        'reason': 'Duplicate file',
                        'risk': 'medium',
                        'hash': row[2]
                    })
                current_rule += 1
            
            # Large files analysis (> 500MB)
            if self.rules.get('large_files') and not self._is_cancelled:
                self.progress.emit(int((current_rule / max(total_rules, 1)) * 100), "Finding large files...")
                cursor.execute("""
                    SELECT path, size FROM files 
                    WHERE size > 524288000
                    ORDER BY size DESC
                    LIMIT 100
                """)
                for row in cursor.fetchall():
                    if self._is_cancelled:
                        break
                    results.append({
                        'path': row[0],
                        'size': row[1],
                        'reason': 'Large file (>500MB)',
                        'risk': 'low'
                    })
                current_rule += 1
            
            # Old files analysis (> 2 years)
            if self.rules.get('old_files') and not self._is_cancelled:
                self.progress.emit(int((current_rule / max(total_rules, 1)) * 100), "Finding old files...")
                two_years_ago = (datetime.now() - timedelta(days=730)).timestamp()
                cursor.execute("""
                    SELECT path, size, modified FROM files 
                    WHERE modified < ?
                    ORDER BY modified ASC
                    LIMIT 100
                """, (two_years_ago,))
                for row in cursor.fetchall():
                    if self._is_cancelled:
                        break
                    results.append({
                        'path': row[0],
                        'size': row[1],
                        'reason': 'Old file (>2 years)',
                        'risk': 'low'
                    })
                current_rule += 1
            
            # Temporary files analysis
            if self.rules.get('temp_files') and not self._is_cancelled:
                self.progress.emit(int((current_rule / max(total_rules, 1)) * 100), "Finding temporary files...")
                temp_patterns = ['%.tmp', '%.temp', '%~%', '%.bak', '%.old', '%.cache']
                for pattern in temp_patterns:
                    if self._is_cancelled:
                        break
                    cursor.execute("""
                        SELECT path, size FROM files 
                        WHERE LOWER(path) LIKE ?
                        LIMIT 50
                    """, (pattern,))
                    for row in cursor.fetchall():
                        results.append({
                            'path': row[0],
                            'size': row[1],
                            'reason': 'Temporary file',
                            'risk': 'high'
                        })
                current_rule += 1
            
            self.progress.emit(100, "Analysis complete!")
            
        except Exception as e:
            self.progress.emit(100, f"Error: {str(e)}")
            
        self.finished.emit(results)


class AnalysisTab(QWidget):
    """Smart file analysis tab with professional UX"""
    
    # Signal to send files to cleanup tab
    send_to_cleanup = Signal(list)
    
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.worker = None
        self.results = []
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        
        # Header section
        header = QHBoxLayout()
        title = QLabel("🔍 Smart File Analysis")
        title.setStyleSheet("""
            font-size: 20px;
            font-weight: bold;
            color: #cdd6f4;
        """)
        
        subtitle = QLabel("Identify files that can be safely removed to free up space")
        subtitle.setStyleSheet("color: #6c7086; font-size: 12px;")
        
        header_text = QVBoxLayout()
        header_text.addWidget(title)
        header_text.addWidget(subtitle)
        header_text.setSpacing(4)
        
        header.addLayout(header_text)
        header.addStretch()
        layout.addLayout(header)
        
        # Stats cards row
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(12)
        
        self.stat_total = StatCard("Files Found", "0", "📁", "#89b4fa")
        self.stat_size = StatCard("Total Size", "0 B", "💾", "#a6e3a1")
        self.stat_duplicates = StatCard("Duplicates", "0", "📋", "#f9e2af")
        self.stat_risk = StatCard("High Risk", "0", "⚠️", "#f38ba8")
        
        stats_layout.addWidget(self.stat_total)
        stats_layout.addWidget(self.stat_size)
        stats_layout.addWidget(self.stat_duplicates)
        stats_layout.addWidget(self.stat_risk)
        stats_layout.addStretch()
        
        layout.addLayout(stats_layout)
        
        # Analysis rules section
        rules_group = QGroupBox("Analysis Rules")
        rules_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px;
            }
        """)
        
        rules_layout = QHBoxLayout(rules_group)
        rules_layout.setContentsMargins(16, 20, 16, 12)
        rules_layout.setSpacing(24)
        
        self.check_duplicates = QCheckBox("🔄 Duplicate Files")
        self.check_duplicates.setChecked(True)
        self.check_duplicates.setToolTip("Find files with identical content (same hash)")
        
        self.check_large = QCheckBox("📦 Large Files (>500MB)")
        self.check_large.setChecked(True)
        self.check_large.setToolTip("Find files larger than 500MB")
        
        self.check_old = QCheckBox("📅 Old Files (>2 years)")
        self.check_old.setChecked(False)
        self.check_old.setToolTip("Find files not modified in over 2 years")
        
        self.check_temp = QCheckBox("🗑️ Temporary Files")
        self.check_temp.setChecked(True)
        self.check_temp.setToolTip("Find .tmp, .temp, .bak, .cache files")
        
        for cb in [self.check_duplicates, self.check_large, self.check_old, self.check_temp]:
            cb.setStyleSheet("""
                QCheckBox {
                    color: #cdd6f4;
                    spacing: 8px;
                    font-size: 13px;
                }
                QCheckBox::indicator {
                    width: 18px;
                    height: 18px;
                    border-radius: 4px;
                    border: 2px solid #6c7086;
                    background: #1e1e2e;
                }
                QCheckBox::indicator:checked {
                    background: #89b4fa;
                    border-color: #89b4fa;
                }
                QCheckBox::indicator:hover {
                    border-color: #89b4fa;
                }
            """)
            rules_layout.addWidget(cb)
        
        rules_layout.addStretch()
        layout.addWidget(rules_group)
        
        # Progress section
        progress_frame = QFrame()
        progress_frame.setStyleSheet("""
            QFrame {
                background: #1e1e2e;
                border-radius: 8px;
                padding: 8px;
            }
        """)
        progress_layout = QHBoxLayout(progress_frame)
        progress_layout.setContentsMargins(12, 8, 12, 8)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background: #313244;
                border-radius: 4px;
                border: none;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #89b4fa, stop:1 #b4befe);
                border-radius: 4px;
            }
        """)
        
        self.progress_label = QLabel("Ready to analyze")
        self.progress_label.setStyleSheet("color: #6c7086; font-size: 12px;")
        
        progress_layout.addWidget(self.progress_bar, 1)
        progress_layout.addWidget(self.progress_label)
        
        layout.addWidget(progress_frame)
        
        # Results table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["", "File Path", "Size", "Reason", "Risk"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        
        # Table styling
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #1e1e2e;
                alternate-background-color: #232334;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 8px;
                gridline-color: #313244;
                selection-background-color: #45475a;
            }
            QTableWidget::item {
                padding: 8px;
                border: none;
            }
            QTableWidget::item:selected {
                background-color: #45475a;
            }
            QHeaderView::section {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #313244, stop:1 #1e1e2e);
                color: #89b4fa;
                font-weight: bold;
                padding: 10px 8px;
                border: none;
                border-bottom: 2px solid #89b4fa;
            }
        """)
        
        # Configure header
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.setColumnWidth(0, 40)
        
        layout.addWidget(self.table, 1)
        
        # Action buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(12)
        
        # Selection buttons
        self.btn_select_all = QPushButton("☑️ Select All")
        self.btn_select_all.setToolTip("Select all files in the list")
        self.btn_select_all.clicked.connect(self.select_all)
        
        self.btn_deselect_all = QPushButton("☐ Deselect All")
        self.btn_deselect_all.setToolTip("Deselect all files")
        self.btn_deselect_all.clicked.connect(self.deselect_all)
        
        buttons_layout.addWidget(self.btn_select_all)
        buttons_layout.addWidget(self.btn_deselect_all)
        buttons_layout.addStretch()
        
        # Main action buttons
        self.btn_analyze = QPushButton("🔍 Start Analysis")
        self.btn_analyze.setToolTip("Begin scanning for files based on selected rules")
        self.btn_analyze.setMinimumWidth(150)
        self.btn_analyze.clicked.connect(self.start_analysis)
        
        self.btn_cancel = QPushButton("⏹️ Cancel")
        self.btn_cancel.setToolTip("Stop the current analysis")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self.cancel_analysis)
        
        self.btn_send_cleanup = QPushButton("📤 Send to Cleanup")
        self.btn_send_cleanup.setToolTip("Send selected files to the Cleanup tab for processing")
        self.btn_send_cleanup.setEnabled(False)
        self.btn_send_cleanup.clicked.connect(self.send_selected_to_cleanup)
        
        # Button styling
        primary_style = """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #89b4fa, stop:1 #7aa2f7);
                color: #1e1e2e;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #9cc4ff, stop:1 #89b4fa);
            }
            QPushButton:pressed {
                background: #7aa2f7;
            }
            QPushButton:disabled {
                background: #45475a;
                color: #6c7086;
            }
        """
        
        secondary_style = """
            QPushButton {
                background: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 8px;
                padding: 10px 16px;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #3a3a4e;
                border-color: #6c7086;
            }
            QPushButton:pressed {
                background: #45475a;
            }
        """
        
        danger_style = """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f38ba8, stop:1 #e06c8a);
                color: #1e1e2e;
                border: none;
                border-radius: 8px;
                padding: 10px 16px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f5a0b8, stop:1 #f38ba8);
            }
            QPushButton:disabled {
                background: #45475a;
                color: #6c7086;
            }
        """
        
        self.btn_analyze.setStyleSheet(primary_style)
        self.btn_cancel.setStyleSheet(secondary_style)
        self.btn_send_cleanup.setStyleSheet(danger_style)
        self.btn_select_all.setStyleSheet(secondary_style)
        self.btn_deselect_all.setStyleSheet(secondary_style)
        
        buttons_layout.addWidget(self.btn_cancel)
        buttons_layout.addWidget(self.btn_analyze)
        buttons_layout.addWidget(self.btn_send_cleanup)
        
        layout.addLayout(buttons_layout)
        
    def start_analysis(self):
        """Start the analysis with selected rules"""
        rules = {
            'duplicates': self.check_duplicates.isChecked(),
            'large_files': self.check_large.isChecked(),
            'old_files': self.check_old.isChecked(),
            'temp_files': self.check_temp.isChecked()
        }
        
        if not any(rules.values()):
            QMessageBox.warning(self, "No Rules Selected", 
                "Please select at least one analysis rule.")
            return
        
        # Reset UI
        self.table.setRowCount(0)
        self.results = []
        self.progress_bar.setValue(0)
        self.btn_analyze.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.btn_send_cleanup.setEnabled(False)
        
        # Update stats
        self.stat_total.set_value("...")
        self.stat_size.set_value("...")
        self.stat_duplicates.set_value("...")
        self.stat_risk.set_value("...")
        
        # Start worker
        self.worker = AnalysisWorker(self.db, rules)
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.analysis_finished)
        self.worker.start()
        
    def cancel_analysis(self):
        """Cancel the running analysis"""
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.progress_label.setText("Cancelling...")
            
    def update_progress(self, value: int, message: str):
        """Update progress bar and label"""
        self.progress_bar.setValue(value)
        self.progress_label.setText(message)
        
    def analysis_finished(self, results: list):
        """Handle analysis completion"""
        self.results = results
        self.btn_analyze.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.btn_send_cleanup.setEnabled(len(results) > 0)
        
        # Populate table
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(results))
        
        total_size = 0
        duplicates_count = 0
        high_risk_count = 0
        
        for row, item in enumerate(results):
            # Checkbox
            checkbox = QTableWidgetItem()
            checkbox.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            checkbox.setCheckState(Qt.Unchecked)
            self.table.setItem(row, 0, checkbox)
            
            # Path
            path_item = QTableWidgetItem(item['path'])
            path_item.setToolTip(item['path'])
            self.table.setItem(row, 1, path_item)
            
            # Size
            size = item['size']
            total_size += size
            size_text = self.format_size(size)
            size_item = QTableWidgetItem(size_text)
            size_item.setData(Qt.UserRole, size)  # For sorting
            self.table.setItem(row, 2, size_item)
            
            # Reason
            reason_item = QTableWidgetItem(item['reason'])
            self.table.setItem(row, 3, reason_item)
            if 'Duplicate' in item['reason']:
                duplicates_count += 1
            
            # Risk level with color
            risk = item.get('risk', 'low')
            risk_item = QTableWidgetItem()
            if risk == 'high':
                risk_item.setText("⚠️ High")
                risk_item.setForeground(QColor("#f38ba8"))
                high_risk_count += 1
            elif risk == 'medium':
                risk_item.setText("⚡ Medium")
                risk_item.setForeground(QColor("#f9e2af"))
            else:
                risk_item.setText("✓ Low")
                risk_item.setForeground(QColor("#a6e3a1"))
            self.table.setItem(row, 4, risk_item)
        
        self.table.setSortingEnabled(True)
        
        # Update stats
        self.stat_total.set_value(str(len(results)))
        self.stat_size.set_value(self.format_size(total_size))
        self.stat_duplicates.set_value(str(duplicates_count))
        self.stat_risk.set_value(str(high_risk_count))
        
        self.progress_label.setText(f"Found {len(results)} files ({self.format_size(total_size)})")
        
    def format_size(self, size: int) -> str:
        """Format bytes to human readable string"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"
        
    def select_all(self):
        """Select all items in the table"""
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item:
                item.setCheckState(Qt.Checked)
                
    def deselect_all(self):
        """Deselect all items in the table"""
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item:
                item.setCheckState(Qt.Unchecked)
                
    def show_context_menu(self, position):
        """Show context menu for table"""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #1e1e2e;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item {
                padding: 8px 24px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #45475a;
            }
        """)
        
        select_action = QAction("☑️ Select", self)
        select_action.triggered.connect(lambda: self.set_selected_rows(Qt.Checked))
        
        deselect_action = QAction("☐ Deselect", self)
        deselect_action.triggered.connect(lambda: self.set_selected_rows(Qt.Unchecked))
        
        open_folder_action = QAction("📂 Open Folder", self)
        open_folder_action.triggered.connect(self.open_selected_folder)
        
        menu.addAction(select_action)
        menu.addAction(deselect_action)
        menu.addSeparator()
        menu.addAction(open_folder_action)
        
        menu.exec_(self.table.viewport().mapToGlobal(position))
        
    def set_selected_rows(self, state):
        """Set check state for selected rows"""
        for index in self.table.selectedIndexes():
            if index.column() == 0:
                continue
            row = index.row()
            item = self.table.item(row, 0)
            if item:
                item.setCheckState(state)
                
    def open_selected_folder(self):
        """Open folder containing selected file"""
        current_row = self.table.currentRow()
        if current_row >= 0:
            path_item = self.table.item(current_row, 1)
            if path_item:
                folder = os.path.dirname(path_item.text())
                os.startfile(folder)
                
    def send_selected_to_cleanup(self):
        """Send selected files to cleanup tab"""
        selected_paths = []
        for row in range(self.table.rowCount()):
            checkbox = self.table.item(row, 0)
            if checkbox and checkbox.checkState() == Qt.Checked:
                path_item = self.table.item(row, 1)
                if path_item:
                    selected_paths.append(path_item.text())
        
        if not selected_paths:
            QMessageBox.information(self, "No Selection", 
                "Please select files to send to cleanup.")
            return
            
        # Emit signal to main window
        self.send_to_cleanup.emit(selected_paths)
        QMessageBox.information(self, "Files Sent", 
            f"Sent {len(selected_paths)} files to the Cleanup tab.\n"
            "Switch to the '⚙️ Advanced' tab to process them.")
