#!/usr/bin/env python3
"""
Local Cleaner - Desktop Application for Disk Cleanup and Analysis
Entry point for the application

Author: Emilio
License: MIT
"""

import sys
import os
from pathlib import Path

# Add src directory to Python path for module imports
SRC_DIR = Path(__file__).parent / "src"
sys.path.insert(0, str(SRC_DIR))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from ui.main_window import MainWindow
from utils.logger import setup_logger


def main():
    """Main entry point for Local Cleaner application."""
    
    # Initialize logging system
    logger = setup_logger("LocalCleaner", "logs/app.log")
    logger.info("=" * 60)
    logger.info("Starting Local Cleaner Application")
    logger.info("=" * 60)
    
    try:
        # Create Qt application instance
        app = QApplication(sys.argv)
        app.setApplicationName("Local Cleaner")
        app.setApplicationVersion("1.1.0")
        
        # Apply modern Fusion style
        app.setStyle('Fusion')
        
        # Create and show main window
        window = MainWindow()
        window.show()
        
        logger.info("UI initialized successfully")
        
        # Run the application event loop
        sys.exit(app.exec())
        
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        print(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
