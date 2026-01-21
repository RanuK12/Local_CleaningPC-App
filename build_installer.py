#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Build Script for Local Cleaner
Creates a standalone Windows executable using PyInstaller.

Usage:
    python build_installer.py          # Build executable
    python build_installer.py --clean  # Clean build artifacts first
    python build_installer.py --test   # Build and run test
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path
from datetime import datetime


# Configuration
APP_NAME = "LocalCleaner"
VERSION = "1.1.0"
SPEC_FILE = "LocalCleaner.spec"

# Paths
ROOT_DIR = Path(__file__).parent.absolute()
BUILD_DIR = ROOT_DIR / "build"
DIST_DIR = ROOT_DIR / "dist"
RESOURCES_DIR = ROOT_DIR / "resources"


def print_header(text: str):
    """Print formatted header"""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60 + "\n")


def print_step(text: str):
    """Print step indicator"""
    print(f"→ {text}")


def print_success(text: str):
    """Print success message"""
    print(f"✅ {text}")


def print_error(text: str):
    """Print error message"""
    print(f"❌ {text}")


def clean_build():
    """Remove previous build artifacts"""
    print_step("Cleaning previous build artifacts...")
    
    dirs_to_clean = [BUILD_DIR, DIST_DIR]
    files_to_clean = []
    
    for d in dirs_to_clean:
        if d.exists():
            shutil.rmtree(d)
            print(f"   Removed: {d}")
    
    for f in files_to_clean:
        if f.exists():
            f.unlink()
            print(f"   Removed: {f}")
    
    print_success("Build directory cleaned")


def check_dependencies():
    """Check that all required dependencies are installed"""
    print_step("Checking dependencies...")
    
    # Check PyInstaller via subprocess
    try:
        result = subprocess.run(
            [sys.executable, "-m", "PyInstaller", "--version"],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            print_error("PyInstaller not found")
            print("   Install with: pip install pyinstaller")
            return False
        print(f"   PyInstaller version: {result.stdout.strip()}")
    except Exception as e:
        print_error(f"PyInstaller check failed: {e}")
        return False
    
    # Check other dependencies
    deps = ['PySide6', 'psutil', 'send2trash']
    missing = []
    
    for dep in deps:
        try:
            __import__(dep)
        except ImportError:
            missing.append(dep)
    
    if missing:
        print_error(f"Missing dependencies: {', '.join(missing)}")
        print("   Install with: pip install " + " ".join(missing))
        return False
    
    print_success("All dependencies found")
    return True


def create_icon():
    """Create application icon if it doesn't exist"""
    icon_path = RESOURCES_DIR / "icon.ico"
    
    if not icon_path.exists():
        print_step("Creating placeholder icon...")
        # For now, we'll skip icon creation - user should provide their own
        print("   Note: No icon.ico found. Executable will use default icon.")
        print("   Place your icon at: resources/icon.ico")
    else:
        print_success(f"Icon found: {icon_path}")


def build_executable():
    """Build the executable using PyInstaller"""
    print_header(f"Building {APP_NAME} v{VERSION}")
    
    # Ensure resources directory exists
    RESOURCES_DIR.mkdir(exist_ok=True)
    
    # Check for spec file
    spec_path = ROOT_DIR / SPEC_FILE
    if not spec_path.exists():
        print_error(f"Spec file not found: {spec_path}")
        return False
    
    print_step(f"Running PyInstaller with {SPEC_FILE}...")
    
    try:
        result = subprocess.run(
            [
                sys.executable, "-m", "PyInstaller",
                "--clean",
                "--noconfirm",
                str(spec_path)
            ],
            cwd=str(ROOT_DIR),
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print_error("PyInstaller failed")
            print("STDOUT:", result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout)
            print("STDERR:", result.stderr[-2000:] if len(result.stderr) > 2000 else result.stderr)
            return False
        
        print_success("PyInstaller completed successfully")
        
    except FileNotFoundError:
        print_error("PyInstaller not found. Install with: pip install pyinstaller")
        return False
    except Exception as e:
        print_error(f"Build error: {e}")
        return False
    
    return True


def verify_build():
    """Verify the build was successful"""
    print_step("Verifying build...")
    
    exe_path = DIST_DIR / f"{APP_NAME}.exe"
    
    if not exe_path.exists():
        print_error(f"Executable not found: {exe_path}")
        return False
    
    size_mb = exe_path.stat().st_size / (1024 * 1024)
    print_success(f"Executable created: {exe_path}")
    print(f"   Size: {size_mb:.1f} MB")
    
    return True


def create_release_package():
    """Create a release package with the executable and supporting files"""
    print_step("Creating release package...")
    
    release_dir = DIST_DIR / f"{APP_NAME}-v{VERSION}"
    release_dir.mkdir(exist_ok=True)
    
    # Copy executable
    exe_src = DIST_DIR / f"{APP_NAME}.exe"
    exe_dst = release_dir / f"{APP_NAME}.exe"
    if exe_src.exists():
        shutil.copy2(exe_src, exe_dst)
    
    # Copy README
    readme_src = ROOT_DIR / "README.md"
    if readme_src.exists():
        shutil.copy2(readme_src, release_dir / "README.md")
    
    # Copy LICENSE
    license_src = ROOT_DIR / "LICENSE"
    if license_src.exists():
        shutil.copy2(license_src, release_dir / "LICENSE")
    
    # Create data directory
    (release_dir / "data").mkdir(exist_ok=True)
    (release_dir / "logs").mkdir(exist_ok=True)
    
    print_success(f"Release package created: {release_dir}")
    
    # Create ZIP archive
    zip_path = DIST_DIR / f"{APP_NAME}-v{VERSION}-Windows"
    shutil.make_archive(str(zip_path), 'zip', DIST_DIR, f"{APP_NAME}-v{VERSION}")
    print_success(f"ZIP archive created: {zip_path}.zip")
    
    return True


def main():
    """Main build process"""
    start_time = datetime.now()
    
    print_header("Local Cleaner Build System")
    print(f"Version: {VERSION}")
    print(f"Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Parse arguments
    clean_first = "--clean" in sys.argv
    test_after = "--test" in sys.argv
    
    # Clean if requested
    if clean_first:
        clean_build()
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Create/check icon
    create_icon()
    
    # Build
    if not build_executable():
        sys.exit(1)
    
    # Verify
    if not verify_build():
        sys.exit(1)
    
    # Create release package
    create_release_package()
    
    # Summary
    duration = (datetime.now() - start_time).total_seconds()
    print_header("Build Complete!")
    print(f"Duration: {duration:.1f} seconds")
    print(f"Output: {DIST_DIR / f'{APP_NAME}.exe'}")
    
    # Test if requested
    if test_after:
        print_step("Launching application for testing...")
        exe_path = DIST_DIR / f"{APP_NAME}.exe"
        subprocess.Popen([str(exe_path)])
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
