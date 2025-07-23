"""
Centralized logging utility for Load Cell & IMU Calibration application.
"""

import os
from datetime import datetime


class Logger:
    """Centralized logging class for file and UI logging"""
    
    def __init__(self, log_file_path):
        self.log_file_path = log_file_path
        self.ensure_log_directory()
        self.write_session_header()
        
    def ensure_log_directory(self):
        """Create logs directory if it doesn't exist"""
        log_dir = os.path.dirname(self.log_file_path)
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
    def write_session_header(self):
        """Write session start header to log file"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        header = f"\n{'='*60}\nLOAD CELL CALIBRATION SESSION START\nTimestamp: {timestamp}\n{'='*60}\n"
        self.write_to_file(header)
        
    def write_to_file(self, message):
        """Write message to log file"""
        try:
            with open(self.log_file_path, 'a', encoding='utf-8') as f:
                f.write(message)
                f.flush()  # Ensure immediate write
        except Exception as e:
            print(f"Error writing to log file: {e}")
            
    def log(self, message, category="INFO"):
        """Log message with timestamp and category"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]  # Include milliseconds
        log_entry = f"[{timestamp}] [{category}] {message}\n"
        self.write_to_file(log_entry)
        return f"[{timestamp.split()[1]}] {message}"  # Return just time for UI
        
    def log_error(self, message):
        """Log error message"""
        return self.log(message, "ERROR")
        
    def log_success(self, message):
        """Log success message"""
        return self.log(message, "SUCCESS")
        
    def log_warning(self, message):
        """Log warning message"""
        return self.log(message, "WARNING")
        
    def log_step(self, message):
        """Log step progress"""
        return self.log(message, "STEP")
        
    def log_serial(self, message, direction="RX"):
        """Log serial communication"""
        return self.log(message, f"SERIAL_{direction}")
        
    def log_upload(self, message):
        """Log upload activities"""
        return self.log(message, "UPLOAD")
        
    def log_calibration(self, message):
        """Log calibration activities"""
        return self.log(message, "CALIBRATION")

    def log_imu(self, message):
        """Log IMU activities"""
        return self.log(message, "IMU")