"""Tests para utilidades de hash"""

import unittest
from pathlib import Path
import tempfile
import os

from utils.hash_utils import HashCalculator


class TestHashCalculator(unittest.TestCase):
    """Tests para HashCalculator"""
    
    def setUp(self):
        """Setup para tests"""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Cleanup después de tests"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_quick_hash_empty_file(self):
        """Test hash rápido de archivo vacío"""
        test_file = Path(self.temp_dir) / "empty.txt"
        test_file.write_text("")
        
        hash_val = HashCalculator.quick_hash(test_file)
        self.assertIsNotNone(hash_val)
        self.assertEqual(len(hash_val), 32)  # MD5
    
    def test_quick_hash_consistency(self):
        """Test que hash rápido es consistente"""
        test_file = Path(self.temp_dir) / "test.txt"
        test_file.write_text("test content")
        
        hash1 = HashCalculator.quick_hash(test_file)
        hash2 = HashCalculator.quick_hash(test_file)
        
        self.assertEqual(hash1, hash2)
    
    def test_full_hash_sha256(self):
        """Test hash completo SHA256"""
        test_file = Path(self.temp_dir) / "test.txt"
        test_file.write_text("test content")
        
        hash_val = HashCalculator.full_hash(test_file, 'sha256')
        self.assertIsNotNone(hash_val)
        self.assertEqual(len(hash_val), 64)  # SHA256
    
    def test_compare_identical_files(self):
        """Test comparación de archivos idénticos"""
        file1 = Path(self.temp_dir) / "file1.txt"
        file2 = Path(self.temp_dir) / "file2.txt"
        
        content = "test content"
        file1.write_text(content)
        file2.write_text(content)
        
        self.assertTrue(HashCalculator.compare_files(file1, file2))
    
    def test_compare_different_files(self):
        """Test comparación de archivos diferentes"""
        file1 = Path(self.temp_dir) / "file1.txt"
        file2 = Path(self.temp_dir) / "file2.txt"
        
        file1.write_text("content 1")
        file2.write_text("content 2")
        
        self.assertFalse(HashCalculator.compare_files(file1, file2))


if __name__ == '__main__':
    unittest.main()
