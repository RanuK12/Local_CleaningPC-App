"""
Advanced Cleanup Tab - Professional cleanup operations with clear UX
Execute cleanup operations with visual feedback and safety confirmations
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QRadioButton, QButtonGroup,
    QMessageBox, QFrame, QGroupBox, QProgressBar, QHeaderView,
    QCheckBox, QMenu, QSizePolicy
)
from PySide6.QtCore import Qt, QThread, Signal, QSize
from PySide6.QtGui import QColor, QFont, QIcon
import os

from core.cleaner import CleanupEngine
from db.database import Database
from db.models import CleanupCandidate
from utils.config import Config
from utils.logger import setup_logger
from ui.dialogs import ConfirmationDialog


class ActionCard(QFrame):
    """Clickable action card for cleanup method selection"""
    
    clicked = Signal()
    
    def __init__(self, icon: str, title: str, description: str, 
                 color: str = "#89b4fa", risk_level: str = "safe"):
        super().__init__()
        self.color = color
        self.risk_level = risk_level
        self._selected = False
        self.setup_ui(icon, title, description)
        
    def setup_ui(self, icon: str, title: str, description: str):
        self.setMinimumSize(180, 100)
        self.setCursor(Qt.PointingHandCursor)
        self._update_style()
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(6)
        
        # Icon and title row
        header = QHBoxLayout()
        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 24px; background: transparent; border: none;")
        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            color: {self.color}; 
            font-size: 14px; 
            font-weight: bold; 
            background: transparent; 
            border: none;
        """)
        header.addWidget(icon_label)
        header.addWidget(title_label)
        header.addStretch()
        
        # Description
        desc_label = QLabel(description)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("""
            color: #6c7086; 
            font-size: 11px; 
            background: transparent; 
            border: none;
        """)
        
        # Risk indicator
        risk_colors = {
            "safe": ("#a6e3a1", "Safe"),
            "moderate": ("#f9e2af", "Moderate"),
            "danger": ("#f38ba8", "Danger")
        }
        risk_color, risk_text = risk_colors.get(self.risk_level, ("#6c7086", "Unknown"))
        risk_label = QLabel(f"● {risk_text}")
        risk_label.setStyleSheet(f"color: {risk_color}; font-size: 10px; background: transparent; border: none;")
        
        layout.addLayout(header)
        layout.addWidget(desc_label)
        layout.addStretch()
        layout.addWidget(risk_label)
        
    def _update_style(self):
        if self._selected:
            self.setStyleSheet(f"""
                ActionCard {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #313244, stop:1 #252536);
                    border: 2px solid {self.color};
                    border-radius: 12px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                ActionCard {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #1e1e2e, stop:1 #181825);
                    border: 1px solid #45475a;
                    border-radius: 12px;
                }}
                ActionCard:hover {{
                    border: 1px solid {self.color}80;
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #252536, stop:1 #1e1e2e);
                }}
            """)
    
    def set_selected(self, selected: bool):
        self._selected = selected
        self._update_style()
        
    def is_selected(self) -> bool:
        return self._selected
        
    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)


class CleanupWorker(QThread):
    """Worker thread for cleanup operations"""
    
    progress = Signal(int, str)  # percentage, message
    finished = Signal(dict)
    error = Signal(str)
    
    def __init__(self, db: Database, config: Config, actions: list, dry_run: bool):
        super().__init__()
        self.db = db
        self.config = config
        self.actions = actions
        self.dry_run = dry_run
    
    def run(self):
        """Executes cleanup"""
        try:
            cleaner = CleanupEngine(self.db, self.config)
            
            def progress_callback(p):
                pct = int((p.get('current', 0) / max(p.get('total', 1), 1)) * 100)
                self.progress.emit(pct, p.get('current_file', 'Processing...'))
            
            if self.dry_run:
                results = cleaner.simulate_cleanup(self.actions)
            else:
                results = cleaner.execute_cleanup(
                    self.actions,
                    progress_callback=progress_callback
                )
            
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))


class CleanupTab(QWidget):
    """Advanced Cleanup Tab with professional UX"""
    
    def __init__(self, db: Database, config: Config):
        super().__init__()
        
        self.db = db
        self.config = config
        self.logger = setup_logger("CleanupTab", "logs/ui.log")
        self.candidates = []
        self.worker = None
        self._selected_action = 0  # Default to dry-run
        
        self._create_ui()
    
    def _create_ui(self):
        """Build the cleanup tab UI with professional styling."""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # Header section
        header_layout = QVBoxLayout()
        header_layout.setSpacing(4)
        
        title = QLabel("⚙️ Advanced Cleanup Operations")
        title.setStyleSheet("""
            font-size: 20px;
            font-weight: bold;
            color: #cdd6f4;
        """)
        
        subtitle = QLabel("Review cleanup candidates and select your preferred action. Always preview with Dry Run first!")
        subtitle.setStyleSheet("color: #6c7086; font-size: 12px;")
        
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        layout.addLayout(header_layout)
        
        # Stats summary bar
        stats_frame = QFrame()
        stats_frame.setStyleSheet("""
            QFrame {
                background: #1e1e2e;
                border-radius: 8px;
                padding: 4px;
            }
        """)
        stats_layout = QHBoxLayout(stats_frame)
        stats_layout.setContentsMargins(16, 10, 16, 10)
        
        self.stat_files = QLabel("📁 Files: 0")
        self.stat_files.setStyleSheet("color: #89b4fa; font-weight: bold;")
        
        self.stat_size = QLabel("💾 Total Size: 0 MB")
        self.stat_size.setStyleSheet("color: #a6e3a1; font-weight: bold;")
        
        self.stat_selected = QLabel("☑️ Selected: 0")
        self.stat_selected.setStyleSheet("color: #f9e2af; font-weight: bold;")
        
        stats_layout.addWidget(self.stat_files)
        stats_layout.addWidget(QLabel("│"))
        stats_layout.addWidget(self.stat_size)
        stats_layout.addWidget(QLabel("│"))
        stats_layout.addWidget(self.stat_selected)
        stats_layout.addStretch()
        
        layout.addWidget(stats_frame)
        
        # Action selection cards
        actions_group = QGroupBox("🎯 Select Cleanup Action")
        actions_group.setStyleSheet("""
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
        
        actions_layout = QHBoxLayout(actions_group)
        actions_layout.setContentsMargins(16, 24, 16, 16)
        actions_layout.setSpacing(12)
        
        # Create action cards
        self.card_dryrun = ActionCard(
            "🔍", "Dry Run", 
            "Preview changes without modifying files",
            "#a6e3a1", "safe"
        )
        self.card_dryrun.set_selected(True)
        self.card_dryrun.clicked.connect(lambda: self._select_action(0))
        
        self.card_quarantine = ActionCard(
            "📦", "Quarantine",
            "Move files to a safe quarantine folder",
            "#89b4fa", "safe"
        )
        self.card_quarantine.clicked.connect(lambda: self._select_action(1))
        
        self.card_trash = ActionCard(
            "🗑️", "Recycle Bin",
            "Send files to the Windows Recycle Bin",
            "#f9e2af", "moderate"
        )
        self.card_trash.clicked.connect(lambda: self._select_action(2))
        
        self.card_delete = ActionCard(
            "🔥", "Permanent Delete",
            "Permanently remove files (IRREVERSIBLE!)",
            "#f38ba8", "danger"
        )
        self.card_delete.clicked.connect(lambda: self._select_action(3))
        
        self.action_cards = [
            self.card_dryrun,
            self.card_quarantine,
            self.card_trash,
            self.card_delete
        ]
        
        for card in self.action_cards:
            actions_layout.addWidget(card)
        
        actions_layout.addStretch()
        layout.addWidget(actions_group)
        
        # Progress section (hidden by default)
        self.progress_frame = QFrame()
        self.progress_frame.setVisible(False)
        self.progress_frame.setStyleSheet("""
            QFrame {
                background: #1e1e2e;
                border-radius: 8px;
                padding: 8px;
            }
        """)
        progress_layout = QVBoxLayout(self.progress_frame)
        progress_layout.setContentsMargins(16, 12, 16, 12)
        
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
        
        self.progress_label = QLabel("Processing...")
        self.progress_label.setStyleSheet("color: #6c7086; font-size: 11px;")
        
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.progress_label)
        
        layout.addWidget(self.progress_frame)
        
        # Candidates table
        table_group = QGroupBox("📋 Cleanup Candidates")
        table_group.setStyleSheet("""
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
        
        table_layout = QVBoxLayout(table_group)
        table_layout.setContentsMargins(12, 24, 12, 12)
        
        # Table toolbar
        toolbar = QHBoxLayout()
        
        self.btn_select_all = QPushButton("☑️ Select All")
        self.btn_select_all.clicked.connect(self._select_all)
        
        self.btn_deselect_all = QPushButton("☐ Deselect All")
        self.btn_deselect_all.clicked.connect(self._deselect_all)
        
        self.btn_invert = QPushButton("🔄 Invert Selection")
        self.btn_invert.clicked.connect(self._invert_selection)
        
        toolbar_btn_style = """
            QPushButton {
                background: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 11px;
            }
            QPushButton:hover {
                background: #45475a;
            }
        """
        self.btn_select_all.setStyleSheet(toolbar_btn_style)
        self.btn_deselect_all.setStyleSheet(toolbar_btn_style)
        self.btn_invert.setStyleSheet(toolbar_btn_style)
        
        toolbar.addWidget(self.btn_select_all)
        toolbar.addWidget(self.btn_deselect_all)
        toolbar.addWidget(self.btn_invert)
        toolbar.addStretch()
        
        table_layout.addLayout(toolbar)
        
        # Main table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "", "File Name", "Category", "Size", "Reason", "Risk"
        ])
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSortingEnabled(True)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.table.itemChanged.connect(self._update_selection_stats)
        
        # Table styling
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #1e1e2e;
                alternate-background-color: #232334;
                color: #cdd6f4;
                border: none;
                border-radius: 8px;
                gridline-color: transparent;
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
                background: #313244;
                color: #89b4fa;
                font-weight: bold;
                padding: 10px 8px;
                border: none;
                border-bottom: 2px solid #89b4fa;
            }
        """)
        
        # Configure columns
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table.setColumnWidth(0, 40)
        
        table_layout.addWidget(self.table)
        layout.addWidget(table_group, 1)
        
        # Bottom action bar
        action_bar = QFrame()
        action_bar.setStyleSheet("""
            QFrame {
                background: #1e1e2e;
                border-radius: 8px;
            }
        """)
        action_bar_layout = QHBoxLayout(action_bar)
        action_bar_layout.setContentsMargins(16, 12, 16, 12)
        
        self.status_label = QLabel("💡 Select files from the Analysis tab, then execute cleanup here")
        self.status_label.setStyleSheet("color: #6c7086; font-size: 12px;")
        
        self.btn_cancel = QPushButton("⏹️ Cancel")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self._cancel_cleanup)
        
        self.btn_execute = QPushButton("▶️ Execute Cleanup")
        self.btn_execute.setMinimumWidth(160)
        self.btn_execute.clicked.connect(self._execute_cleanup)
        
        # Button styles
        cancel_style = """
            QPushButton {
                background: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 13px;
            }
            QPushButton:hover {
                background: #45475a;
            }
            QPushButton:disabled {
                background: #1e1e2e;
                color: #45475a;
            }
        """
        
        execute_style = """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #89b4fa, stop:1 #7aa2f7);
                color: #1e1e2e;
                border: none;
                border-radius: 8px;
                padding: 10px 24px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #9cc4ff, stop:1 #89b4fa);
            }
            QPushButton:disabled {
                background: #45475a;
                color: #6c7086;
            }
        """
        
        self.btn_cancel.setStyleSheet(cancel_style)
        self.btn_execute.setStyleSheet(execute_style)
        
        action_bar_layout.addWidget(self.status_label)
        action_bar_layout.addStretch()
        action_bar_layout.addWidget(self.btn_cancel)
        action_bar_layout.addWidget(self.btn_execute)
        
        layout.addWidget(action_bar)
    
    def _select_action(self, action_id: int):
        """Select an action card"""
        self._selected_action = action_id
        for i, card in enumerate(self.action_cards):
            card.set_selected(i == action_id)
        
        # Update execute button style based on risk
        if action_id == 3:  # Permanent delete
            self.btn_execute.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #f38ba8, stop:1 #e06c8a);
                    color: #1e1e2e;
                    border: none;
                    border-radius: 8px;
                    padding: 10px 24px;
                    font-weight: bold;
                    font-size: 13px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #f5a0b8, stop:1 #f38ba8);
                }
                QPushButton:disabled {
                    background: #45475a;
                    color: #6c7086;
                }
            """)
            self.btn_execute.setText("⚠️ Execute PERMANENT Delete")
        else:
            self.btn_execute.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #89b4fa, stop:1 #7aa2f7);
                    color: #1e1e2e;
                    border: none;
                    border-radius: 8px;
                    padding: 10px 24px;
                    font-weight: bold;
                    font-size: 13px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #9cc4ff, stop:1 #89b4fa);
                }
                QPushButton:disabled {
                    background: #45475a;
                    color: #6c7086;
                }
            """)
            self.btn_execute.setText("▶️ Execute Cleanup")
    
    def set_candidates(self, candidates: list):
        """Set candidates from analysis tab"""
        self.candidates = candidates
        self._load_candidates()
        self._update_stats()
    
    def add_files_from_analysis(self, file_paths: list):
        """Add files sent from analysis tab"""
        # Create simple candidates from paths
        for path in file_paths:
            try:
                if os.path.exists(path):
                    # Check if already in candidates
                    if not any(c.file_info.path == path for c in self.candidates if hasattr(c, 'file_info')):
                        from db.models import FileInfo
                        file_info = FileInfo(
                            path=path,
                            name=os.path.basename(path),
                            size=os.path.getsize(path),
                            modified=os.path.getmtime(path),
                            category='Unknown'
                        )
                        candidate = CleanupCandidate(
                            file_info=file_info,
                            reason="Sent from Analysis",
                            risk_level='low',
                            category='Analysis'
                        )
                        self.candidates.append(candidate)
            except Exception as e:
                self.logger.error(f"Error adding file {path}: {e}")
        
        self._load_candidates()
        self._update_stats()
        self.status_label.setText(f"✓ Added {len(file_paths)} files from Analysis tab")
    
    def _load_candidates(self):
        """Load candidates into table"""
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        
        for idx, candidate in enumerate(self.candidates[:500]):
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            # Checkbox
            check = QTableWidgetItem()
            check.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            check.setCheckState(Qt.Unchecked)
            self.table.setItem(row, 0, check)
            
            # File name
            name = candidate.file_info.name if hasattr(candidate, 'file_info') else str(candidate)
            name_item = QTableWidgetItem(name[:50])
            name_item.setToolTip(candidate.file_info.path if hasattr(candidate, 'file_info') else str(candidate))
            self.table.setItem(row, 1, name_item)
            
            # Category
            cat_item = QTableWidgetItem(candidate.category if hasattr(candidate, 'category') else 'Unknown')
            cat_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 2, cat_item)
            
            # Size
            size = candidate.file_info.size if hasattr(candidate, 'file_info') else 0
            size_text = self._format_size(size)
            size_item = QTableWidgetItem(size_text)
            size_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            size_item.setData(Qt.UserRole, size)
            self.table.setItem(row, 3, size_item)
            
            # Reason
            reason = candidate.reason if hasattr(candidate, 'reason') else ''
            reason_item = QTableWidgetItem(reason[:40])
            reason_item.setToolTip(reason)
            self.table.setItem(row, 4, reason_item)
            
            # Risk level
            risk = candidate.risk_level if hasattr(candidate, 'risk_level') else 'low'
            risk_item = QTableWidgetItem()
            if risk == 'high':
                risk_item.setText("⚠️ High")
                risk_item.setForeground(QColor("#f38ba8"))
            elif risk == 'medium':
                risk_item.setText("⚡ Medium")
                risk_item.setForeground(QColor("#f9e2af"))
            else:
                risk_item.setText("✓ Low")
                risk_item.setForeground(QColor("#a6e3a1"))
            risk_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 5, risk_item)
        
        self.table.setSortingEnabled(True)
    
    def _update_stats(self):
        """Update statistics display"""
        total_size = sum(
            c.file_info.size if hasattr(c, 'file_info') else 0 
            for c in self.candidates
        )
        self.stat_files.setText(f"📁 Files: {len(self.candidates)}")
        self.stat_size.setText(f"💾 Total Size: {self._format_size(total_size)}")
        self._update_selection_stats()
    
    def _update_selection_stats(self):
        """Update selected count"""
        selected = sum(
            1 for row in range(self.table.rowCount())
            if self.table.item(row, 0) and self.table.item(row, 0).checkState() == Qt.Checked
        )
        self.stat_selected.setText(f"☑️ Selected: {selected}")
    
    def _format_size(self, size: int) -> str:
        """Format bytes to human readable"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"
    
    def _select_all(self):
        """Select all items"""
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item:
                item.setCheckState(Qt.Checked)
    
    def _deselect_all(self):
        """Deselect all items"""
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item:
                item.setCheckState(Qt.Unchecked)
    
    def _invert_selection(self):
        """Invert selection"""
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item:
                current = item.checkState()
                item.setCheckState(Qt.Unchecked if current == Qt.Checked else Qt.Checked)
    
    def _show_context_menu(self, position):
        """Show context menu"""
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
        
        select_action = menu.addAction("☑️ Select")
        select_action.triggered.connect(lambda: self._set_selected_rows(Qt.Checked))
        
        deselect_action = menu.addAction("☐ Deselect")
        deselect_action.triggered.connect(lambda: self._set_selected_rows(Qt.Unchecked))
        
        menu.addSeparator()
        
        open_folder = menu.addAction("📂 Open Folder")
        open_folder.triggered.connect(self._open_selected_folder)
        
        remove_action = menu.addAction("🗑️ Remove from List")
        remove_action.triggered.connect(self._remove_selected)
        
        menu.exec_(self.table.viewport().mapToGlobal(position))
    
    def _set_selected_rows(self, state):
        """Set check state for selected rows"""
        for index in self.table.selectedIndexes():
            row = index.row()
            item = self.table.item(row, 0)
            if item:
                item.setCheckState(state)
    
    def _open_selected_folder(self):
        """Open folder of selected file"""
        row = self.table.currentRow()
        if row >= 0 and row < len(self.candidates):
            path = self.candidates[row].file_info.path if hasattr(self.candidates[row], 'file_info') else ''
            if path and os.path.exists(os.path.dirname(path)):
                os.startfile(os.path.dirname(path))
    
    def _remove_selected(self):
        """Remove selected items from list"""
        rows_to_remove = []
        for row in range(self.table.rowCount()):
            if row in [index.row() for index in self.table.selectedIndexes()]:
                rows_to_remove.append(row)
        
        for row in sorted(rows_to_remove, reverse=True):
            if row < len(self.candidates):
                del self.candidates[row]
        
        self._load_candidates()
        self._update_stats()
    
    def _get_selected_candidates(self) -> list:
        """Get checked candidates"""
        selected = []
        for row in range(self.table.rowCount()):
            check_item = self.table.item(row, 0)
            if check_item and check_item.checkState() == Qt.Checked:
                if row < len(self.candidates):
                    selected.append(self.candidates[row])
        return selected
    
    def _execute_cleanup(self):
        """Execute cleanup operation"""
        selected = self._get_selected_candidates()
        
        if not selected:
            QMessageBox.warning(self, "No Selection", 
                "Please select at least one file to clean up.")
            return
        
        # Determine action type
        action_id = self._selected_action
        
        if action_id == 0:  # Dry-run
            action_type = 'quarantine'
            dry_run = True
            title = "Preview Cleanup"
            msg = f"This will PREVIEW the cleanup of {len(selected)} file(s).\nNo files will be modified.\n\nContinue?"
        
        elif action_id == 1:  # Quarantine
            action_type = 'quarantine'
            dry_run = False
            title = "Move to Quarantine"
            msg = f"This will move {len(selected)} file(s) to the quarantine folder.\nFiles can be restored later.\n\nContinue?"
        
        elif action_id == 2:  # Recycle Bin
            action_type = 'delete'
            dry_run = False
            title = "Send to Recycle Bin"
            msg = f"This will send {len(selected)} file(s) to the Recycle Bin.\nFiles can be restored from there.\n\nContinue?"
        
        else:  # Permanent delete
            action_type = 'delete'
            dry_run = False
            title = "⚠️ PERMANENT DELETE"
            msg = (
                f"⚠️ WARNING: This will PERMANENTLY delete {len(selected)} file(s).\n"
                f"This action CANNOT BE UNDONE!\n\n"
                f"Are you ABSOLUTELY sure?"
            )
            
            # First confirmation
            reply = QMessageBox.critical(
                self,
                title,
                msg,
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply != QMessageBox.Yes:
                self.status_label.setText("Operation cancelled")
                return
            
            # Double confirmation for permanent delete
            dialog = ConfirmationDialog(
                "FINAL CONFIRMATION",
                "Type 'DELETE' to confirm permanent deletion:",
                self
            )
            
            if dialog.exec() != dialog.Accepted or not dialog.is_confirmed():
                self.status_label.setText("Operation cancelled")
                return
        
        # Show confirmation for non-destructive actions
        if action_id != 3:
            reply = QMessageBox.question(
                self,
                title,
                msg,
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply != QMessageBox.Yes:
                self.status_label.setText("Operation cancelled")
                return
        
        # Create cleanup plan
        cleaner = CleanupEngine(self.db, self.config)
        actions = cleaner.create_cleanup_plan(selected, action_type)
        
        self.logger.info(
            f"Executing {len(actions)} actions - Type: {action_type}, Dry-run: {dry_run}"
        )
        
        # Update UI for processing
        self.btn_execute.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.progress_frame.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Processing...")
        
        # Execute in worker thread
        self.worker = CleanupWorker(self.db, self.config, actions, dry_run)
        self.worker.progress.connect(self._update_progress)
        self.worker.finished.connect(lambda r: self._on_cleanup_finished(r, dry_run))
        self.worker.error.connect(self._on_error)
        self.worker.start()
    
    def _cancel_cleanup(self):
        """Cancel running cleanup"""
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.status_label.setText("Operation cancelled")
            self.progress_frame.setVisible(False)
            self.btn_execute.setEnabled(True)
            self.btn_cancel.setEnabled(False)
    
    def _update_progress(self, value: int, message: str):
        """Update progress display"""
        self.progress_bar.setValue(value)
        self.progress_label.setText(message)
    
    def _on_cleanup_finished(self, results: dict, dry_run: bool):
        """Handle cleanup completion"""
        self.btn_execute.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.progress_frame.setVisible(False)
        
        status = "Preview complete" if dry_run else "Cleanup complete"
        freed_mb = results.get('total_freed', 0) / 1024 / 1024
        
        msg = (
            f"✓ {status}\n\n"
            f"Successful: {results.get('successful', 0)}\n"
            f"Failed: {results.get('failed', 0)}\n"
            f"Space freed: {freed_mb:.1f} MB"
        )
        
        self.status_label.setText(
            f"✓ {status} - {results.get('successful', 0)} files, {freed_mb:.1f} MB freed"
        )
        self.logger.info(msg)
        
        QMessageBox.information(self, status, msg)
        
        # Refresh list if not dry-run
        if not dry_run:
            self._remove_completed_candidates(results)
    
    def _remove_completed_candidates(self, results: dict):
        """Remove successfully processed candidates from list"""
        # In a real implementation, you would track which files were processed
        # For now, remove all checked items
        new_candidates = []
        for row in range(self.table.rowCount()):
            check_item = self.table.item(row, 0)
            if check_item and check_item.checkState() != Qt.Checked:
                if row < len(self.candidates):
                    new_candidates.append(self.candidates[row])
        
        self.candidates = new_candidates
        self._load_candidates()
        self._update_stats()
    
    def _on_error(self, error: str):
        """Handle cleanup error"""
        self.btn_execute.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.progress_frame.setVisible(False)
        
        self.status_label.setText(f"❌ Error: {error[:50]}")
        self.logger.error(f"Cleanup error: {error}")
        
        QMessageBox.critical(self, "Error", f"Cleanup failed:\n{error}")
