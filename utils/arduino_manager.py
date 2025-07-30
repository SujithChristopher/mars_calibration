"""
Arduino CLI and library management utilities.
"""

import os
import sys
import requests
import zipfile
import shutil
import subprocess
import json
from pathlib import Path
import platform


class ArduinoManager:
    def __init__(self, app_data_dir):
        self.app_data_dir = Path(app_data_dir)
        self.arduino_cli_dir = self.app_data_dir / "arduino-cli"
        self.arduino_cli_path = self.arduino_cli_dir / "arduino-cli.exe"
        
        # Create directories
        self.arduino_cli_dir.mkdir(parents=True, exist_ok=True)
        
        # Arduino CLI download URLs for different platforms
        self.cli_urls = {
            "windows": "https://downloads.arduino.cc/arduino-cli/arduino-cli_latest_Windows_64bit.zip",
            "linux": "https://downloads.arduino.cc/arduino-cli/arduino-cli_latest_Linux_64bit.tar.gz",
            "darwin": "https://downloads.arduino.cc/arduino-cli/arduino-cli_latest_macOS_64bit.tar.gz"
        }
        
        # Required libraries for the project
        self.required_libraries = [
            "Arduino_LSM9DS1",
            "HX711 Arduino Library"
        ]
        
        # Required board packages
        self.required_boards = [
            "teensy:avr",
            "arduino:mbed_nano",
            "arduino:samd",
            "arduino:avr"
        ]
    
    def get_platform(self):
        """Get current platform identifier"""
        system = platform.system().lower()
        if system == "windows":
            return "windows"
        elif system == "linux":
            return "linux"
        elif system == "darwin":
            return "darwin"
        else:
            raise RuntimeError(f"Unsupported platform: {system}")
    
    def is_arduino_cli_installed(self):
        """Check if arduino-cli is available"""
        if self.arduino_cli_path.exists():
            return True
        
        # Also check if it's in PATH
        try:
            result = subprocess.run(["arduino-cli", "version"], 
                                  capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def download_arduino_cli(self, progress_callback=None):
        """Download and install arduino-cli"""
        try:
            platform_key = self.get_platform()
            url = self.cli_urls[platform_key]
            
            if progress_callback:
                progress_callback("Downloading Arduino CLI...")
            
            # Download the archive
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            archive_path = self.arduino_cli_dir / "arduino-cli-archive"
            
            # Write the downloaded file
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(archive_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback and total_size > 0:
                            progress = (downloaded / total_size) * 50  # 50% for download
                            progress_callback(f"Downloading Arduino CLI... {progress:.1f}%")
            
            if progress_callback:
                progress_callback("Extracting Arduino CLI...")
            
            # Extract the archive
            if platform_key == "windows":
                with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                    zip_ref.extractall(self.arduino_cli_dir)
            else:
                import tarfile
                with tarfile.open(archive_path, 'r:gz') as tar_ref:
                    tar_ref.extractall(self.arduino_cli_dir)
            
            # Make executable on Unix systems
            if platform_key != "windows":
                self.arduino_cli_path = self.arduino_cli_dir / "arduino-cli"
                os.chmod(self.arduino_cli_path, 0o755)
            
            # Clean up archive
            os.remove(archive_path)
            
            if progress_callback:
                progress_callback("Arduino CLI installed successfully!")
            
            return True
            
        except Exception as e:
            if progress_callback:
                progress_callback(f"Failed to install Arduino CLI: {str(e)}")
            return False
    
    def get_arduino_cli_command(self):
        """Get the arduino-cli command to use"""
        if self.arduino_cli_path.exists():
            return str(self.arduino_cli_path)
        else:
            return "arduino-cli"  # Assume it's in PATH
    
    def initialize_arduino_cli(self, progress_callback=None):
        """Initialize arduino-cli configuration"""
        try:
            cmd = self.get_arduino_cli_command()
            
            if progress_callback:
                progress_callback("Initializing Arduino CLI configuration...")
            
            # Initialize config
            result = subprocess.run([cmd, "config", "init"], 
                                  capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                if progress_callback:
                    progress_callback(f"Config init warning: {result.stderr}")
            
            # Update board package index
            if progress_callback:
                progress_callback("Updating board package index...")
            
            result = subprocess.run([cmd, "core", "update-index"], 
                                  capture_output=True, text=True, timeout=60)
            
            if result.returncode != 0:
                if progress_callback:
                    progress_callback(f"Index update failed: {result.stderr}")
                return False
            
            return True
            
        except Exception as e:
            if progress_callback:
                progress_callback(f"Arduino CLI initialization failed: {str(e)}")
            return False
    
    def install_required_boards(self, progress_callback=None):
        """Install required board packages"""
        cmd = self.get_arduino_cli_command()
        
        for board_package in self.required_boards:
            try:
                if progress_callback:
                    progress_callback(f"Installing board package: {board_package}")
                
                # Check if already installed
                result = subprocess.run([cmd, "core", "list"], 
                                      capture_output=True, text=True, timeout=30)
                
                if board_package in result.stdout:
                    if progress_callback:
                        progress_callback(f"Board package {board_package} already installed")
                    continue
                
                # Install the board package
                result = subprocess.run([cmd, "core", "install", board_package], 
                                      capture_output=True, text=True, timeout=300)
                
                if result.returncode == 0:
                    if progress_callback:
                        progress_callback(f"Successfully installed {board_package}")
                else:
                    if progress_callback:
                        progress_callback(f"Failed to install {board_package}: {result.stderr}")
                
            except Exception as e:
                if progress_callback:
                    progress_callback(f"Error installing {board_package}: {str(e)}")
    
    def install_required_libraries(self, progress_callback=None):
        """Install required Arduino libraries"""
        cmd = self.get_arduino_cli_command()
        
        for library in self.required_libraries:
            try:
                if progress_callback:
                    progress_callback(f"Installing library: {library}")
                
                # Check if already installed
                result = subprocess.run([cmd, "lib", "list"], 
                                      capture_output=True, text=True, timeout=30)
                
                if library in result.stdout:
                    if progress_callback:
                        progress_callback(f"Library {library} already installed")
                    continue
                
                # Install the library
                result = subprocess.run([cmd, "lib", "install", library], 
                                      capture_output=True, text=True, timeout=180)
                
                if result.returncode == 0:
                    if progress_callback:
                        progress_callback(f"Successfully installed {library}")
                else:
                    if progress_callback:
                        progress_callback(f"Failed to install {library}: {result.stderr}")
                
            except Exception as e:
                if progress_callback:
                    progress_callback(f"Error installing {library}: {str(e)}")
    
    def setup_arduino_environment(self, progress_callback=None):
        """Complete setup of Arduino environment"""
        if progress_callback:
            progress_callback("Setting up Arduino environment...")
        
        # Step 1: Check/install arduino-cli
        if not self.is_arduino_cli_installed():
            if not self.download_arduino_cli(progress_callback):
                return False
        else:
            if progress_callback:
                progress_callback("Arduino CLI already available")
        
        # Step 2: Initialize arduino-cli
        if not self.initialize_arduino_cli(progress_callback):
            return False
        
        # Step 3: Install required boards
        self.install_required_boards(progress_callback)
        
        # Step 4: Install required libraries
        self.install_required_libraries(progress_callback)
        
        if progress_callback:
            progress_callback("Arduino environment setup complete!")
        
        return True
    
    def compile_sketch(self, sketch_path, board_fqbn, progress_callback=None):
        """Compile an Arduino sketch"""
        try:
            cmd = self.get_arduino_cli_command()
            
            if progress_callback:
                progress_callback(f"Compiling {Path(sketch_path).name}...")
            
            result = subprocess.run([
                cmd, "compile", 
                "--fqbn", board_fqbn,
                sketch_path
            ], capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0:
                if progress_callback:
                    progress_callback("Compilation successful!")
                return True, result.stdout
            else:
                if progress_callback:
                    progress_callback(f"Compilation failed: {result.stderr}")
                return False, result.stderr
                
        except Exception as e:
            error_msg = f"Compilation error: {str(e)}"
            if progress_callback:
                progress_callback(error_msg)
            return False, error_msg
    
    def upload_sketch(self, sketch_path, board_fqbn, port, progress_callback=None):
        """Upload an Arduino sketch"""
        try:
            cmd = self.get_arduino_cli_command()
            
            if progress_callback:
                progress_callback(f"Uploading to {port}...")
            
            result = subprocess.run([
                cmd, "upload",
                "--fqbn", board_fqbn,
                "--port", port,
                sketch_path
            ], capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0:
                if progress_callback:
                    progress_callback("Upload successful!")
                return True, result.stdout
            else:
                if progress_callback:
                    progress_callback(f"Upload failed: {result.stderr}")
                return False, result.stderr
                
        except Exception as e:
            error_msg = f"Upload error: {str(e)}"
            if progress_callback:
                progress_callback(error_msg)
            return False, error_msg