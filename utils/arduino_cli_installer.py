"""
Arduino CLI installer utility - downloads and installs arduino-cli if not present.
"""

import os
import sys
import platform
import zipfile
import tarfile
import requests
from pathlib import Path


class ArduinoCLIInstaller:
    """Manages arduino-cli installation and updates"""

    # Arduino CLI latest release URL
    GITHUB_API_URL = "https://api.github.com/repos/arduino/arduino-cli/releases/latest"

    def __init__(self, install_dir):
        """
        Initialize installer

        Args:
            install_dir: Path to directory where arduino-cli should be installed
        """
        self.install_dir = Path(install_dir)
        self.install_dir.mkdir(parents=True, exist_ok=True)

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

    def get_executable_path(self):
        """Get the path to the arduino-cli executable"""
        if sys.platform == "win32":
            return self.install_dir / "arduino-cli.exe"
        else:
            return self.install_dir / "arduino-cli"

    def is_installed(self):
        """Check if arduino-cli is already installed"""
        exe_path = self.get_executable_path()
        return exe_path.exists() and exe_path.is_file()

    def get_latest_release_info(self):
        """Fetch latest release information from GitHub API"""
        try:
            response = requests.get(self.GITHUB_API_URL, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise RuntimeError(f"Failed to fetch release info: {e}")

    def find_download_url(self, release_info):
        """Find the correct download URL for current platform"""
        os_name, arch, extension = self.get_platform_info()

        # Expected filename pattern: arduino-cli_<version>_<OS>_<arch>.<extension>
        # Example: arduino-cli_0.35.3_Windows_64bit.zip

        for asset in release_info.get("assets", []):
            name = asset.get("name", "")
            if os_name in name and arch in name and name.endswith(extension):
                return asset.get("browser_download_url")

        raise RuntimeError(f"No compatible release found for {os_name} {arch}")

    def download_file(self, url, dest_path, progress_callback=None):
        """
        Download file with progress tracking

        Args:
            url: Download URL
            dest_path: Destination file path
            progress_callback: Optional callback(downloaded_bytes, total_bytes)
        """
        try:
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0

            with open(dest_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback:
                            progress_callback(downloaded, total_size)

            return True
        except Exception as e:
            if dest_path.exists():
                dest_path.unlink()
            raise RuntimeError(f"Download failed: {e}")

    def extract_archive(self, archive_path, extract_to):
        """Extract zip or tar.gz archive"""
        try:
            if archive_path.suffix == '.zip':
                with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_to)
            elif archive_path.name.endswith('.tar.gz'):
                with tarfile.open(archive_path, 'r:gz') as tar_ref:
                    tar_ref.extractall(extract_to)
            else:
                raise RuntimeError(f"Unsupported archive format: {archive_path}")

            return True
        except Exception as e:
            raise RuntimeError(f"Extraction failed: {e}")

    def make_executable(self, file_path):
        """Make file executable on Unix systems"""
        if sys.platform != "win32":
            os.chmod(file_path, 0o755)

    def install(self, progress_callback=None):
        """
        Download and install arduino-cli

        Args:
            progress_callback: Optional callback(downloaded_bytes, total_bytes)

        Returns:
            Path to installed executable
        """
        if self.is_installed():
            return self.get_executable_path()

        try:
            # Get latest release info
            release_info = self.get_latest_release_info()
            version = release_info.get("tag_name", "unknown")

            # Find download URL
            download_url = self.find_download_url(release_info)

            # Download to temp directory
            temp_dir = self.install_dir / "temp"
            temp_dir.mkdir(parents=True, exist_ok=True)

            os_name, arch, extension = self.get_platform_info()
            archive_name = f"arduino-cli_{version}_{os_name}_{arch}.{extension}"
            archive_path = temp_dir / archive_name

            # Download
            self.download_file(download_url, archive_path, progress_callback)

            # Extract
            self.extract_archive(archive_path, self.install_dir)

            # Make executable on Unix
            exe_path = self.get_executable_path()
            self.make_executable(exe_path)

            # Cleanup
            archive_path.unlink()
            temp_dir.rmdir()

            # Verify installation
            if not self.is_installed():
                raise RuntimeError("Installation verification failed")

            return exe_path

        except Exception as e:
            raise RuntimeError(f"Installation failed: {e}")

    def get_version(self):
        """Get installed arduino-cli version"""
        if not self.is_installed():
            return None

        try:
            import subprocess
            result = subprocess.run(
                [str(self.get_executable_path()), "version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                # Parse version from output
                return result.stdout.strip()
            return None
        except Exception:
            return None


def ensure_arduino_cli(install_dir, progress_callback=None):
    """
    Ensure arduino-cli is installed, download if necessary

    Args:
        install_dir: Directory to install arduino-cli
        progress_callback: Optional callback(downloaded_bytes, total_bytes)

    Returns:
        Path to arduino-cli executable
    """
    installer = ArduinoCLIInstaller(install_dir)

    if installer.is_installed():
        return installer.get_executable_path()

    return installer.install(progress_callback)
