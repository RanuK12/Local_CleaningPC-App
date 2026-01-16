"""
Apps & Cleanup Tab: Shows installed apps, cleanup groups, and provides cleanup/uninstall options.
Similar to Windows Settings > Apps and Disk Cleanup functionality.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QCheckBox, QComboBox,
    QLineEdit, QProgressBar, QMessageBox, QFrame, QTabWidget,
    QHeaderView, QAbstractItemView, QSplitter, QGroupBox,
    QScrollArea, QSizePolicy
)
from PySide6.QtCore import Qt, QThread, Signal, QSize
from PySide6.QtGui import QFont
from typing import List, Dict

from core.app_analyzer import AppAnalyzer, InstalledApp, CleanupGroup
from utils.logger import setup_logger


class AppScanWorker(QThread):
    """Worker thread for scanning installed apps"""
    progress = Signal(str)
    finished = Signal(list)
    error = Signal(str)
    
    def __init__(self):
        super().__init__()
        self.analyzer = AppAnalyzer()
    
    def run(self):
        try:
            self.progress.emit("Buscando aplicaciones instaladas...")
            apps = self.analyzer.get_installed_apps()
            self.finished.emit(apps)
        except Exception as e:
            self.error.emit(str(e))


class CleanupScanWorker(QThread):
    """Worker thread for scanning cleanup groups"""
    progress = Signal(str)
    finished = Signal(list)
    error = Signal(str)
    
    def __init__(self):
        super().__init__()
        self.analyzer = AppAnalyzer()
    
    def run(self):
        try:
            self.progress.emit("Analizando archivos temporales y caché...")
            groups = self.analyzer.get_cleanup_groups()
            self.finished.emit(groups)
        except Exception as e:
            self.error.emit(str(e))


class CleanupWorker(QThread):
    """Worker thread for cleaning files"""
    progress = Signal(str, int, int)  # message, current, total
    finished = Signal(dict)
    error = Signal(str)
    
    def __init__(self, groups: List[CleanupGroup], dry_run: bool = False):
        super().__init__()
        self.groups = groups
        self.dry_run = dry_run
        self.analyzer = AppAnalyzer()
    
    def run(self):
        try:
            total_deleted = 0
            total_freed = 0
            all_errors = []
            
            for i, group in enumerate(self.groups):
                self.progress.emit(f"Limpiando {group.name}...", i + 1, len(self.groups))
                deleted, freed, errors = self.analyzer.clean_group(group, self.dry_run)
                total_deleted += deleted
                total_freed += freed
                all_errors.extend(errors)
            
            self.finished.emit({
                'deleted': total_deleted,
                'freed': total_freed,
                'errors': all_errors,
                'dry_run': self.dry_run
            })
        except Exception as e:
            self.error.emit(str(e))


class AppsCleanupTab(QWidget):
    """Tab for managing apps and system cleanup"""
    
    def __init__(self):
        super().__init__()
        self.logger = setup_logger("AppsCleanupTab", "logs/ui.log")
        self.analyzer = AppAnalyzer()
        self.apps: List[InstalledApp] = []
        self.cleanup_groups: List[CleanupGroup] = []
        self.selected_groups: List[CleanupGroup] = []
        
        self._create_ui()
    
    def _create_ui(self):
        """Build the UI"""
        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)
        self.setLayout(layout)
        
        # Header
        header = QLabel("🧹 Limpieza del Sistema")
        header.setStyleSheet("font-size: 16pt; font-weight: bold; color: #89b4fa;")
        layout.addWidget(header)
        
        # Sub-tabs for Apps and Cleanup
        self.sub_tabs = QTabWidget()
        self.sub_tabs.setDocumentMode(True)
        
        # Tab 1: Cleanup Groups (like Windows Disk Cleanup)
        cleanup_widget = self._create_cleanup_tab()
        self.sub_tabs.addTab(cleanup_widget, "🗑️ Limpieza de Disco")
        
        # Tab 2: Installed Apps
        apps_widget = self._create_apps_tab()
        self.sub_tabs.addTab(apps_widget, "📦 Aplicaciones Instaladas")
        
        layout.addWidget(self.sub_tabs)
    
    def _create_cleanup_tab(self) -> QWidget:
        """Create the disk cleanup tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(12)
        
        # Scan button and status
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
        
        self.scan_cleanup_btn = QPushButton("🔍 Analizar Sistema")
        self.scan_cleanup_btn.setMinimumHeight(40)
        self.scan_cleanup_btn.setCursor(Qt.PointingHandCursor)
        self.scan_cleanup_btn.clicked.connect(self._scan_cleanup)
        control_layout.addWidget(self.scan_cleanup_btn)
        
        control_layout.addStretch()
        
        self.cleanup_status = QLabel("Haz clic en Analizar para buscar archivos limpiables")
        self.cleanup_status.setStyleSheet("color: #6c7086;")
        control_layout.addWidget(self.cleanup_status)
        
        layout.addWidget(control_frame)
        
        # Cleanup groups list
        self.cleanup_scroll = QScrollArea()
        self.cleanup_scroll.setWidgetResizable(True)
        self.cleanup_scroll.setStyleSheet("""
            QScrollArea {
                border: 1px solid #45475a;
                border-radius: 8px;
                background-color: #181825;
            }
        """)
        
        self.cleanup_container = QWidget()
        self.cleanup_layout = QVBoxLayout(self.cleanup_container)
        self.cleanup_layout.setSpacing(8)
        self.cleanup_layout.setAlignment(Qt.AlignTop)
        
        # Placeholder
        placeholder = QLabel("Los grupos de limpieza aparecerán aquí después del análisis")
        placeholder.setStyleSheet("color: #6c7086; padding: 40px;")
        placeholder.setAlignment(Qt.AlignCenter)
        self.cleanup_layout.addWidget(placeholder)
        
        self.cleanup_scroll.setWidget(self.cleanup_container)
        layout.addWidget(self.cleanup_scroll)
        
        # Bottom action bar
        action_frame = QFrame()
        action_frame.setObjectName("actionFrame")
        action_frame.setStyleSheet("""
            QFrame#actionFrame {
                background-color: #181825;
                border-radius: 10px;
                padding: 10px;
            }
        """)
        action_layout = QHBoxLayout(action_frame)
        
        self.total_selected_label = QLabel("Seleccionado: 0 MB")
        self.total_selected_label.setStyleSheet("font-weight: bold; color: #a6e3a1; font-size: 12pt;")
        action_layout.addWidget(self.total_selected_label)
        
        action_layout.addStretch()
        
        self.preview_btn = QPushButton("👁️ Vista Previa")
        self.preview_btn.setEnabled(False)
        self.preview_btn.clicked.connect(self._preview_cleanup)
        action_layout.addWidget(self.preview_btn)
        
        self.clean_btn = QPushButton("🧹 Limpiar Seleccionados")
        self.clean_btn.setEnabled(False)
        self.clean_btn.setStyleSheet("background-color: #f38ba8; color: #1e1e2e;")
        self.clean_btn.setCursor(Qt.PointingHandCursor)
        self.clean_btn.clicked.connect(self._clean_selected)
        action_layout.addWidget(self.clean_btn)
        
        layout.addWidget(action_frame)
        
        return widget
    
    def _create_apps_tab(self) -> QWidget:
        """Create the installed apps tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(12)
        
        # Search and filter bar
        filter_frame = QFrame()
        filter_frame.setObjectName("filterFrame")
        filter_frame.setStyleSheet("""
            QFrame#filterFrame {
                background-color: #181825;
                border-radius: 10px;
            }
        """)
        filter_layout = QHBoxLayout(filter_frame)
        
        self.app_search = QLineEdit()
        self.app_search.setPlaceholderText("🔍 Buscar aplicación...")
        self.app_search.setMinimumWidth(300)
        self.app_search.textChanged.connect(self._filter_apps)
        filter_layout.addWidget(self.app_search)
        
        # Sort combo
        sort_label = QLabel("Ordenar:")
        sort_label.setStyleSheet("color: #6c7086;")
        filter_layout.addWidget(sort_label)
        
        self.sort_combo = QComboBox()
        self.sort_combo.addItems([
            "📝 A-Z (Nombre)",
            "📝 Z-A (Nombre)",
            "📊 Mayor tamaño",
            "📊 Menor tamaño",
            "💿 Por disco"
        ])
        self.sort_combo.setMinimumWidth(150)
        self.sort_combo.currentIndexChanged.connect(self._sort_apps)
        self.sort_combo.setStyleSheet("""
            QComboBox {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 6px;
                padding: 6px 12px;
            }
            QComboBox:hover {
                border-color: #89b4fa;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border: none;
            }
        """)
        filter_layout.addWidget(self.sort_combo)
        
        filter_layout.addStretch()
        
        self.scan_apps_btn = QPushButton("🔄 Cargar Apps")
        self.scan_apps_btn.setCursor(Qt.PointingHandCursor)
        self.scan_apps_btn.clicked.connect(self._scan_apps)
        filter_layout.addWidget(self.scan_apps_btn)
        
        layout.addWidget(filter_frame)
        
        # Apps table
        self.apps_table = QTableWidget()
        self.apps_table.setColumnCount(6)
        self.apps_table.setHorizontalHeaderLabels([
            "📦 Aplicación", "🏢 Editor", "📌 Versión", "💿 Disco", "📊 Tamaño", "⚙️ Acciones"
        ])
        self.apps_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.apps_table.setAlternatingRowColors(True)
        self.apps_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.apps_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.apps_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.apps_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.apps_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.apps_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Fixed)
        self.apps_table.setColumnWidth(5, 120)
        self.apps_table.verticalHeader().setVisible(False)
        self.apps_table.setShowGrid(False)
        
        layout.addWidget(self.apps_table)
        
        # Status bar
        self.apps_status = QLabel("Haz clic en 'Cargar Apps' para ver las aplicaciones instaladas")
        self.apps_status.setStyleSheet("color: #6c7086;")
        layout.addWidget(self.apps_status)
        
        return widget
    
    def _scan_cleanup(self):
        """Start scanning for cleanup groups"""
        self.scan_cleanup_btn.setEnabled(False)
        self.cleanup_status.setText("⏳ Analizando sistema...")
        self.cleanup_status.setStyleSheet("color: #89b4fa;")
        
        self.cleanup_worker = CleanupScanWorker()
        self.cleanup_worker.progress.connect(lambda msg: self.cleanup_status.setText(msg))
        self.cleanup_worker.finished.connect(self._on_cleanup_scan_finished)
        self.cleanup_worker.error.connect(self._on_cleanup_error)
        self.cleanup_worker.start()
    
    def _on_cleanup_scan_finished(self, groups: List[CleanupGroup]):
        """Handle cleanup scan completion"""
        self.cleanup_groups = groups
        self.selected_groups = []  # Reset selection
        self.scan_cleanup_btn.setEnabled(True)
        
        # Clear existing items safely
        for i in reversed(range(self.cleanup_layout.count())):
            item = self.cleanup_layout.itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()
        
        if not groups:
            self.cleanup_status.setText("✨ ¡Tu sistema está limpio!")
            self.cleanup_status.setStyleSheet("color: #a6e3a1;")
            return
        
        total_size = sum(g.total_size for g in groups)
        self.cleanup_status.setText(f"✅ Encontrados {len(groups)} grupos - {self.analyzer.format_size(total_size)} recuperables")
        self.cleanup_status.setStyleSheet("color: #a6e3a1;")
        
        # Create group cards
        for group in groups:
            card = self._create_cleanup_card(group)
            self.cleanup_layout.addWidget(card)
            # Auto-select safe groups
            if group.is_safe:
                self.selected_groups.append(group)
        
        self.cleanup_layout.addStretch()
        self._update_selection_total()
    
    def _create_cleanup_card(self, group: CleanupGroup) -> QFrame:
        """Create a card for a cleanup group"""
        card = QFrame()
        card.setObjectName("cleanupCard")
        card.setStyleSheet("""
            QFrame#cleanupCard {
                background-color: #1e1e2e;
                border: 1px solid #45475a;
                border-radius: 8px;
                padding: 8px;
            }
            QFrame#cleanupCard:hover {
                border-color: #89b4fa;
            }
        """)
        
        layout = QHBoxLayout(card)
        layout.setContentsMargins(12, 8, 12, 8)
        
        # Checkbox
        checkbox = QCheckBox()
        checkbox.setChecked(group.is_safe)
        checkbox.stateChanged.connect(lambda state, g=group: self._toggle_group(g, state))
        checkbox.setStyleSheet("QCheckBox::indicator { width: 20px; height: 20px; }")
        layout.addWidget(checkbox)
        
        # Store reference
        group._checkbox = checkbox
        
        # Icon and name
        icon_label = QLabel(group.icon)
        icon_label.setStyleSheet("font-size: 20pt;")
        layout.addWidget(icon_label)
        
        # Info section
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        name_label = QLabel(group.name)
        name_label.setStyleSheet("font-weight: bold; color: #cdd6f4; font-size: 11pt;")
        info_layout.addWidget(name_label)
        
        desc_label = QLabel(f"{group.description} • {group.file_count} archivos")
        desc_label.setStyleSheet("color: #6c7086; font-size: 9pt;")
        info_layout.addWidget(desc_label)
        
        layout.addLayout(info_layout)
        layout.addStretch()
        
        # Size
        size_label = QLabel(self.analyzer.format_size(group.total_size))
        size_label.setStyleSheet("font-weight: bold; color: #fab387; font-size: 12pt;")
        layout.addWidget(size_label)
        
        return card
    
    def _toggle_group(self, group: CleanupGroup, state: int):
        """Toggle group selection"""
        # In PySide6, stateChanged emits int: 0=Unchecked, 1=PartiallyChecked, 2=Checked
        is_checked = state == 2  # Qt.CheckState.Checked.value
        
        if is_checked:
            if group not in self.selected_groups:
                self.selected_groups.append(group)
        else:
            if group in self.selected_groups:
                self.selected_groups.remove(group)
        
        self._update_selection_total()
    
    def _update_selection_total(self):
        """Update the total selected size"""
        total = sum(g.total_size for g in self.selected_groups)
        self.total_selected_label.setText(f"Seleccionado: {self.analyzer.format_size(total)}")
        
        has_selection = len(self.selected_groups) > 0
        self.preview_btn.setEnabled(has_selection)
        self.clean_btn.setEnabled(has_selection)
    
    def _preview_cleanup(self):
        """Show preview of files to be deleted"""
        if not self.selected_groups:
            return
        
        preview_text = "Archivos a eliminar:\n\n"
        for group in self.selected_groups:
            preview_text += f"📁 {group.name} ({self.analyzer.format_size(group.total_size)})\n"
            for file_info in group.files[:5]:  # Show first 5
                preview_text += f"   • {file_info['name']}\n"
            if len(group.files) > 5:
                preview_text += f"   ... y {len(group.files) - 5} archivos más\n"
            preview_text += "\n"
        
        QMessageBox.information(self, "Vista Previa", preview_text)
    
    def _clean_selected(self):
        """Clean selected groups"""
        if not self.selected_groups:
            return
        
        total_size = sum(g.total_size for g in self.selected_groups)
        total_files = sum(g.file_count for g in self.selected_groups)
        
        reply = QMessageBox.warning(
            self,
            "Confirmar Limpieza",
            f"¿Eliminar {total_files} archivos ({self.analyzer.format_size(total_size)})?\n\n"
            "Esta acción no se puede deshacer.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.clean_btn.setEnabled(False)
            self.cleanup_status.setText("🧹 Limpiando...")
            
            self.clean_worker = CleanupWorker(self.selected_groups.copy(), dry_run=False)
            self.clean_worker.progress.connect(
                lambda msg, cur, tot: self.cleanup_status.setText(f"{msg} ({cur}/{tot})")
            )
            self.clean_worker.finished.connect(self._on_cleanup_finished)
            self.clean_worker.error.connect(self._on_cleanup_error)
            self.clean_worker.start()
    
    def _on_cleanup_finished(self, result: dict):
        """Handle cleanup completion"""
        self.clean_btn.setEnabled(True)
        
        deleted = result['deleted']
        freed = result['freed']
        errors = result['errors']
        
        if errors:
            error_text = "\n".join(errors[:5])
            if len(errors) > 5:
                error_text += f"\n... y {len(errors) - 5} errores más"
            QMessageBox.warning(
                self,
                "Limpieza Completa con Errores",
                f"Eliminados: {deleted} archivos ({self.analyzer.format_size(freed)})\n\n"
                f"Errores:\n{error_text}"
            )
        else:
            QMessageBox.information(
                self,
                "Limpieza Completa",
                f"✅ Eliminados {deleted} archivos\n"
                f"💾 Espacio liberado: {self.analyzer.format_size(freed)}"
            )
        
        self.cleanup_status.setText(f"✅ Liberados {self.analyzer.format_size(freed)}")
        self.cleanup_status.setStyleSheet("color: #a6e3a1;")
        
        # Refresh
        self.selected_groups = []
        self._scan_cleanup()
    
    def _on_cleanup_error(self, error: str):
        """Handle cleanup error"""
        self.scan_cleanup_btn.setEnabled(True)
        self.clean_btn.setEnabled(True)
        self.cleanup_status.setText(f"❌ Error: {error}")
        self.cleanup_status.setStyleSheet("color: #f38ba8;")
    
    def _scan_apps(self):
        """Start scanning installed apps"""
        self.scan_apps_btn.setEnabled(False)
        self.apps_status.setText("⏳ Buscando aplicaciones...")
        self.apps_status.setStyleSheet("color: #89b4fa;")
        
        self.app_worker = AppScanWorker()
        self.app_worker.progress.connect(lambda msg: self.apps_status.setText(msg))
        self.app_worker.finished.connect(self._on_apps_scan_finished)
        self.app_worker.error.connect(self._on_apps_error)
        self.app_worker.start()
    
    def _on_apps_scan_finished(self, apps: List[InstalledApp]):
        """Handle apps scan completion"""
        self.apps = apps
        self.scan_apps_btn.setEnabled(True)
        self.apps_status.setText(f"✅ {len(apps)} aplicaciones encontradas")
        self.apps_status.setStyleSheet("color: #a6e3a1;")
        
        self._populate_apps_table(apps)
    
    def _populate_apps_table(self, apps: List[InstalledApp]):
        """Populate the apps table"""
        self.apps_table.setRowCount(0)
        
        for app in apps:
            row = self.apps_table.rowCount()
            self.apps_table.insertRow(row)
            
            # Name
            name_item = QTableWidgetItem(app.name)
            name_item.setData(Qt.UserRole, app)
            self.apps_table.setItem(row, 0, name_item)
            
            # Publisher
            self.apps_table.setItem(row, 1, QTableWidgetItem(app.publisher[:30] if app.publisher else "-"))
            
            # Version
            self.apps_table.setItem(row, 2, QTableWidgetItem(app.version or "-"))
            
            # Drive
            drive_item = QTableWidgetItem(app.install_drive or "-")
            drive_item.setTextAlignment(Qt.AlignCenter)
            self.apps_table.setItem(row, 3, drive_item)
            
            # Size
            size_text = self.analyzer.format_size(app.size_bytes) if app.size_bytes > 0 else "-"
            self.apps_table.setItem(row, 4, QTableWidgetItem(size_text))
            
            # Uninstall button
            if app.uninstall_string:
                uninstall_btn = QPushButton("🗑️ Desinstalar")
                uninstall_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #45475a;
                        color: #cdd6f4;
                        border-radius: 4px;
                        padding: 4px 8px;
                    }
                    QPushButton:hover {
                        background-color: #f38ba8;
                        color: #1e1e2e;
                    }
                """)
                uninstall_btn.setCursor(Qt.PointingHandCursor)
                uninstall_btn.clicked.connect(lambda checked, a=app: self._uninstall_app(a))
                self.apps_table.setCellWidget(row, 5, uninstall_btn)
    
    def _filter_apps(self, text: str):
        """Filter apps table by search text"""
        text = text.lower()
        for row in range(self.apps_table.rowCount()):
            item = self.apps_table.item(row, 0)
            if item:
                app_name = item.text().lower()
                publisher = self.apps_table.item(row, 1).text().lower() if self.apps_table.item(row, 1) else ""
                show = text in app_name or text in publisher
                self.apps_table.setRowHidden(row, not show)
    
    def _sort_apps(self, index: int):
        """Sort apps based on selected criteria"""
        if not self.apps:
            return
        
        sorted_apps = self.apps.copy()
        
        if index == 0:  # A-Z
            sorted_apps.sort(key=lambda x: x.name.lower())
        elif index == 1:  # Z-A
            sorted_apps.sort(key=lambda x: x.name.lower(), reverse=True)
        elif index == 2:  # Largest first
            sorted_apps.sort(key=lambda x: x.size_bytes, reverse=True)
        elif index == 3:  # Smallest first
            sorted_apps.sort(key=lambda x: x.size_bytes)
        elif index == 4:  # By drive
            sorted_apps.sort(key=lambda x: (x.install_drive or "Z:", x.name.lower()))
        
        self._populate_apps_table(sorted_apps)
    
    def _uninstall_app(self, app: InstalledApp):
        """Uninstall an application"""
        reply = QMessageBox.warning(
            self,
            "Confirmar Desinstalación",
            f"¿Desinstalar {app.name}?\n\n"
            "Se abrirá el desinstalador de la aplicación.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            success, message = self.analyzer.uninstall_app(app)
            if success:
                QMessageBox.information(self, "Desinstalación", message)
            else:
                QMessageBox.warning(self, "Error", message)
    
    def _on_apps_error(self, error: str):
        """Handle apps scan error"""
        self.scan_apps_btn.setEnabled(True)
        self.apps_status.setText(f"❌ Error: {error}")
        self.apps_status.setStyleSheet("color: #f38ba8;")
