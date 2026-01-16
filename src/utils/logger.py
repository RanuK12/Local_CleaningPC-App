"""
Sistema de logging estructurado
"""

import logging
import logging.handlers
from pathlib import Path
from datetime import datetime


def setup_logger(name: str, log_file: str = None) -> logging.Logger:
    """
    Configura logger con salida a archivo y consola
    
    Args:
        name: Nombre del logger
        log_file: Ruta al archivo de log (opcional)
    
    Returns:
        Logger configurado
    """
    
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    # Crear directorio de logs si no existe
    if log_file:
        log_path = Path(log_file).parent
        log_path.mkdir(parents=True, exist_ok=True)
    
    # Formato de logs
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Handler para consola
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Handler para archivo
    if log_file:
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


class ActionLogger:
    """Logger para acciones de limpieza/borrado"""
    
    def __init__(self, log_file: str = None):
        self.log_file = log_file or "logs/actions.log"
        Path(self.log_file).parent.mkdir(parents=True, exist_ok=True)
        self.logger = setup_logger("Actions", self.log_file)
    
    def log_action(self, action: str, target: str, status: str, details: str = ""):
        """
        Log de una acción
        
        Args:
            action: Tipo de acción (move, delete, analyze, etc.)
            target: Archivo/carpeta afectada
            status: Estado (success, fail, simulation, etc.)
            details: Detalles adicionales
        """
        msg = f"[{action.upper()}] {target} - {status}"
        if details:
            msg += f" ({details})"
        
        if status in ["fail", "error"]:
            self.logger.error(msg)
        elif status == "simulation":
            self.logger.info(f"[SIMULATION] {msg}")
        else:
            self.logger.info(msg)
    
    def log_scan_start(self, paths: list):
        """Log inicio de escaneo"""
        self.logger.info(f"ESCANEO INICIADO: {', '.join(paths)}")
    
    def log_scan_complete(self, file_count: int, total_size: int, duration: float):
        """Log finalización de escaneo"""
        self.logger.info(
            f"ESCANEO COMPLETADO: {file_count} archivos, "
            f"{self._format_size(total_size)}, {duration:.2f}s"
        )
    
    def log_analysis_result(self, category: str, count: int, saved_space: int):
        """Log resultado de análisis"""
        self.logger.info(
            f"ANÁLISIS - {category}: {count} items, "
            f"espacio potencial: {self._format_size(saved_space)}"
        )
    
    @staticmethod
    def _format_size(bytes_size: int) -> str:
        """Formatea tamaño en bytes a legible"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_size < 1024.0:
                return f"{bytes_size:.2f} {unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.2f} PB"
