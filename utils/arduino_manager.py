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
    def __init__(self, arduino_cli_dir):
        """
        Initialize Arduino Manager

        Args:
            arduino_cli_dir: Path to directory where arduino-cli should be installed
                           (e.g., Documents/HOMER/arduino-cli)
        """
        self.arduino_cli_dir = Path(arduino_cli_dir)

        # Determine executable name based on platform
        if platform.system().lower() == "windows":
            self.arduino_cli_path = self.arduino_cli_dir / "arduino-cli.exe"
        else:
            self.arduino_cli_path = self.arduino_cli_dir / "arduino-cli"

        # Create directories
        self.arduino_cli_dir.mkdir(parents=True, exist_ok=True)
        
        # Arduino CLI GitHub API URL for latest release
        self.github_api_url = "https://api.github.com/repos/arduino/arduino-cli/releases/latest"
        
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
    
    def get_platform_info(self):
        """Get platform-specific information for download"""
        system = platform.system().lower()
        machine = platform.machine().lower()

        # Map to arduino-cli naming convention
        if system == "windows":
            os_name = "Windows"
            if "amd64" in machine or "x86_64" in machine:
                arch = "64bit"
            else:
                arch = "32bit"
            extension = "zip"
        elif system == "darwin":
            os_name = "macOS"
            if "arm" in machine or "aarch64" in machine:
                arch = "ARM64"
            else:
                arch = "64bit"
            extension = "tar.gz"
        elif system == "linux":
            os_name = "Linux"
            if "aarch64" in machine or "arm64" in machine:
                arch = "ARM64"
            elif "arm" in machine:
                arch = "ARMv7"
            elif "amd64" in machine or "x86_64" in machine:
                arch = "64bit"
            else:
                arch = "32bit"
            extension = "tar.gz"
        else:
            raise RuntimeError(f"Unsupported platform: {system}")

        return os_name, arch, extension

    def find_download_url(self):
        """Find the correct download URL for current platform from GitHub API"""
        try:
            response = requests.get(self.github_api_url, timeout=10)
            response.raise_for_status()
            release_info = response.json()

            os_name, arch, extension = self.get_platform_info()

            # Expected filename pattern: arduino-cli_<version>_<OS>_<arch>.<extension>
            for asset in release_info.get("assets", []):
                name = asset.get("name", "")
                if os_name in name and arch in name and name.endswith(extension):
                    return asset.get("browser_download_url")

            raise RuntimeError(f"No compatible release found for {os_name} {arch}")

        except Exception as e:
            raise RuntimeError(f"Failed to fetch release info: {e}")

    def download_arduino_cli(self, progress_callback=None):
        """Download and install arduino-cli"""
        try:
            if progress_callback:
                progress_callback("Fetching latest Arduino CLI release info...")

            # Get download URL from GitHub API
            url = self.find_download_url()
            os_name, arch, extension = self.get_platform_info()

            if progress_callback:
                progress_callback(f"Downloading Arduino CLI for {os_name} {arch}...")

            # Download the archive
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()

            # Determine archive file extension
            if extension == "zip":
                archive_path = self.arduino_cli_dir / "arduino-cli-archive.zip"
            else:
                archive_path = self.arduino_cli_dir / "arduino-cli-archive.tar.gz"

            # Write the downloaded file
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0

            with open(archive_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback and total_size > 0:
                            progress = (downloaded / total_size) * 100
                            progress_callback(f"Downloading Arduino CLI... {progress:.1f}%")

            if progress_callback:
                progress_callback("Extracting Arduino CLI...")

            # Extract the archive
            if extension == "zip":
                with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                    zip_ref.extractall(self.arduino_cli_dir)
            else:
                import tarfile
                with tarfile.open(archive_path, 'r:gz') as tar_ref:
                    tar_ref.extractall(self.arduino_cli_dir)

            # Make executable on Unix systems
            if platform.system().lower() != "windows":
                os.chmod(self.arduino_cli_path, 0o755)

            # Clean up archive
            archive_path.unlink()

            if progress_callback:
                progress_callback(f"✓ Arduino CLI installed to {self.arduino_cli_dir}")

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