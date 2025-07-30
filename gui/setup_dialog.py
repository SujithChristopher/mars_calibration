"""
Setup dialog for first-time application initialization.
"""

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QProgressBar, QTextEdit, QGroupBox)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont

from utils.arduino_manager import ArduinoManager


class SetupWorker(QThread):
    """Worker thread for Arduino environment setup"""
    progress_updated = Signal(str)
    setup_completed = Signal(bool, str)
    
    def __init__(self, arduino_manager):
        super().__init__()
        self.arduino_manager = arduino_manager
    
    def run(self):
        """Run the setup process in background thread"""
        try:
            success = self.arduino_manager.setup_arduino_environment(
                progress_callback=self.progress_updated.emit
            )
            
            if success:
                self.setup_completed.emit(True, "Arduino environment setup completed successfully!")
            else:
                self.setup_completed.emit(False, "Arduino environment setup failed. Some features may not work.")
                
        except Exception as e:
            self.setup_completed.emit(False, f"Setup failed with error: {str(e)}")


class SetupDialog(QDialog):
    """Dialog for first-time application setup"""
    
    def __init__(self, arduino_manager, parent=None):
        super().__init__(parent)
        self.arduino_manager = arduino_manager
        self.setup_thread = None
        self.setup_completed = False
        
        self.setWindowTitle("Mars Load Cell Calibration - First Time Setup")
        self.setModal(True)
        self.setFixedSize(600, 500)
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the dialog UI"""
        layout = QVBoxLayout(self)
        
        # Title
        title_label = QLabel("First Time Setup")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("QLabel { color: #2196F3; margin: 10px; }")
        layout.addWidget(title_label)
        
        # Description
        desc_label = QLabel(
            "This application requires Arduino CLI and specific libraries to function properly.\n"
            "The setup process will:\n\n"
            "• Download Arduino CLI if not present (~50MB)\n"
            "• Install required board packages (Teensy, Arduino)\n"
            "• Install required libraries (LSM9DS1, HX711)\n\n"
            "This is a one-time setup process."
        )
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("QLabel { padding: 15px; background: palette(base); border: 1px solid palette(mid); border-radius: 5px; }")
        layout.addWidget(desc_label)
        
        # Progress section
        progress_group = QGroupBox("Setup Progress")
        progress_layout = QVBoxLayout(progress_group)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.progress_bar.hide()
        progress_layout.addWidget(self.progress_bar)
        
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setMaximumHeight(200)
        self.status_text.setFont(QFont("Consolas", 9))
        progress_layout.addWidget(self.status_text)
        
        layout.addWidget(progress_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.setup_button = QPushButton("Start Setup")
        self.setup_button.setStyleSheet("QPushButton { background: #4CAF50; color: white; padding: 10px 20px; font-weight: bold; }")
        self.setup_button.clicked.connect(self.start_setup)
        button_layout.addWidget(self.setup_button)
        
        self.skip_button = QPushButton("Skip Setup")
        self.skip_button.clicked.connect(self.skip_setup)
        button_layout.addWidget(self.skip_button)
        
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.close_dialog)
        self.close_button.hide()
        button_layout.addWidget(self.close_button)
        
        layout.addLayout(button_layout)
    
    def start_setup(self):
        """Start the Arduino environment setup"""
        self.setup_button.setEnabled(False)
        self.skip_button.setEnabled(False)
        self.progress_bar.show()
        
        self.status_text.append("Starting Arduino environment setup...")
        
        # Start setup in background thread
        self.setup_thread = SetupWorker(self.arduino_manager)
        self.setup_thread.progress_updated.connect(self.update_progress)
        self.setup_thread.setup_completed.connect(self.setup_finished)
        self.setup_thread.start()
    
    def update_progress(self, message):
        """Update progress display"""
        self.status_text.append(message)
        self.status_text.verticalScrollBar().setValue(
            self.status_text.verticalScrollBar().maximum()
        )
    
    def setup_finished(self, success, message):
        """Handle setup completion"""
        self.progress_bar.hide()
        self.setup_completed = success
        
        if success:
            self.status_text.append(f"\n✓ {message}")
            self.setup_button.setText("Setup Complete")
            self.setup_button.setStyleSheet("QPushButton { background: #4CAF50; color: white; padding: 10px 20px; font-weight: bold; }")
        else:
            self.status_text.append(f"\n✗ {message}")
            self.setup_button.setText("Setup Failed")
            self.setup_button.setStyleSheet("QPushButton { background: #f44336; color: white; padding: 10px 20px; font-weight: bold; }")
        
        self.close_button.show()
        self.skip_button.setText("Continue Anyway")
        self.skip_button.setEnabled(True)
    
    def skip_setup(self):
        """Skip the setup process"""
        self.status_text.append("Setup skipped. Some features may not work properly without Arduino CLI.")
        self.accept()
    
    def close_dialog(self):
        """Close the dialog"""
        if self.setup_completed:
            self.accept()
        else:
            self.reject()