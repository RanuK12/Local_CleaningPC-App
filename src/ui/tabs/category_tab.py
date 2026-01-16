"""
Category Visualization Tab - Professional disk usage analysis by category
Features visual progress bars, color coding, and interactive elements
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QLabel, QPushButton, QProgressBar, QComboBox, QSpinBox, QGroupBox,
    QFrame, QGridLayout, QSizePolicy, QHeaderView, QMenu, QMessageBox,
    QFileDialog, QScrollArea
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QSize
from PySide6.QtGui import QColor, QBrush, QFont, QPainter, QPen, QLinearGradient
import os
import csv
import json
from datetime import datetime

from core.visualizer import VisualizationEngine
from utils.logger import setup_logger


class CategoryBar(QWidget):
    """Custom widget to display a colored progress bar for category visualization"""
    
    def __init__(self, percentage: float = 0, color: str = "#89b4fa"):
        super().__init__()
        self.percentage = min(percentage, 100)
        self.color = color
        self.setMinimumHeight(20)
        self.setMinimumWidth(100)
        
    def set_value(self, percentage: float, color: str = None):
        self.percentage = min(percentage, 100)
        if color:
            self.color = color
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Background
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#313244"))
        painter.drawRoundedRect(0, 0, self.width(), self.height(), 4, 4)
        
        # Progress bar
        if self.percentage > 0:
            gradient = QLinearGradient(0, 0, self.width() * self.percentage / 100, 0)
            gradient.setColorAt(0, QColor(self.color))
            gradient.setColorAt(1, QColor(self.color).lighter(120))
            painter.setBrush(gradient)
            painter.drawRoundedRect(
                0, 0, 
                int(self.width() * self.percentage / 100), 
                self.height(), 
                4, 4
            )
        
        # Percentage text
        painter.setPen(QColor("#cdd6f4"))
        painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
        painter.drawText(
            self.rect(), 
            Qt.AlignCenter, 
            f"{self.percentage:.1f}%"
        )


class StatWidget(QFrame):
    """Reusable stat display widget with icon and value"""
    
    def __init__(self, icon: str, label: str, value: str = "0", color: str = "#89b4fa"):
        super().__init__()
        self.color = color
        self.setup_ui(icon, label, value)
        
    def setup_ui(self, icon: str, label: str, value: str):
        self.setStyleSheet(f"""
            StatWidget {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #313244, stop:1 #1e1e2e);
                border: 1px solid {self.color}30;
                border-radius: 12px;
            }}
            StatWidget:hover {{
                border: 1px solid {self.color}60;
            }}
        """)
        self.setMinimumSize(160, 80)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)
        
        # Top row with icon and label
        top_layout = QHBoxLayout()
        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 16px; background: transparent; border: none;")
        text_label = QLabel(label)
        text_label.setStyleSheet("color: #a6adc8; font-size: 11px; background: transparent; border: none;")
        top_layout.addWidget(icon_label)
        top_layout.addWidget(text_label)
        top_layout.addStretch()
        
        # Value
        self.value_label = QLabel(value)
        self.value_label.setStyleSheet(f"""
            color: {self.color}; 
            font-size: 22px; 
            font-weight: bold; 
            background: transparent; 
            border: none;
        """)
        
        layout.addLayout(top_layout)
        layout.addWidget(self.value_label)
        
    def set_value(self, value: str):
        self.value_label.setText(value)


class VisualizationWorker(QThread):
    """Background thread for visualization data generation."""
    
    progress = Signal(int, str)  # percentage, message
    finished = Signal(list, list)  # category_stats, top_folders
    error = Signal(str)
    
    def __init__(self, config):
        super().__init__()
        self.config = config
    
    def run(self):
        try:
            from db.database import Database
            db = Database()
            visualizer = VisualizationEngine(db)
            
            self.progress.emit(25, "Gathering category statistics...")
            category_stats = visualizer.get_category_statistics()
            
            self.progress.emit(60, "Finding top folders...")
            top_folders = visualizer.get_top_folders(limit=20)
            
            self.progress.emit(100, "Complete!")
            self.finished.emit(category_stats, top_folders)
        except Exception as e:
            self.error.emit(f"Visualization error: {str(e)}")


class CategoryVisualizationTab(QWidget):
    """
    Professional category visualization tab with visual bars and statistics.
    Shows disk usage by category with interactive elements.
    """
    
    def __init__(self, database, config, categorizer):
        super().__init__()
        self.db = database
        self.config = config
        self.categorizer = categorizer
        self.visualizer = VisualizationEngine(database)
        self.logger = setup_logger("CategoryTab", "logs/ui.log")
        
        self.current_category_stats = []
        self.current_top_folders = []
        self.worker = None
        
        # Category colors for visual distinction
        self.category_colors = {
            'Documents': '#89b4fa',
            'Images': '#f9e2af',
            'Videos': '#f38ba8',
            'Audio': '#a6e3a1',
            'Archives': '#cba6f7',
            'Code': '#94e2d5',
            'Executables': '#fab387',
            'System': '#f5c2e7',
            'Other': '#6c7086'
        }
        
        self._create_ui()
    
    def _create_ui(self):
        """Build the professional UI for category visualization."""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(16, 16, 16, 16)
        
        # Header section
        header_layout = QVBoxLayout()
        header_layout.setSpacing(4)
        
        title = QLabel("📊 Disk Usage by Category")
        title.setStyleSheet("""
            font-size: 20px;
            font-weight: bold;
            color: #cdd6f4;
        """)
        
        subtitle = QLabel("Analyze how your storage is distributed across different file categories")
        subtitle.setStyleSheet("color: #6c7086; font-size: 12px;")
        
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        main_layout.addLayout(header_layout)
        
        # Stats cards row
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(12)
        
        self.stat_total_size = StatWidget("💾", "Total Size", "0 GB", "#89b4fa")
        self.stat_total_files = StatWidget("📁", "Total Files", "0", "#a6e3a1")
        self.stat_categories = StatWidget("🏷️", "Categories", "0", "#f9e2af")
        self.stat_largest = StatWidget("📦", "Largest", "0 GB", "#f38ba8")
        
        stats_layout.addWidget(self.stat_total_size)
        stats_layout.addWidget(self.stat_total_files)
        stats_layout.addWidget(self.stat_categories)
        stats_layout.addWidget(self.stat_largest)
        stats_layout.addStretch()
        
        main_layout.addLayout(stats_layout)
        
        # Controls bar
        controls_frame = QFrame()
        controls_frame.setStyleSheet("""
            QFrame {
                background: #1e1e2e;
                border-radius: 8px;
                padding: 4px;
            }
        """)
        controls_layout = QHBoxLayout(controls_frame)
        controls_layout.setContentsMargins(12, 8, 12, 8)
        
        self.btn_refresh = QPushButton("🔄 Refresh")
        self.btn_refresh.setToolTip("Reload category statistics")
        self.btn_refresh.clicked.connect(self._start_visualization)
        
        controls_layout.addWidget(self.btn_refresh)
        controls_layout.addSpacing(16)
        
        # Min size filter
        size_label = QLabel("Min folder size:")
        size_label.setStyleSheet("color: #a6adc8; font-size: 12px;")
        controls_layout.addWidget(size_label)
        
        self.min_size_spinbox = QSpinBox()
        self.min_size_spinbox.setMinimum(0)
        self.min_size_spinbox.setMaximum(10000)
        self.min_size_spinbox.setValue(100)
        self.min_size_spinbox.setSuffix(" MB")
        self.min_size_spinbox.setStyleSheet("""
            QSpinBox {
                background: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 6px;
                padding: 4px 8px;
                min-width: 80px;
            }
            QSpinBox:focus {
                border-color: #89b4fa;
            }
        """)
        controls_layout.addWidget(self.min_size_spinbox)
        
        controls_layout.addStretch()
        
        self.btn_export = QPushButton("📥 Export Report")
        self.btn_export.setToolTip("Export data as CSV or JSON")
        self.btn_export.clicked.connect(self._export_report)
        
        controls_layout.addWidget(self.btn_export)
        
        # Button styles
        btn_style = """
            QPushButton {
                background: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #45475a;
                border-color: #6c7086;
            }
            QPushButton:pressed {
                background: #585b70;
            }
        """
        self.btn_refresh.setStyleSheet(btn_style)
        self.btn_export.setStyleSheet(btn_style.replace("#313244", "#a6e3a1").replace("#cdd6f4", "#1e1e2e"))
        
        main_layout.addWidget(controls_frame)
        
        # Progress section
        self.progress_frame = QFrame()
        self.progress_frame.setVisible(False)
        progress_layout = QHBoxLayout(self.progress_frame)
        progress_layout.setContentsMargins(0, 0, 0, 0)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background: #313244;
                border-radius: 3px;
                border: none;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #89b4fa, stop:1 #b4befe);
                border-radius: 3px;
            }
        """)
        
        self.progress_label = QLabel("Loading...")
        self.progress_label.setStyleSheet("color: #6c7086; font-size: 11px;")
        
        progress_layout.addWidget(self.progress_bar, 1)
        progress_layout.addWidget(self.progress_label)
        
        main_layout.addWidget(self.progress_frame)
        
        # Category table with visual bars
        category_group = QGroupBox("🏷️ Categories")
        category_group.setStyleSheet("""
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
        
        category_layout = QVBoxLayout(category_group)
        category_layout.setContentsMargins(12, 20, 12, 12)
        
        self.category_table = QTableWidget()
        self.category_table.setColumnCount(5)
        self.category_table.setHorizontalHeaderLabels([
            "Category", "Files", "Size", "Usage", "% of Disk"
        ])
        self.category_table.setAlternatingRowColors(True)
        self.category_table.setShowGrid(False)
        self.category_table.verticalHeader().setVisible(False)
        self.category_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.category_table.setSortingEnabled(True)
        self.category_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.category_table.customContextMenuRequested.connect(self._show_category_menu)
        
        self._style_table(self.category_table)
        
        header = self.category_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        
        category_layout.addWidget(self.category_table)
        main_layout.addWidget(category_group)
        
        # Top folders table
        folders_group = QGroupBox("📁 Top Folders by Size")
        folders_group.setStyleSheet("""
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
        
        folders_layout = QVBoxLayout(folders_group)
        folders_layout.setContentsMargins(12, 20, 12, 12)
        
        self.folders_table = QTableWidget()
        self.folders_table.setColumnCount(5)
        self.folders_table.setHorizontalHeaderLabels([
            "Folder Path", "Files", "Size", "Usage", "% of Disk"
        ])
        self.folders_table.setAlternatingRowColors(True)
        self.folders_table.setShowGrid(False)
        self.folders_table.verticalHeader().setVisible(False)
        self.folders_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.folders_table.setSortingEnabled(True)
        self.folders_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.folders_table.customContextMenuRequested.connect(self._show_folder_menu)
        
        self._style_table(self.folders_table)
        
        header = self.folders_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Fixed)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.folders_table.setColumnWidth(3, 150)
        
        folders_layout.addWidget(self.folders_table)
        main_layout.addWidget(folders_group)
        
        # Status bar
        self.status_label = QLabel("✨ Click 'Refresh' to load category statistics")
        self.status_label.setStyleSheet("""
            color: #6c7086; 
            font-size: 11px;
            padding: 4px 8px;
            background: #1e1e2e;
            border-radius: 4px;
        """)
        main_layout.addWidget(self.status_label)
    
    def _style_table(self, table: QTableWidget):
        """Apply consistent styling to tables"""
        table.setStyleSheet("""
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
    
    def load_visualization(self):
        """Load and display visualization data."""
        self._start_visualization()
    
    def _start_visualization(self):
        """Start background visualization worker."""
        self.progress_frame.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_label.setText("Loading...")
        self.btn_refresh.setEnabled(False)
        
        self.worker = VisualizationWorker(self.config)
        self.worker.progress.connect(self._update_progress)
        self.worker.finished.connect(self._on_visualization_finished)
        self.worker.error.connect(self._on_visualization_error)
        self.worker.start()
    
    def _update_progress(self, value: int, message: str):
        """Update progress bar"""
        self.progress_bar.setValue(value)
        self.progress_label.setText(message)
    
    def _on_visualization_finished(self, category_stats, top_folders):
        """Handle visualization data received."""
        self.current_category_stats = category_stats
        self.current_top_folders = top_folders
        
        self._populate_category_table()
        self._populate_folders_table()
        self._update_stats()
        
        self.progress_frame.setVisible(False)
        self.btn_refresh.setEnabled(True)
        self.status_label.setText(
            f"✓ Loaded {len(category_stats)} categories and {len(top_folders)} folders"
        )
        self.logger.info(f"Visualization complete: {len(category_stats)} categories")
    
    def _on_visualization_error(self, error_msg):
        """Handle visualization error."""
        self.status_label.setText(f"⚠️ Error: {error_msg}")
        self.progress_frame.setVisible(False)
        self.btn_refresh.setEnabled(True)
        self.logger.error(error_msg)
    
    def _populate_category_table(self):
        """Populate category statistics table with visual bars."""
        self.category_table.setSortingEnabled(False)
        self.category_table.setRowCount(len(self.current_category_stats))
        
        for row, stats in enumerate(self.current_category_stats):
            # Get color for this category
            color = self.category_colors.get(stats.category_name, '#6c7086')
            
            # Category name with color indicator
            name_item = QTableWidgetItem(f"● {stats.category_name}")
            name_item.setForeground(QColor(color))
            name_item.setFont(QFont("Segoe UI", 10, QFont.Bold))
            self.category_table.setItem(row, 0, name_item)
            
            # File count
            files_item = QTableWidgetItem(f"{stats.total_files:,}")
            files_item.setTextAlignment(Qt.AlignCenter)
            files_item.setData(Qt.UserRole, stats.total_files)
            self.category_table.setItem(row, 1, files_item)
            
            # Size
            size_item = QTableWidgetItem(f"{stats.total_size_gb:.2f} GB")
            size_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            size_item.setData(Qt.UserRole, stats.total_size_gb)
            self.category_table.setItem(row, 2, size_item)
            
            # Visual progress bar
            bar_widget = CategoryBar(stats.percentage_of_disk, color)
            self.category_table.setCellWidget(row, 3, bar_widget)
            
            # Percentage text
            pct_item = QTableWidgetItem(f"{stats.percentage_of_disk:.1f}%")
            pct_item.setTextAlignment(Qt.AlignCenter)
            pct_item.setData(Qt.UserRole, stats.percentage_of_disk)
            self.category_table.setItem(row, 4, pct_item)
        
        self.category_table.setSortingEnabled(True)
    
    def _populate_folders_table(self):
        """Populate top folders table with visual bars."""
        self.folders_table.setSortingEnabled(False)
        self.folders_table.setRowCount(len(self.current_top_folders))
        
        max_percentage = max((f.percentage_of_disk for f in self.current_top_folders), default=1)
        
        for row, folder_stats in enumerate(self.current_top_folders):
            # Path with tooltip
            path_item = QTableWidgetItem(folder_stats.folder_path)
            path_item.setToolTip(folder_stats.folder_path)
            self.folders_table.setItem(row, 0, path_item)
            
            # File count
            files_item = QTableWidgetItem(f"{folder_stats.file_count:,}")
            files_item.setTextAlignment(Qt.AlignCenter)
            files_item.setData(Qt.UserRole, folder_stats.file_count)
            self.folders_table.setItem(row, 1, files_item)
            
            # Size
            size_item = QTableWidgetItem(f"{folder_stats.total_size_gb:.2f} GB")
            size_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            size_item.setData(Qt.UserRole, folder_stats.total_size_gb)
            self.folders_table.setItem(row, 2, size_item)
            
            # Visual bar (color gradient based on relative size)
            hue = int(200 - (folder_stats.percentage_of_disk / max(max_percentage, 1) * 80))
            color = QColor.fromHsv(hue, 180, 220).name()
            bar_widget = CategoryBar(folder_stats.percentage_of_disk, color)
            self.folders_table.setCellWidget(row, 3, bar_widget)
            
            # Percentage
            pct_item = QTableWidgetItem(f"{folder_stats.percentage_of_disk:.1f}%")
            pct_item.setTextAlignment(Qt.AlignCenter)
            pct_item.setData(Qt.UserRole, folder_stats.percentage_of_disk)
            self.folders_table.setItem(row, 4, pct_item)
        
        self.folders_table.setSortingEnabled(True)
    
    def _update_stats(self):
        """Update summary statistics cards."""
        summary = self.visualizer.get_disk_summary()
        
        total_gb = summary.get('total_gb', 0)
        total_files = summary.get('total_files', 0)
        largest_gb = summary.get('largest_file', {}).get('size_gb', 0)
        
        self.stat_total_size.set_value(f"{total_gb:.2f} GB")
        self.stat_total_files.set_value(f"{total_files:,}")
        self.stat_categories.set_value(str(len(self.current_category_stats)))
        self.stat_largest.set_value(f"{largest_gb:.2f} GB")
    
    def _show_category_menu(self, position):
        """Show context menu for category table"""
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
        
        view_files = menu.addAction("📂 View Files in Category")
        view_files.triggered.connect(self._view_category_files)
        
        menu.exec_(self.category_table.viewport().mapToGlobal(position))
    
    def _show_folder_menu(self, position):
        """Show context menu for folders table"""
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
        
        open_folder = menu.addAction("📂 Open in Explorer")
        open_folder.triggered.connect(self._open_selected_folder)
        
        menu.addSeparator()
        
        copy_path = menu.addAction("📋 Copy Path")
        copy_path.triggered.connect(self._copy_folder_path)
        
        menu.exec_(self.folders_table.viewport().mapToGlobal(position))
    
    def _view_category_files(self):
        """View files in selected category"""
        row = self.category_table.currentRow()
        if row >= 0:
            category = self.current_category_stats[row].category_name
            self.status_label.setText(f"📂 Viewing files in category: {category}")
    
    def _open_selected_folder(self):
        """Open selected folder in Windows Explorer"""
        row = self.folders_table.currentRow()
        if row >= 0:
            path = self.current_top_folders[row].folder_path
            if os.path.exists(path):
                os.startfile(path)
            else:
                QMessageBox.warning(self, "Folder Not Found", f"Path not found: {path}")
    
    def _copy_folder_path(self):
        """Copy folder path to clipboard"""
        row = self.folders_table.currentRow()
        if row >= 0:
            from PySide6.QtWidgets import QApplication
            path = self.current_top_folders[row].folder_path
            QApplication.clipboard().setText(path)
            self.status_label.setText(f"📋 Copied: {path}")
    
    def _export_report(self):
        """Export visualization as CSV or JSON report."""
        if not self.current_category_stats:
            QMessageBox.information(self, "No Data", 
                "Please refresh the data before exporting.")
            return
        
        # Ask for export format
        file_path, _ = QFileDialog.getSaveFileName(
            self, 
            "Export Report",
            f"category_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "CSV Files (*.csv);;JSON Files (*.json)"
        )
        
        if not file_path:
            return
        
        try:
            if file_path.endswith('.json'):
                self._export_json(file_path)
            else:
                self._export_csv(file_path)
            
            self.status_label.setText(f"✓ Report exported to: {file_path}")
            QMessageBox.information(self, "Export Complete", 
                f"Report saved to:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export: {str(e)}")
    
    def _export_csv(self, file_path: str):
        """Export data as CSV"""
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Categories section
            writer.writerow(["Categories"])
            writer.writerow(["Category", "Files", "Size (GB)", "% of Disk"])
            for stats in self.current_category_stats:
                writer.writerow([
                    stats.category_name,
                    stats.total_files,
                    f"{stats.total_size_gb:.2f}",
                    f"{stats.percentage_of_disk:.1f}"
                ])
            
            writer.writerow([])
            
            # Folders section
            writer.writerow(["Top Folders"])
            writer.writerow(["Path", "Files", "Size (GB)", "% of Disk"])
            for folder in self.current_top_folders:
                writer.writerow([
                    folder.folder_path,
                    folder.file_count,
                    f"{folder.total_size_gb:.2f}",
                    f"{folder.percentage_of_disk:.1f}"
                ])
    
    def _export_json(self, file_path: str):
        """Export data as JSON"""
        data = {
            "exported_at": datetime.now().isoformat(),
            "categories": [
                {
                    "name": s.category_name,
                    "files": s.total_files,
                    "size_gb": round(s.total_size_gb, 2),
                    "percentage": round(s.percentage_of_disk, 1)
                }
                for s in self.current_category_stats
            ],
            "top_folders": [
                {
                    "path": f.folder_path,
                    "files": f.file_count,
                    "size_gb": round(f.total_size_gb, 2),
                    "percentage": round(f.percentage_of_disk, 1)
                }
                for f in self.current_top_folders
            ]
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
