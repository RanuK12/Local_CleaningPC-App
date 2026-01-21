"""
Base de datos SQLite para indexado de archivos
"""

import sqlite3
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from .models import FileInfo, DuplicateGroup


class Database:
    """Gestor de base de datos SQLite"""
    
    def __init__(self, db_path: str = "data/inventory.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = None
        self.init_db()
    
    def init_db(self):
        """Inicializa la base de datos con tablas"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Tabla de archivos
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                extension TEXT,
                size INTEGER,
                created_time TEXT,
                modified_time TEXT,
                accessed_time TEXT,
                is_directory BOOLEAN,
                parent_path TEXT,
                owner TEXT,
                quick_hash TEXT,
                full_hash TEXT,
                scan_date TEXT,
                category TEXT DEFAULT 'Unknown',
                category_confidence TEXT DEFAULT 'Low',
                indexed_date TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Tabla de duplicados
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS duplicates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hash_value TEXT NOT NULL,
                file_count INTEGER,
                total_size INTEGER,
                scan_date TEXT
            )
        """)
        
        # Tabla de candidatos a limpiar
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cleanup_candidates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL,
                category TEXT,
                risk_level TEXT,
                reason TEXT,
                saved_space INTEGER,
                recommended_action TEXT,
                created_date TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Tabla de acciones de limpieza
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cleanup_actions (
                id TEXT PRIMARY KEY,
                file_path TEXT NOT NULL,
                action_type TEXT,
                target_path TEXT,
                dry_run BOOLEAN,
                status TEXT,
                error_message TEXT,
                timestamp TEXT,
                created_date TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Índices para búsquedas rápidas
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_extension ON files(extension)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_size ON files(size)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_parent ON files(parent_path)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_quick_hash ON files(quick_hash)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_full_hash ON files(full_hash)")
        
        # Índices adicionales para mejor rendimiento
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_category ON files(category)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_modified ON files(modified_time)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_name ON files(name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_hash_size ON files(quick_hash, size)")
        
        conn.commit()
    
    def get_connection(self) -> sqlite3.Connection:
        """Obtiene conexión a BD"""
        if self.connection is None:
            self.connection = sqlite3.connect(str(self.db_path), check_same_thread=False)
            self.connection.row_factory = sqlite3.Row
            # Optimizar configuración SQLite para mejor rendimiento
            self.connection.execute("PRAGMA journal_mode=WAL")
            self.connection.execute("PRAGMA synchronous=NORMAL")
            self.connection.execute("PRAGMA cache_size=10000")
            self.connection.execute("PRAGMA temp_store=MEMORY")
        return self.connection
    
    def close(self):
        """Cierra conexión de forma segura"""
        if self.connection:
            try:
                self.connection.execute("PRAGMA optimize")
                self.connection.close()
            except Exception:
                pass
            finally:
                self.connection = None
    
    def insert_file(self, file_info: FileInfo) -> int:
        """Inserta un archivo en la BD"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO files 
                (path, name, extension, size, created_time, modified_time, 
                 accessed_time, is_directory, parent_path, owner, quick_hash, 
                 full_hash, scan_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                file_info.path,
                file_info.name,
                file_info.extension,
                file_info.size,
                file_info.created_time.isoformat() if file_info.created_time else None,
                file_info.modified_time.isoformat() if file_info.modified_time else None,
                file_info.accessed_time.isoformat() if file_info.accessed_time else None,
                file_info.is_directory,
                file_info.parent_path,
                file_info.owner,
                file_info.quick_hash,
                file_info.full_hash,
                datetime.now().isoformat()
            ))
            
            conn.commit()
            return cursor.lastrowid
        
        except Exception as e:
            print(f"Error insertando archivo: {e}")
            return None
    
    def bulk_insert_files(self, files: List[FileInfo]):
        """Inserta múltiples archivos"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        data = []
        for file_info in files:
            data.append((
                file_info.path,
                file_info.name,
                file_info.extension,
                file_info.size,
                file_info.created_time.isoformat() if file_info.created_time else None,
                file_info.modified_time.isoformat() if file_info.modified_time else None,
                file_info.accessed_time.isoformat() if file_info.accessed_time else None,
                file_info.is_directory,
                file_info.parent_path,
                file_info.owner,
                file_info.quick_hash,
                file_info.full_hash,
                datetime.now().isoformat()
            ))
        
        cursor.executemany("""
            INSERT OR REPLACE INTO files 
            (path, name, extension, size, created_time, modified_time, 
             accessed_time, is_directory, parent_path, owner, quick_hash, 
             full_hash, scan_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, data)
        
        conn.commit()
    
    def get_file_by_path(self, path: str) -> Optional[FileInfo]:
        """Obtiene archivo por ruta"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM files WHERE path = ?", (path,))
        row = cursor.fetchone()
        
        if row:
            return self._row_to_fileinfo(row)
        return None
    
    def get_files_by_extension(self, extension: str) -> List[FileInfo]:
        """Obtiene archivos por extensión"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM files WHERE extension = ?", (extension,))
        rows = cursor.fetchall()
        
        return [self._row_to_fileinfo(row) for row in rows]
    
    def get_large_files(self, min_size: int, limit: int = 100) -> List[FileInfo]:
        """Obtiene archivos más grandes"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM files WHERE size >= ? AND NOT is_directory "
            "ORDER BY size DESC LIMIT ?",
            (min_size, limit)
        )
        rows = cursor.fetchall()
        
        return [self._row_to_fileinfo(row) for row in rows]
    
    def get_duplicates_by_hash(self, hash_value: str) -> List[FileInfo]:
        """Obtiene archivos con mismo hash"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM files WHERE quick_hash = ? ORDER BY path",
            (hash_value,)
        )
        rows = cursor.fetchall()
        
        return [self._row_to_fileinfo(row) for row in rows]
    
    def get_all_files(self, exclude_dirs: bool = True, limit: int = None, offset: int = 0) -> List[FileInfo]:
        """
        Obtiene archivos con paginación opcional para mejor rendimiento.
        
        Args:
            exclude_dirs: Excluir directorios
            limit: Número máximo de resultados (None = sin límite)
            offset: Offset para paginación
            
        Returns:
            Lista de FileInfo
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM files"
        params = []
        
        if exclude_dirs:
            query += " WHERE NOT is_directory"
        
        query += " ORDER BY size DESC"
        
        if limit is not None:
            query += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        return [self._row_to_fileinfo(row) for row in rows]
    
    def get_file_count(self, exclude_dirs: bool = True) -> int:
        """Obtiene conteo total de archivos para paginación"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = "SELECT COUNT(*) FROM files"
        if exclude_dirs:
            query += " WHERE NOT is_directory"
        
        cursor.execute(query)
        return cursor.fetchone()[0]
    
    def clear_scan(self):
        """Limpia escaneo previo"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM files")
        cursor.execute("DELETE FROM duplicates")
        cursor.execute("DELETE FROM cleanup_candidates")
        conn.commit()
    
    def get_statistics(self) -> dict:
        """Obtiene estadísticas de la BD"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) as count, SUM(size) as total_size FROM files WHERE NOT is_directory")
        row = cursor.fetchone()
        
        return {
            'total_files': row['count'] or 0,
            'total_size': row['total_size'] or 0,
        }
    
    @staticmethod
    def _row_to_fileinfo(row) -> FileInfo:
        """Convierte row de BD a FileInfo"""
        return FileInfo(
            id=row['id'],
            path=row['path'],
            name=row['name'],
            extension=row['extension'],
            size=row['size'],
            created_time=datetime.fromisoformat(row['created_time']) if row['created_time'] else None,
            modified_time=datetime.fromisoformat(row['modified_time']) if row['modified_time'] else None,
            accessed_time=datetime.fromisoformat(row['accessed_time']) if row['accessed_time'] else None,
            is_directory=row['is_directory'],
            parent_path=row['parent_path'],
            owner=row['owner'],
            quick_hash=row['quick_hash'],
            full_hash=row['full_hash']
        )
