"""Tests para configuración"""

import unittest
from pathlib import Path
import tempfile
import json

from utils.config import Config


class TestConfig(unittest.TestCase):
    """Tests para Config"""
    
    def setUp(self):
        """Setup para tests"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.config_file = self.temp_dir / "test_config.json"
    
    def tearDown(self):
        """Cleanup"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_default_config(self):
        """Test que los defaults se cargan"""
        config = Config(str(self.config_file))
        
        self.assertIsNotNone(config.get('excluded_paths'))
        self.assertIsNotNone(config.get('excluded_extensions'))
    
    def test_save_and_load(self):
        """Test guardar y cargar configuración"""
        config = Config(str(self.config_file))
        config.set('test_key', 'test_value')
        
        # Recargar
        config2 = Config(str(self.config_file))
        self.assertEqual(config2.get('test_key'), 'test_value')
    
    def test_path_excluded(self):
        """Test exclusión de ruta"""
        config = Config(str(self.config_file))
        
        # Debería estar excluido por defecto
        self.assertTrue(config.is_path_excluded("C:\\Windows"))
        self.assertTrue(config.is_path_excluded("C:\\Windows\\System32"))
    
    def test_extension_excluded(self):
        """Test exclusión de extensión"""
        config = Config(str(self.config_file))
        
        self.assertTrue(config.is_extension_excluded("file.dll"))
        self.assertFalse(config.is_extension_excluded("file.txt"))


if __name__ == '__main__':
    unittest.main()
