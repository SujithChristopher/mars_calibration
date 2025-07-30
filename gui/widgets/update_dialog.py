"""
Update notification dialog for Mars Calibration application.
"""

import sys
from typing import Dict, Any, Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTextEdit, QProgressBar, QMessageBox, QWidget, QFrame
)
from PySide6.QtCore import Qt, QThread, QTimer, Signal, QSize
from PySide6.QtGui import QFont, QPixmap, QIcon

from utils.updater import ApplicationUpdater


class UpdateDownloadThread(QThread):
    """Thread for downloading updates without blocking the UI."""
    
    progress_updated = Signal(int)
    download_completed = Signal(str)  # Path to downloaded file
    download_failed = Signal(str)     # Error message
    
    def __init__(self, updater: ApplicationUpdater, download_url: str):
        super().__init__()
        self.updater = updater
        self.download_url = download_url
        self.downloaded_path = None
    
    def run(self):
        """Download the update in a separate thread."""
        try:
            def progress_callback(progress):
                self.progress_updated.emit(int(progress))
            
            # Download the update
            download_path = self.updater.download_update(self.download_url, progress_callback)
            
            if download_path:
                # Extract and prepare
                executable_path = self.updater.extract_and_prepare_update(download_path)
                if executable_path:
                    self.download_completed.emit(executable_path)
                else:
                    self.download_failed.emit("Failed to extract update")
            else:
                self.download_failed.emit("Failed to download update")
                
        except Exception as e:
            self.download_failed.emit(f"Update download error: {str(e)}")


class UpdateNotificationDialog(QDialog):
    """Dialog to notify user about available updates."""
    
    def __init__(self, update_info: Dict[str, Any], current_version: str, parent=None):
        super().__init__(parent)
        self.update_info = update_info
        self.current_version = current_version
        self.updater = ApplicationUpdater(current_version)
        self.download_thread = None
        self.downloaded_executable_path = None
        
        self.setWindowTitle("Update Available - Mars Calibration")
        self.setWindowIcon(self.parent().windowIcon() if self.parent() else QIcon())
        self.setFixedSize(500, 400)
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)
        
        self.setup_ui()
        self.setup_connections()
    
    def setup_ui(self):
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header_frame = self.create_header()
        layout.addWidget(header_frame)
        
        # Version info
        version_frame = self.create_version_info()
        layout.addWidget(version_frame)
        
        # Release notes
        notes_frame = self.create_release_notes()
        layout.addWidget(notes_frame)
        
        # Progress bar (initially hidden)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("")
        self.status_label.setVisible(False)
        self.status_label.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(self.status_label)
        
        # Buttons
        button_frame = self.create_buttons()
        layout.addWidget(button_frame)
    
    def create_header(self) -> QWidget:
        """Create the header section."""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #f0f0f0;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        
        layout = QHBoxLayout(frame)
        
        # Icon (you can add an icon here)
        icon_label = QLabel("🚀")
        icon_label.setStyleSheet("font-size: 24px;")
        layout.addWidget(icon_label)
        
        # Title
        title_label = QLabel("Update Available!")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(14)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        layout.addStretch()
        
        return frame
    
    def create_version_info(self) -> QWidget:
        """Create version information section."""
        frame = QFrame()
        layout = QVBoxLayout(frame)
        
        # Current version
        current_label = QLabel(f"Current Version: {self.current_version}")
        current_label.setStyleSheet("font-weight: bold; color: #666;")
        layout.addWidget(current_label)
        
        # New version
        new_label = QLabel(f"New Version: {self.update_info['version']}")
        new_label.setStyleSheet("font-weight: bold; color: #2196F3;")
        layout.addWidget(new_label)
        
        # Published date
        published_label = QLabel(f"Published: {self.update_info['published_at'][:10]}")
        published_label.setStyleSheet("color: #888; font-size: 12px;")
        layout.addWidget(published_label)
        
        return frame
    
    def create_release_notes(self) -> QWidget:
        """Create release notes section."""
        frame = QFrame()
        layout = QVBoxLayout(frame)
        
        notes_label = QLabel("What's New:")
        notes_label.setStyleSheet("font-weight: bold; margin-bottom: 5px;")
        layout.addWidget(notes_label)
        
        # Release notes text
        self.notes_text = QTextEdit()
        self.notes_text.setPlainText(self.update_info.get('release_notes', 'No release notes available.'))
        self.notes_text.setReadOnly(True)
        self.notes_text.setMaximumHeight(120)
        self.notes_text.setStyleSheet("""
            QTextEdit {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 8px;
                background-color: #fafafa;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 12px;
            }
        """)
        layout.addWidget(self.notes_text)
        
        return frame
    
    def create_buttons(self) -> QWidget:
        """Create button section."""
        frame = QFrame()
        layout = QHBoxLayout(frame)
        layout.addStretch()
        
        # View Release button
        self.view_release_btn = QPushButton("View Release")
        self.view_release_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: white;
            }
            QPushButton:hover {
                background-color: #f5f5f5;
            }
        """)
        layout.addWidget(self.view_release_btn)
        
        # Skip button
        self.skip_btn = QPushButton("Skip This Version")
        self.skip_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: white;
            }
            QPushButton:hover {
                background-color: #f5f5f5;
            }
        """)
        layout.addWidget(self.skip_btn)
        
        # Update button
        self.update_btn = QPushButton("Update Now")
        self.update_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 20px;
                border: none;
                border-radius: 4px;
                background-color: #2196F3;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:disabled {
                background-color: #ccc;
                color: #888;
            }
        """)
        layout.addWidget(self.update_btn)
        
        return frame
    
    def setup_connections(self):
        """Set up signal connections."""
        self.view_release_btn.clicked.connect(self.view_release)
        self.skip_btn.clicked.connect(self.skip_version)
        self.update_btn.clicked.connect(self.start_update)
    
    def view_release(self):
        """Open the GitHub release page."""
        import webbrowser
        webbrowser.open(self.update_info['release_url'])
    
    def skip_version(self):
        """Skip this version (could be saved to settings)."""
        self.reject()
    
    def start_update(self):
        """Start the update process."""
        if not self.update_info.get('download_url'):
            QMessageBox.warning(self, "Update Error", 
                              "No download URL found for your platform.")
            return
        
        # Disable buttons and show progress
        self.update_btn.setEnabled(False)
        self.skip_btn.setEnabled(False)
        self.view_release_btn.setEnabled(False)
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setVisible(True)
        self.status_label.setText("Downloading update...")
        
        # Start download thread
        self.download_thread = UpdateDownloadThread(self.updater, self.update_info['download_url'])
        self.download_thread.progress_updated.connect(self.update_progress)
        self.download_thread.download_completed.connect(self.download_completed)
        self.download_thread.download_failed.connect(self.download_failed)
        self.download_thread.start()
    
    def update_progress(self, progress: int):
        """Update the progress bar."""
        self.progress_bar.setValue(progress)
        self.status_label.setText(f"Downloading update... {progress}%")
    
    def download_completed(self, executable_path: str):
        """Handle successful download."""
        self.downloaded_executable_path = executable_path
        self.status_label.setText("Download completed! Ready to install.")
        
        # Show install confirmation
        reply = QMessageBox.question(
            self, 
            "Install Update",
            "Update downloaded successfully!\n\n"
            "The application will close and restart with the new version.\n"
            "Do you want to install the update now?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if reply == QMessageBox.Yes:
            self.install_update()
        else:
            # Re-enable buttons if user chooses not to install
            self.reset_ui()
    
    def download_failed(self, error_message: str):
        """Handle download failure."""
        self.status_label.setText("Download failed!")
        QMessageBox.critical(self, "Update Failed", f"Failed to download update:\n{error_message}")
        self.reset_ui()
    
    def install_update(self):
        """Install the downloaded update."""
        if not self.downloaded_executable_path:
            return
        
        self.status_label.setText("Installing update...")
        
        try:
            success = self.updater.install_update(self.downloaded_executable_path)
            if success:
                # The application should exit as part of the update process
                QMessageBox.information(
                    self, 
                    "Update Installed",
                    "Update installed successfully!\nThe application will now restart."
                )
                # Exit the application - the update script will restart it
                sys.exit(0)
            else:
                QMessageBox.critical(self, "Installation Failed", 
                                   "Failed to install the update. Please try again.")
                self.reset_ui()
                
        except Exception as e:
            QMessageBox.critical(self, "Installation Error", 
                               f"Error during installation: {str(e)}")
            self.reset_ui()
    
    def reset_ui(self):
        """Reset UI to initial state."""
        self.update_btn.setEnabled(True)
        self.skip_btn.setEnabled(True)
        self.view_release_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setVisible(False)
    
    def closeEvent(self, event):
        """Handle dialog close event."""
        if self.download_thread and self.download_thread.isRunning():
            reply = QMessageBox.question(
                self,
                "Cancel Update",
                "An update is currently downloading. Do you want to cancel?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.download_thread.terminate()
                self.download_thread.wait()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


class UpdateChecker(QThread):
    """Background thread to check for updates."""
    
    update_available = Signal(dict)  # Emitted when an update is found
    check_completed = Signal()       # Emitted when check is complete
    
    def __init__(self, current_version: str):
        super().__init__()
        self.current_version = current_version
        self.updater = ApplicationUpdater(current_version)
    
    def run(self):
        """Check for updates in background."""
        try:
            update_info = self.updater.check_for_updates()
            if update_info:
                self.update_available.emit(update_info)
        except Exception as e:
            print(f"Update check failed: {e}")
        finally:
            self.check_completed.emit()