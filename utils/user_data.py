"""
User data directory management for application data storage.
"""

import os
from pathlib import Path
import sys
from . import calibration_resources


class UserDataManager:
    def __init__(self, app_name="MarsLoadCellCalibration"):
        self.app_name = app_name
        self.app_data_dir = self.get_app_data_directory()
        self.setup_directories()
    
    def get_app_data_directory(self):
        """Get the appropriate application data directory for the current OS"""
        if sys.platform == "win32":
            # Windows: Use APPDATA
            base_dir = os.environ.get('APPDATA', os.path.expanduser('~'))
        elif sys.platform == "darwin":
            # macOS: Use ~/Library/Application Support
            base_dir = os.path.expanduser('~/Library/Application Support')
        else:
            # Linux: Use ~/.local/share
            base_dir = os.path.expanduser('~/.local/share')
        
        return Path(base_dir) / self.app_name
    
    def setup_directories(self):
        """Create all necessary subdirectories"""
        # Calibrations directory in Documents/HOMER/mars/
        if sys.platform == "win32":
            documents_dir = Path(os.path.expanduser("~/Documents"))
        elif sys.platform == "darwin":
            # macOS
            documents_dir = Path(os.path.expanduser("~/Documents"))
        else:
            # Linux
            documents_dir = Path(os.path.expanduser("~/Documents"))

        calibrations_dir = documents_dir / "HOMER" / "mars"

        self.directories = {
            'root': self.app_data_dir,
            'logs': self.app_data_dir / 'logs',
            'calibrations': calibrations_dir,
            'arduino_cli': self.app_data_dir / 'arduino-cli',
            'temp': self.app_data_dir / 'temp',
            'compiled': self.app_data_dir / 'compiled_output'
        }

        # Create all directories
        for dir_path in self.directories.values():
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def get_directory(self, name):
        """Get a specific directory path"""
        return self.directories.get(name, self.app_data_dir)
    
    def get_log_file_path(self):
        """Get the main log file path"""
        return self.directories['logs'] / 'application.log'
    
    def get_calibration_file_path(self, filename=None):
        """Get calibration file path, optionally with specific filename"""
        if filename:
            return self.directories['calibrations'] / filename
        return self.directories['calibrations']
    
    def cleanup_temp_files(self):
        """Clean up temporary files"""
        try:
            temp_dir = self.directories['temp']
            if temp_dir.exists():
                for file in temp_dir.iterdir():
                    if file.is_file():
                        file.unlink()
        except Exception as e:
            print(f"Warning: Could not clean temp files: {e}")
    
    def get_arduino_sketches_dir(self):
        """Get directory for Arduino sketches (relative to executable)"""
        if getattr(sys, 'frozen', False):
            # Running as PyInstaller bundle
            base_path = Path(sys._MEIPASS)
        else:
            # Running as script
            base_path = Path(__file__).parent.parent
        
        return base_path
    
    def copy_arduino_sketches(self):
        """
        Create Arduino sketches in user data directory using embedded firmware.
        Uses embedded firmware resources for calibration.ino to ensure the latest code
        is always available. Other sketches are copied from the project directory if available.
        """
        try:
            import shutil
            source_dir = self.get_arduino_sketches_dir()
            target_dir = self.app_data_dir / 'arduino_sketches'
            target_dir.mkdir(parents=True, exist_ok=True)

            # Create calibration firmware using embedded resource (always fresh)
            calibration_dir = target_dir / 'calibration'
            calibration_dir.mkdir(parents=True, exist_ok=True)

            calibration_firmware_path = calibration_dir / 'calibration.ino'
            calibration_resources.write_calibration_firmware(calibration_firmware_path)

            # Copy other sketch directories from project (legacy support)
            other_sketch_dirs = ['loadcell_calibration', 'firmware', 'marsfire', 'imu_program', 'imu_program_teensy']

            for sketch_dir in other_sketch_dirs:
                source_sketch = source_dir / sketch_dir
                target_sketch = target_dir / sketch_dir

                if source_sketch.exists():
                    # Remove old copy if it exists to ensure we get the latest version
                    if target_sketch.exists():
                        shutil.rmtree(target_sketch)
                    # Copy the sketch directory
                    shutil.copytree(source_sketch, target_sketch)

            return target_dir

        except Exception as e:
            print(f"Warning: Could not create Arduino sketches: {e}")
            return self.get_arduino_sketches_dir()