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
            "Local Cleaner v1.1.0\n\n"
            "Aplicación Desktop para análisis y limpieza de discos.\n\n"
            "✅ 100% local (offline)\n"
            "✅ Completamente segura\n"
            "✅ Modo simulación (dry-run)\n\n"
            "Desarrollado por Emilio Ranucoli\n"
            "https://github.com/RanuK12"
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
        """
        Load stylesheet from external QSS file for maintainability.
        Falls back to minimal embedded styles if file not found.
        """
        qss_path = Path("resources/style.qss")
        
        try:
            if qss_path.exists():
                with open(qss_path, 'r', encoding='utf-8') as f:
                    return f.read()
        except Exception:
            pass
        
        # Minimal fallback stylesheet
        return """
        QMainWindow { background-color: #1e1e2e; }
        QWidget { background-color: #1e1e2e; color: #cdd6f4; font-family: 'Segoe UI'; }
        QPushButton { background-color: #89b4fa; color: #1e1e2e; border-radius: 6px; padding: 8px 16px; }
        QPushButton:hover { background-color: #b4befe; }
        QTableWidget { background-color: #181825; border: 1px solid #45475a; }
        QTabBar::tab { background-color: #313244; padding: 10px 20px; }
        QTabBar::tab:selected { background-color: #181825; color: #89b4fa; }
        """
    
    def closeEvent(self, event):
        """Closes the application"""
        self.db.close()
        self.logger.info("Application closed")
        event.accept()
