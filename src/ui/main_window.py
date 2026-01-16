"""
Main application window with navigation tabs.
Coordinates between inventory scanning, analysis, and cleanup operations.
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QLabel, QPushButton, QProgressBar,
    QStatusBar, QMessageBox, QDockWidget, QFileDialog
)
from PySide6.QtCore import Qt, QThread, Signal, QSize
from PySide6.QtGui import QIcon, QFont, QColor
from pathlib import Path

from db.database import Database
from utils.config import Config
from utils.logger import setup_logger
from core.categorizer import FileCategorizer

from ui.tabs.inventory_tab import InventoryTab
from ui.tabs.analysis_tab import AnalysisTab
from ui.tabs.cleanup_tab import CleanupTab
from ui.tabs.category_tab import CategoryVisualizationTab
from ui.tabs.apps_cleanup_tab import AppsCleanupTab
from ui.tabs.disk_stats_tab import DiskStatsTab
from ui.dialogs import SettingsDialog


class MainWindow(QMainWindow):
    """
    Main application window.
    Provides tab navigation for inventory, analysis, category visualization, and cleanup.
    """
    
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("Local Cleaner - Disk Inventory & Smart Cleanup")
        self.setGeometry(100, 100, 1400, 900)
        
        # Initialize core components
        self.db = Database()
        self.config = Config()
        self.categorizer = FileCategorizer()
        self.logger = setup_logger("MainWindow", "logs/main.log")
        
        self.logger.info("Initializing MainWindow")
        
        # Build UI
        self._create_ui()
        self._create_menu()
        
        self.setStyleSheet(self._get_stylesheet())
    
    def _create_ui(self):
        """Build main user interface."""
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout()
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)
        central_widget.setLayout(layout)
        
        # Header with logo and stats
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 10)
        
        # Title section
        title_section = QVBoxLayout()
        title_label = QLabel("🧹 Local Cleaner")
        title_label.setProperty("cssClass", "title")
        title_font = QFont("Segoe UI", 22)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #89b4fa; font-size: 22pt; font-weight: bold;")
        
        subtitle_label = QLabel("Disk Inventory & Smart Cleanup Tool")
        subtitle_label.setStyleSheet("color: #6c7086; font-size: 10pt;")
        
        title_section.addWidget(title_label)
        title_section.addWidget(subtitle_label)
        header_layout.addLayout(title_section)
        
        header_layout.addStretch()
        
        # Quick stats display
        self.quick_stats = QLabel("Ready to scan")
        self.quick_stats.setStyleSheet("""
            background-color: #313244;
            color: #a6e3a1;
            padding: 12px 20px;
            border-radius: 8px;
            font-weight: 600;
        """)
        header_layout.addWidget(self.quick_stats)
        
        layout.addWidget(header_widget)
        
        # Tabs: Inventory, Analysis, Categories, Cleanup
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        
        self.inventory_tab = InventoryTab(self.db, self.config)
        self.analysis_tab = AnalysisTab(self.db)
        self.category_tab = CategoryVisualizationTab(self.db, self.config, self.categorizer)
        self.cleanup_tab = CleanupTab(self.db, self.config)
        self.apps_cleanup_tab = AppsCleanupTab()
        self.disk_stats_tab = DiskStatsTab()
        
        self.tabs.addTab(self.inventory_tab, "📁 Inventario")
        self.tabs.addTab(self.apps_cleanup_tab, "🧹 Limpieza")
        self.tabs.addTab(self.disk_stats_tab, "💿 Discos")
        self.tabs.addTab(self.analysis_tab, "🔍 Análisis")
        self.tabs.addTab(self.category_tab, "📊 Categorías")
        self.tabs.addTab(self.cleanup_tab, "⚙️ Avanzado")
        
        layout.addWidget(self.tabs)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
        
        # Connections
        self.inventory_tab.scan_finished.connect(self._on_scan_finished)
        self.analysis_tab.send_to_cleanup.connect(self._on_send_to_cleanup)
    
    def _create_menu(self):
        """Creates application menu"""
        
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("Archivo")
        
        exit_action = file_menu.addAction("Salir")
        exit_action.triggered.connect(self.close)
        
        # Tools menu
        tools_menu = menubar.addMenu("Herramientas")
        
        settings_action = tools_menu.addAction("Configuración")
        settings_action.triggered.connect(self._open_settings)
        
        tools_menu.addSeparator()
        
        clear_db_action = tools_menu.addAction("Limpiar Base de Datos")
        clear_db_action.triggered.connect(self._clear_database)
        
        # Help menu
        help_menu = menubar.addMenu("Ayuda")
        
        about_action = help_menu.addAction("Acerca de")
        about_action.triggered.connect(self._show_about)
    
    def _open_settings(self):
        """Opens settings dialog"""
        dialog = SettingsDialog(self.config, self)
        dialog.exec()
    
    def _clear_database(self):
        """Clears the database"""
        reply = QMessageBox.warning(
            self,
            "Confirmar",
            "¿Limpiar toda la base de datos?\nEsta acción no se puede deshacer.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.db.clear_scan()
            self.status_bar.showMessage("Database cleared")
            self.logger.info("Database cleared by user")
    
    def _show_about(self):
        """Shows About dialog"""
        QMessageBox.information(
            self,
            "Acerca de Local Cleaner",
            "Local Cleaner v1.0\n\n"
            "Aplicación Desktop para análisis y limpieza de discos.\n\n"
            "✅ 100% local (offline)\n"
            "✅ Completamente segura\n"
            "✅ Modo simulación (dry-run)\n\n"
            "© 2026 Senior Software Engineer"
        )
    
    def _on_scan_finished(self, stats):
        """Callback when scan finishes"""
        self.progress_bar.setVisible(False)
        msg = (
            f"Scan completed: "
            f"{stats.get('file_count', 0)} files, "
            f"{stats.get('total_size', 0) / 1024 / 1024:.0f} MB"
        )
        self.status_bar.showMessage(msg)
        self.logger.info(msg)
    
    def _on_send_to_cleanup(self, file_paths: list):
        """Handle files sent from analysis tab to cleanup"""
        self.cleanup_tab.add_files_from_analysis(file_paths)
        # Switch to cleanup tab
        cleanup_index = self.tabs.indexOf(self.cleanup_tab)
        if cleanup_index >= 0:
            self.tabs.setCurrentIndex(cleanup_index)
        self.status_bar.showMessage(f"Added {len(file_paths)} files to cleanup queue")
    
    @staticmethod
    def _get_stylesheet() -> str:
        """Modern dark-light hybrid stylesheet with professional appearance."""
        return """
        /* Main Window */
        QMainWindow {
            background-color: #1e1e2e;
        }
        
        QWidget {
            background-color: #1e1e2e;
            color: #cdd6f4;
            font-family: 'Segoe UI', 'Arial', sans-serif;
            font-size: 10pt;
        }
        
        /* Tab Widget */
        QTabWidget::pane {
            border: 1px solid #45475a;
            border-radius: 8px;
            background-color: #181825;
            margin-top: -1px;
        }
        
        QTabBar::tab {
            padding: 12px 28px;
            margin-right: 4px;
            background-color: #313244;
            border: 1px solid #45475a;
            border-bottom: none;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
            color: #a6adc8;
            font-weight: 500;
            min-width: 120px;
        }
        
        QTabBar::tab:selected {
            background-color: #181825;
            color: #89b4fa;
            border-bottom: 3px solid #89b4fa;
            font-weight: 600;
        }
        
        QTabBar::tab:hover:!selected {
            background-color: #45475a;
            color: #cdd6f4;
        }
        
        /* Buttons - Primary */
        QPushButton {
            padding: 10px 20px;
            background-color: #89b4fa;
            color: #1e1e2e;
            border: none;
            border-radius: 6px;
            font-weight: 600;
            min-height: 20px;
        }
        
        QPushButton:hover {
            background-color: #b4befe;
        }
        
        QPushButton:pressed {
            background-color: #74c7ec;
        }
        
        QPushButton:disabled {
            background-color: #45475a;
            color: #6c7086;
        }
        
        /* Secondary/Danger Buttons */
        QPushButton[cssClass="danger"] {
            background-color: #f38ba8;
        }
        
        QPushButton[cssClass="danger"]:hover {
            background-color: #eba0ac;
        }
        
        QPushButton[cssClass="secondary"] {
            background-color: #45475a;
            color: #cdd6f4;
        }
        
        QPushButton[cssClass="secondary"]:hover {
            background-color: #585b70;
        }
        
        /* Tables */
        QTableWidget {
            background-color: #181825;
            border: 1px solid #45475a;
            border-radius: 8px;
            gridline-color: #313244;
            selection-background-color: #45475a;
            alternate-background-color: #1e1e2e;
        }
        
        QTableWidget::item {
            padding: 8px;
            border-bottom: 1px solid #313244;
        }
        
        QTableWidget::item:selected {
            background-color: #45475a;
            color: #89b4fa;
        }
        
        QHeaderView::section {
            background-color: #313244;
            color: #cdd6f4;
            padding: 10px 8px;
            border: none;
            border-bottom: 2px solid #89b4fa;
            font-weight: 600;
        }
        
        QTableCornerButton::section {
            background-color: #313244;
            border: none;
        }
        
        /* Progress Bar */
        QProgressBar {
            border: none;
            border-radius: 6px;
            background-color: #313244;
            height: 12px;
            text-align: center;
            color: #cdd6f4;
        }
        
        QProgressBar::chunk {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #89b4fa, stop:1 #b4befe);
            border-radius: 6px;
        }
        
        /* Labels */
        QLabel {
            color: #cdd6f4;
            padding: 2px;
        }
        
        QLabel[cssClass="title"] {
            font-size: 18pt;
            font-weight: 700;
            color: #89b4fa;
        }
        
        QLabel[cssClass="subtitle"] {
            font-size: 11pt;
            color: #a6adc8;
        }
        
        QLabel[cssClass="stats"] {
            font-size: 14pt;
            font-weight: 600;
            color: #a6e3a1;
        }
        
        /* Input Fields */
        QLineEdit, QSpinBox, QComboBox {
            padding: 10px 12px;
            background-color: #313244;
            border: 1px solid #45475a;
            border-radius: 6px;
            color: #cdd6f4;
            selection-background-color: #89b4fa;
        }
        
        QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
            border: 2px solid #89b4fa;
        }
        
        QComboBox::drop-down {
            border: none;
            padding-right: 10px;
        }
        
        QComboBox::down-arrow {
            width: 12px;
            height: 12px;
        }
        
        /* Checkboxes */
        QCheckBox {
            spacing: 8px;
            color: #cdd6f4;
        }
        
        QCheckBox::indicator {
            width: 20px;
            height: 20px;
            border-radius: 4px;
            border: 2px solid #45475a;
            background-color: #313244;
        }
        
        QCheckBox::indicator:checked {
            background-color: #89b4fa;
            border-color: #89b4fa;
        }
        
        QCheckBox::indicator:hover {
            border-color: #89b4fa;
        }
        
        /* Scrollbars */
        QScrollBar:vertical {
            background-color: #181825;
            width: 12px;
            border-radius: 6px;
        }
        
        QScrollBar::handle:vertical {
            background-color: #45475a;
            border-radius: 6px;
            min-height: 30px;
        }
        
        QScrollBar::handle:vertical:hover {
            background-color: #585b70;
        }
        
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px;
        }
        
        QScrollBar:horizontal {
            background-color: #181825;
            height: 12px;
            border-radius: 6px;
        }
        
        QScrollBar::handle:horizontal {
            background-color: #45475a;
            border-radius: 6px;
            min-width: 30px;
        }
        
        QScrollBar::handle:horizontal:hover {
            background-color: #585b70;
        }
        
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
            width: 0px;
        }
        
        /* Status Bar */
        QStatusBar {
            background-color: #181825;
            color: #a6adc8;
            border-top: 1px solid #313244;
            padding: 5px;
        }
        
        /* Menu Bar */
        QMenuBar {
            background-color: #181825;
            color: #cdd6f4;
            border-bottom: 1px solid #313244;
            padding: 4px;
        }
        
        QMenuBar::item {
            padding: 6px 12px;
            border-radius: 4px;
        }
        
        QMenuBar::item:selected {
            background-color: #45475a;
        }
        
        QMenu {
            background-color: #1e1e2e;
            border: 1px solid #45475a;
            border-radius: 8px;
            padding: 8px;
        }
        
        QMenu::item {
            padding: 8px 24px;
            border-radius: 4px;
        }
        
        QMenu::item:selected {
            background-color: #45475a;
        }
        
        QMenu::separator {
            height: 1px;
            background-color: #45475a;
            margin: 6px 12px;
        }
        
        /* Group Box */
        QGroupBox {
            font-weight: 600;
            border: 1px solid #45475a;
            border-radius: 8px;
            margin-top: 12px;
            padding-top: 16px;
            background-color: #181825;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 16px;
            padding: 0 8px;
            color: #89b4fa;
        }
        
        /* Message Box */
        QMessageBox {
            background-color: #1e1e2e;
        }
        
        QMessageBox QLabel {
            color: #cdd6f4;
        }
        
        /* Tool Tips */
        QToolTip {
            background-color: #313244;
            color: #cdd6f4;
            border: 1px solid #45475a;
            border-radius: 4px;
            padding: 6px;
        }
        
        /* Dialog */
        QDialog {
            background-color: #1e1e2e;
        }
        """
    
    def closeEvent(self, event):
        """Closes the application"""
        self.db.close()
        self.logger.info("Application closed")
        event.accept()
