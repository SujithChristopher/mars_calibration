"""
Auto-update utility for Mars Calibration application.
Checks GitHub releases for newer versions and handles binary updates.
"""

import os
import sys
import json
import platform
import subprocess
import tempfile
import zipfile
import tarfile
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
import requests
from packaging import version


class ApplicationUpdater:
    def __init__(self, current_version: str, repo_owner: str = "SujithChristopher", repo_name: str = "mars_calibration"):
        self.current_version = current_version
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.github_api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases/latest"
        self.platform = self._detect_platform()
        
    def _detect_platform(self) -> str:
        """Detect the current platform for selecting correct binary."""
        system = platform.system().lower()
        if system == "windows":
            return "windows"
        elif system == "darwin":
            return "macos"
        elif system == "linux":
            return "linux"
        else:
            return "unknown"
    
    def check_for_updates(self) -> Optional[Dict[str, Any]]:
        """
        Check GitHub releases for a newer version.
        
        Returns:
            Dict with update info if available, None if no update or error
        """
        try:
            response = requests.get(self.github_api_url, timeout=10)
            response.raise_for_status()
            
            release_data = response.json()
            latest_version = release_data["tag_name"].lstrip("v")
            
            # Compare versions
            if version.parse(latest_version) > version.parse(self.current_version):
                # Find the appropriate binary for current platform
                download_url = self._find_platform_binary(release_data["assets"])
                
                if download_url:
                    return {
                        "version": latest_version,
                        "tag_name": release_data["tag_name"],
                        "release_notes": release_data.get("body", ""),
                        "download_url": download_url,
                        "published_at": release_data["published_at"],
                        "release_url": release_data["html_url"]
                    }
            
            return None
            
        except requests.RequestException as e:
            print(f"Failed to check for updates: {e}")
            return None
        except Exception as e:
            print(f"Update check error: {e}")
            return None
    
    def _find_platform_binary(self, assets: list) -> Optional[str]:
        """Find the download URL for the current platform."""
        platform_mappings = {
            "windows": "Windows-x64.zip",
            "macos": "macOS-x64.tar.gz",
            "linux": "Linux-x64.tar.gz"
        }
        
        target_suffix = platform_mappings.get(self.platform)
        if not target_suffix:
            return None
        
        for asset in assets:
            if asset["name"].endswith(target_suffix):
                return asset["browser_download_url"]
        
        return None
    
    def download_update(self, download_url: str, progress_callback=None) -> Optional[str]:
        """
        Download the update binary.
        
        Args:
            download_url: URL to download the update from
            progress_callback: Optional callback for progress updates
            
        Returns:
            Path to downloaded file, or None if failed
        """
        try:
            # Create temporary directory for download
            temp_dir = tempfile.mkdtemp(prefix="mars_calibration_update_")
            filename = download_url.split("/")[-1]
            download_path = os.path.join(temp_dir, filename)
            
            # Download with progress
            response = requests.get(download_url, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(download_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if progress_callback and total_size > 0:
                            progress = (downloaded / total_size) * 100
                            progress_callback(progress)
            
            return download_path
            
        except Exception as e:
            print(f"Download failed: {e}")
            return None
    
    def extract_and_prepare_update(self, archive_path: str) -> Optional[str]:
        """
        Extract the downloaded archive and prepare for installation.
        
        Args:
            archive_path: Path to downloaded archive
            
        Returns:
            Path to extracted executable, or None if failed
        """
        try:
            extract_dir = os.path.join(os.path.dirname(archive_path), "extracted")
            os.makedirs(extract_dir, exist_ok=True)
            
            # Extract based on file type
            if archive_path.endswith('.zip'):
                with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
            elif archive_path.endswith('.tar.gz'):
                with tarfile.open(archive_path, 'r:gz') as tar_ref:
                    tar_ref.extractall(extract_dir)
            else:
                print(f"Unsupported archive format: {archive_path}")
                return None
            
            # Find the executable
            executable_name = "MarsCalibration.exe" if self.platform == "windows" else "MarsCalibration"
            
            for root, dirs, files in os.walk(extract_dir):
                for file in files:
                    if file == executable_name:
                        return os.path.join(root, file)
            
            print(f"Executable {executable_name} not found in archive")
            return None
            
        except Exception as e:
            print(f"Extraction failed: {e}")
            return None
    
    def install_update(self, new_executable_path: str) -> bool:
        """
        Install the update by replacing the current executable.
        
        Args:
            new_executable_path: Path to the new executable
            
        Returns:
            True if successful, False otherwise
        """
        try:
            current_executable = sys.executable
            if getattr(sys, 'frozen', False):
                # Running as compiled executable
                current_executable = sys.executable
            else:
                # Running as Python script - can't really update
                print("Cannot update when running from Python source")
                return False
            
            # Create backup
            backup_path = current_executable + ".backup"
            if os.path.exists(backup_path):
                os.remove(backup_path)
            
            # On Windows, we need to use a batch script to replace the running executable
            if self.platform == "windows":
                return self._install_update_windows(current_executable, new_executable_path, backup_path)
            else:
                return self._install_update_unix(current_executable, new_executable_path, backup_path)
            
        except Exception as e:
            print(f"Installation failed: {e}")
            return False
    
    def _install_update_windows(self, current_exe: str, new_exe: str, backup_path: str) -> bool:
        """Windows-specific update installation."""
        try:
            # Create update script
            script_content = f'''@echo off
timeout /t 2 /nobreak > nul
move "{current_exe}" "{backup_path}"
move "{new_exe}" "{current_exe}"
start "" "{current_exe}"
del "%~f0"
'''
            
            script_path = os.path.join(tempfile.gettempdir(), "mars_calibration_update.bat")
            with open(script_path, 'w') as f:
                f.write(script_content)
            
            # Start update script and exit
            subprocess.Popen([script_path], shell=True)
            return True
            
        except Exception as e:
            print(f"Windows update failed: {e}")
            return False
    
    def _install_update_unix(self, current_exe: str, new_exe: str, backup_path: str) -> bool:
        """Unix/macOS-specific update installation."""
        try:
            # Create update script
            script_content = f'''#!/bin/bash
sleep 2
mv "{current_exe}" "{backup_path}"
mv "{new_exe}" "{current_exe}"
chmod +x "{current_exe}"
nohup "{current_exe}" &
rm "$0"
'''
            
            script_path = os.path.join(tempfile.gettempdir(), "mars_calibration_update.sh")
            with open(script_path, 'w') as f:
                f.write(script_content)
            
            os.chmod(script_path, 0o755)
            
            # Start update script and exit
            subprocess.Popen(['/bin/bash', script_path])
            return True
            
        except Exception as e:
            print(f"Unix update failed: {e}")
            return False
    
    def cleanup_temp_files(self, temp_paths: list):
        """Clean up temporary files and directories."""
        for path in temp_paths:
            try:
                if os.path.isfile(path):
                    os.remove(path)
                elif os.path.isdir(path):
                    import shutil
                    shutil.rmtree(path)
            except Exception as e:
                print(f"Cleanup failed for {path}: {e}")


# Convenience function for simple update check
def check_for_app_updates(current_version: str) -> Optional[Dict[str, Any]]:
    """Simple function to check for updates."""
    updater = ApplicationUpdater(current_version)
    return updater.check_for_updates()