"""
Utilidades para cálculo de hashes (detección de duplicados)
"""

import hashlib
from pathlib import Path
from typing import Tuple


class HashCalculator:
    """Calcula hashes de archivos para detectar duplicados"""
    
    # Tamaño de bloque para lectura
    BLOCK_SIZE = 65536  # 64 KB
    
    @staticmethod
    def quick_hash(file_path) -> str:
        """
        Hash rápido: solo primeros y últimos KB + tamaño
        Útil para pre-filtrado de duplicados
        
        Args:
            file_path: Ruta del archivo (str or Path)
        
        Returns:
            Hash hexadecimal
        """
        try:
            # Convert to Path if string
            if isinstance(file_path, str):
                file_path = Path(file_path)
            
            file_size = file_path.stat().st_size
            
            if file_size == 0:
                return hashlib.md5(b"empty").hexdigest()
            
            hash_obj = hashlib.md5()
            
            # Leer primeros 64 KB
            with open(file_path, 'rb') as f:
                chunk = f.read(HashCalculator.BLOCK_SIZE)
                hash_obj.update(chunk)
            
            # Leer últimos 64 KB si el archivo es mayor
            if file_size > HashCalculator.BLOCK_SIZE:
                with open(file_path, 'rb') as f:
                    f.seek(-HashCalculator.BLOCK_SIZE, 2)  # Seek desde el final
                    chunk = f.read(HashCalculator.BLOCK_SIZE)
                    hash_obj.update(chunk)
            
            # Incluir tamaño en hash
            hash_obj.update(str(file_size).encode())
            
            return hash_obj.hexdigest()
        
        except (IOError, OSError):
            return None
    
    @staticmethod
    def full_hash(file_path, algorithm: str = 'sha256') -> str:
        """
        Hash completo del archivo
        
        Args:
            file_path: Ruta del archivo (str or Path)
            algorithm: Algoritmo (md5, sha256, etc.)
        
        Returns:
            Hash hexadecimal
        """
        try:
            # Convert to Path if string
            if isinstance(file_path, str):
                file_path = Path(file_path)
            
            hash_obj = hashlib.new(algorithm)
            
            with open(file_path, 'rb') as f:
                while True:
                    chunk = f.read(HashCalculator.BLOCK_SIZE)
                    if not chunk:
                        break
                    hash_obj.update(chunk)
            
            return hash_obj.hexdigest()
        
        except (IOError, OSError):
            return None
    
    @staticmethod
    def compare_files(file1: Path, file2: Path) -> bool:
        """
        Compara dos archivos para verificar si son idénticos
        
        Args:
            file1: Primera ruta
            file2: Segunda ruta
        
        Returns:
            True si son idénticos
        """
        try:
            # Primero comparar por tamaño
            if file1.stat().st_size != file2.stat().st_size:
                return False
            
            # Luego por hash rápido
            if HashCalculator.quick_hash(file1) != HashCalculator.quick_hash(file2):
                return False
            
            # Finalmente por hash completo
            return HashCalculator.full_hash(file1) == HashCalculator.full_hash(file2)
        
        except (IOError, OSError):
            return False
