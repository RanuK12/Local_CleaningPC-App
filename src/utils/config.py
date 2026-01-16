"""
Configuración de la aplicación
"""

import json
from pathlib import Path
from typing import Dict, List, Any


class Config:
    """Gestor de configuración"""
    
    DEFAULT_CONFIG = {
        "excluded_paths": [
            "C:\\Windows",
            "C:\\Program Files",
            "C:\\Program Files (x86)",
            "C:\\ProgramData",
            "C:\\$Recycle.Bin",
        ],
        "excluded_extensions": [
            ".dll", ".sys", ".exe", ".msi", ".drv", ".ocx"
        ],
        "temp_patterns": [
            "*.tmp", "*.temp", "~*", "$*", "thumbs.db",
            "desktop.ini"
        ],
        "quarantine_path": "C:\\Users\\emilio\\.local-cleaner\\quarantine",
        "log_path": "C:\\Users\\emilio\\.local-cleaner\\logs",
        "max_hash_workers": 4,
        "scan_hidden_files": False,
        "include_system_files": False,
        "old_files_days": 180,
        "duplicate_hash_type": "quick",  # "quick" o "full"
    }
    
    def __init__(self, config_file: str = "resources/config.json"):
        self.config_file = Path(config_file)
        self.config: Dict[str, Any] = {}
        self.load()
    
    def load(self):
        """Carga configuración desde archivo o usa defaults"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
            except Exception as e:
                print(f"Error cargando config: {e}")
                self.config = self.DEFAULT_CONFIG.copy()
        else:
            self.config = self.DEFAULT_CONFIG.copy()
            self.save()
    
    def save(self):
        """Guarda configuración a archivo"""
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Obtiene valor de configuración"""
        return self.config.get(key, default if default is not None else self.DEFAULT_CONFIG.get(key))
    
    def set(self, key: str, value: Any):
        """Establece valor de configuración"""
        self.config[key] = value
        self.save()
    
    def is_path_excluded(self, path: str) -> bool:
        """Verifica si una ruta está excluida"""
        path = Path(path).resolve()
        excluded = self.get("excluded_paths", [])
        
        for exc_path in excluded:
            exc_resolved = Path(exc_path).resolve()
            try:
                # Verifica si path está dentro de exc_path
                path.relative_to(exc_resolved)
                return True
            except ValueError:
                continue
        
        return False
    
    def is_extension_excluded(self, filename: str) -> bool:
        """Verifica si una extensión está excluida"""
        ext = Path(filename).suffix.lower()
        excluded = self.get("excluded_extensions", [])
        return ext in excluded
    
    def is_temp_file(self, filename: str) -> bool:
        """Verifica si un archivo coincide con patrón temporal"""
        import fnmatch
        name = filename.lower()
        patterns = self.get("temp_patterns", [])
        
        for pattern in patterns:
            if fnmatch.fnmatch(name, pattern.lower()):
                return True
        
        return False

    def is_temp_folder(self, path: str) -> bool:
        """Verifica si el archivo está en una carpeta temporal conocida"""
        path_lower = path.lower()
        temp_folders = self.get("temp_folders", [])
        
        for folder in temp_folders:
            if f"\\{folder.lower()}\\" in path_lower or path_lower.endswith(f"\\{folder.lower()}"):
                return True
        
        # Check Windows temp paths
        windows_temp = self.get("windows_temp_paths", [])
        for temp_path in windows_temp:
            if temp_path.lower() in path_lower:
                return True
        
        # Check browser cache patterns
        browser_patterns = self.get("browser_cache_patterns", [])
        for pattern in browser_patterns:
            if pattern.lower().replace("\\*\\", "\\") in path_lower or pattern.lower().replace("*", "") in path_lower:
                return True
        
        return False

    def is_safe_to_delete(self, path: str, filename: str) -> bool:
        """Determina si un archivo es seguro para borrar (temp/cache)"""
        # Check extension
        ext = Path(filename).suffix.lower()
        safe_extensions = self.get("safe_to_delete_extensions", [])
        
        if ext in safe_extensions:
            return True
        
        # Check if in temp folder
        if self.is_temp_folder(path):
            return True
        
        # Check temp file pattern
        if self.is_temp_file(filename):
            return True
        
        return False

    def is_protected_path(self, path: str) -> bool:
        """Verifica si una ruta está protegida (nunca borrar)"""
        path_lower = path.lower()
        protected = self.get("protected_folders", [])
        
        for folder in protected:
            if f"\\{folder.lower()}\\" in path_lower:
                return True
        
        return False
