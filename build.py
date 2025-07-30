#!/usr/bin/env python3
"""
Build script for Mars Load Cell Calibration application.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path


def run_command(command, cwd=None):
    """Run a command and return success status"""
    try:
        result = subprocess.run(command, shell=True, cwd=cwd, check=True, 
                              capture_output=True, text=True)
        print(f"✓ {command}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ {command}")
        print(f"Error: {e.stderr}")
        return False


def check_dependencies():
    """Check if required dependencies are installed"""
    print("Checking dependencies...")
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("✗ Python 3.8 or higher is required")
        return False
    print(f"✓ Python {sys.version}")
    
    # Check if pip packages are installed
    try:
        import PySide6
        import serial
        import toml
        import requests
        print("✓ Required packages are installed")
    except ImportError as e:
        print(f"✗ Missing package: {e}")
        print("Please run: pip install -r requirements.txt")
        return False
    
    return True


def clean_build():
    """Clean previous build artifacts"""
    print("Cleaning build artifacts...")
    
    dirs_to_clean = ['build', 'dist', '__pycache__']
    files_to_clean = ['*.pyc', '*.spec']
    
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"✓ Removed {dir_name}/")
    
    # Clean __pycache__ directories recursively
    for root, dirs, files in os.walk('.'):
        for dir_name in dirs:
            if dir_name == '__pycache__':
                shutil.rmtree(os.path.join(root, dir_name))
                print(f"✓ Removed {os.path.join(root, dir_name)}")


def build_executable():
    """Build the executable using PyInstaller"""
    print("Building executable...")
    
    # Build command
    command = "pyinstaller mars_calibration.spec"
    
    if not run_command(command):
        return False
    
    # Check if executable was created
    exe_name = "MarsLoadCellCalibration.exe" if sys.platform == "win32" else "MarsLoadCellCalibration"
    exe_path = Path("dist") / exe_name
    
    if exe_path.exists():
        print(f"✓ Executable created: {exe_path}")
        print(f"  Size: {exe_path.stat().st_size / (1024*1024):.1f} MB")
        return True
    else:
        print("✗ Executable not found")
        return False


def create_release_package():
    """Create a release package with documentation"""
    print("Creating release package...")
    
    release_dir = Path("release")
    if release_dir.exists():
        shutil.rmtree(release_dir)
    
    release_dir.mkdir()
    
    # Copy executable
    exe_name = "MarsLoadCellCalibration.exe" if sys.platform == "win32" else "MarsLoadCellCalibration"
    exe_source = Path("dist") / exe_name
    exe_dest = release_dir / exe_name
    
    if exe_source.exists():
        shutil.copy2(exe_source, exe_dest)
        print(f"✓ Copied {exe_name} to release/")
    
    # Copy documentation
    docs_to_copy = ["README.md", "requirements.txt"]
    for doc in docs_to_copy:
        if os.path.exists(doc):
            shutil.copy2(doc, release_dir / doc)
            print(f"✓ Copied {doc} to release/")
    
    # Create installation instructions
    install_instructions = """
# Mars Load Cell Calibration - Installation Instructions

## Quick Start
1. Run `MarsLoadCellCalibration.exe` (or `MarsLoadCellCalibration` on Linux/macOS)
2. On first run, the application will offer to download and setup Arduino CLI
3. Follow the setup wizard to install required Arduino libraries
4. Connect your Arduino device and start calibrating!

## System Requirements
- Windows 10/11, macOS 10.14+, or Linux (Ubuntu 18.04+)
- USB port for Arduino connection
- Internet connection for first-time setup (Arduino CLI download)

## Troubleshooting
- If Arduino CLI download fails, you can manually install it from: https://arduino.cc/pro/cli
- Make sure your Arduino device drivers are installed
- Check that the COM port is not in use by other applications

## Data Storage
The application stores logs and calibration data in:
- Windows: `%APPDATA%\\MarsLoadCellCalibration\\`
- macOS: `~/Library/Application Support/MarsLoadCellCalibration/`
- Linux: `~/.local/share/MarsLoadCellCalibration/`

## Support
For issues, please check the logs in the data directory mentioned above.
"""
    
    with open(release_dir / "INSTALL.md", 'w') as f:
        f.write(install_instructions.strip())
    print("✓ Created INSTALL.md")
    
    print(f"✓ Release package created in {release_dir}/")
    return True


def main():
    """Main build process"""
    print("=" * 50)
    print("Mars Load Cell Calibration - Build Script")
    print("=" * 50)
    
    # Change to script directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Clean previous builds
    clean_build()
    
    # Build executable
    if not build_executable():
        print("Build failed!")
        sys.exit(1)
    
    # Create release package
    if not create_release_package():
        print("Release package creation failed!")
        sys.exit(1)
    
    print("\n" + "=" * 50)
    print("✓ Build completed successfully!")
    print("=" * 50)
    print(f"Executable: dist/MarsLoadCellCalibration{''.exe' if sys.platform == 'win32' else ''}")
    print(f"Release package: release/")


if __name__ == "__main__":
    main()