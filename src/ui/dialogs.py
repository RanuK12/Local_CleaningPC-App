"""Application dialogs"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QCheckBox, QSpinBox, QListWidget, QListWidgetItem,
    QMessageBox, QTabWidget, QWidget
)
from PySide6.QtCore import Qt

from utils.config import Config


class SettingsDialog(QDialog):
    """Settings dialog"""
    
    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle("Configuración")
        self.setGeometry(200, 200, 600, 400)
        self.config = config
        
        self._create_ui()
    
    def _create_ui(self):
        """Creates dialog UI"""
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Tabs
        tabs = QTabWidget()
        layout.addWidget(tabs)
        
        # Tab General
        general_tab = self._create_general_tab()
        tabs.addTab(general_tab, "General")
        
        # Tab Exclusiones
        exclusions_tab = self._create_exclusions_tab()
        tabs.addTab(exclusions_tab, "Exclusiones")
        
        # Botones
        button_layout = QHBoxLayout()
        
        save_btn = QPushButton("Guardar")
        save_btn.clicked.connect(self._save_settings)
        button_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("Cancelar")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
    
    def _create_general_tab(self) -> QWidget:
        """Creates general settings tab"""
        
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Hash workers
        hash_layout = QHBoxLayout()
        hash_layout.addWidget(QLabel("Threads de hash:"))
        self.hash_workers = QSpinBox()
        self.hash_workers.setValue(self.config.get('max_hash_workers', 4))
        self.hash_workers.setMinimum(1)
        self.hash_workers.setMaximum(16)
        hash_layout.addWidget(self.hash_workers)
        layout.addLayout(hash_layout)
        
        # Old files days
        old_files_layout = QHBoxLayout()
        old_files_layout.addWidget(QLabel("Días para archivos antiguos:"))
        self.old_files_days = QSpinBox()
        self.old_files_days.setValue(self.config.get('old_files_days', 180))
        self.old_files_days.setMinimum(1)
        self.old_files_days.setMaximum(3650)
        old_files_layout.addWidget(self.old_files_days)
        layout.addLayout(old_files_layout)
        
        # Checkboxes
        self.hidden_files_check = QCheckBox("Incluir archivos ocultos")
        self.hidden_files_check.setChecked(self.config.get('scan_hidden_files', False))
        layout.addWidget(self.hidden_files_check)
        
        self.system_files_check = QCheckBox("Incluir archivos del sistema")
        self.system_files_check.setChecked(self.config.get('include_system_files', False))
        layout.addWidget(self.system_files_check)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def _create_exclusions_tab(self) -> QWidget:
        """Creates exclusions tab"""
        
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Rutas excluidas
        layout.addWidget(QLabel("Rutas excluidas:"))
        self.excluded_paths_list = QListWidget()
        for path in self.config.get('excluded_paths', []):
            self.excluded_paths_list.addItem(path)
        layout.addWidget(self.excluded_paths_list)
        
        # Extensiones excluidas
        layout.addWidget(QLabel("Extensiones excluidas:"))
        self.excluded_ext_list = QListWidget()
        for ext in self.config.get('excluded_extensions', []):
            self.excluded_ext_list.addItem(ext)
        layout.addWidget(self.excluded_ext_list)
        
        widget.setLayout(layout)
        return widget
    
    def _save_settings(self):
        """Saves configuration"""
        self.config.set('max_hash_workers', self.hash_workers.value())
        self.config.set('old_files_days', self.old_files_days.value())
        self.config.set('scan_hidden_files', self.hidden_files_check.isChecked())
        self.config.set('include_system_files', self.system_files_check.isChecked())
        
        QMessageBox.information(self, "Éxito", "Configuración guardada")
        self.accept()


class ConfirmationDialog(QDialog):
    """Confirmation dialog for destructive actions"""
    
    def __init__(self, title: str, message: str, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle(title)
        self.setGeometry(300, 300, 400, 200)
        
        layout = QVBoxLayout()
        
        # Message
        layout.addWidget(QLabel(message))
        layout.addSpacing(20)
        
        # Confirmation checkbox
        self.confirm_check = QCheckBox("Entiendo los riesgos y confirmo")
        layout.addWidget(self.confirm_check)
        
        layout.addStretch()
        
        # Buttons
        button_layout = QHBoxLayout()
        
        ok_btn = QPushButton("Continuar")
        ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(ok_btn)
        
        cancel_btn = QPushButton("Cancelar")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def is_confirmed(self) -> bool:
        """Checks if confirmed"""
        return self.confirm_check.isChecked()
