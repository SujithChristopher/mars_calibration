"""
Main window class for Load Cell & IMU Calibration application.
"""

import os
import sys
import threading
import time
import subprocess
import re
import serial
import serial.tools.list_ports
from datetime import datetime
import toml
import glob

from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QTabWidget, QMessageBox, QLabel, QDialog, QTableWidgetItem
from PySide6.QtCore import QTimer, Signal, QThread, QObject, Qt
from PySide6.QtGui import QFont, QTextCursor

from utils.logger import Logger
from utils.user_data import UserDataManager
from utils.arduino_manager import ArduinoManager
from gui.workers.serial_worker import SerialWorker
from gui.workers.imu_worker import IMUDataWorker
from gui.load_cell_tab import setup_load_cell_tab
from gui.imu_tab import setup_imu_tab
from gui.upload_firmware_tab import setup_upload_firmware_tab
from gui.setup_dialog import SetupDialog
from gui.widgets.update_dialog import UpdateNotificationDialog, UpdateChecker
from version import get_version_string


class LoadCellCalibrationGUI(QMainWindow):
    # Add signals for thread-safe logging and step updates
    log_signal = Signal(str)
    step_update_signal = Signal(int, str)  # step number, message
    
    def __init__(self):
        super().__init__()
        # Get version and set window title
        self.current_version = get_version_string()
        self.setWindowTitle(f"Mars Calibration v{self.current_version} - Load Cell & IMU Calibration System")
        
        # Set responsive window size based on screen ratio
        # For 16:9 screens with taskbar: 1280x720, for 16:10 screens: 1280x750
        self.setGeometry(100, 100, 1280, 720)
        self.setMinimumSize(1000, 580)  # Minimum size for usability
        
        # Serial connection variables
        self.serial_worker = None
        self.serial_thread = None
        self.is_connected = False
        self.current_calibration_factor = 1.0
        
        # IMU connection variables
        self.imu_worker = None
        self.imu_thread = None
        self.is_imu_connected = False
        self.current_imu_data = {}
        
        # Current IMU offsets
        self.current_offset_x = 0.0
        self.current_offset_y = 0.0
        self.current_offset_z = 0.0
        
        # IMU calibration state tracking
        self.imu_calibration_started = False
        
        # 3-IMU system variables
        self.current_imu_index = 0  # 0=IMU1, 1=IMU2, 2=IMU3
        
        # Saved angle offsets for all 3 IMUs
        # 4-Offset Formula-Based IMU Calibration
        self.angle_offset1 = 0.0  # IMU 1 Pitch Offset
        self.angle_offset2 = 0.0  # IMU 1 Roll Offset
        self.angle_offset3 = 0.0  # IMU 2 Roll Offset (relative to IMU1)
        self.angle_offset4 = 0.0  # IMU 3 Roll Offset (relative to IMU1+IMU2)
        # Legacy offsets (kept for backward compatibility, not used in new formula-based method)
        self.angle_offset5 = 0.0
        self.angle_offset6 = 0.0
        
        # Step tracking
        self.current_step = 1
        
        # Mars device ID tracking
        self.current_mars_id = ""
        
        # Initialize user data management
        self.user_data = UserDataManager()
        
        # Initialize logger with proper user data path
        self.logger = Logger(str(self.user_data.get_log_file_path()))
        self.logger.log_step("Application started")
        
        # Initialize Arduino manager
        self.arduino_manager = ArduinoManager(str(self.user_data.get_directory('root')))
        
        # Setup Arduino sketches (copy from bundle if needed)
        sketches_dir = self.user_data.copy_arduino_sketches()
        
        # Arduino sketch file paths
        self.unified_calibration_file = str(sketches_dir / "calibration" / "calibration.ino")  # Unified calibration program
        self.firmware_file = str(sketches_dir / "marsfire" / "marsfire.ino")  # Production firmware
        self.firmware_v2_dir = str(sketches_dir / "marsfire")  # Directory containing all marsfire files (variable.h, etc.)
        self.calibrations_dir = str(self.user_data.get_directory('calibrations'))

        # Show setup dialog on first run
        self.show_setup_dialog_if_needed()

        self.logger.log(f"Unified calibration file: {self.unified_calibration_file}")
        self.logger.log(f"Production firmware file: {self.firmware_file}")
        self.logger.log(f"Marsfire directory: {self.firmware_v2_dir}")
        self.logger.log(f"Calibrations storage: {self.calibrations_dir}")
        
        # Connect signals to methods
        self.log_signal.connect(self.log_message_to_ui)
        self.step_update_signal.connect(self.handle_step_update)
        
        # Setup UI
        self.setup_ui()
        self.refresh_ports()
        self.update_step_status()
        
        # Load saved Mars ID
        self.load_saved_mars_id()
        
        # Initialize update checking
        self.update_checker = None
        self.update_dialog = None
        
        # Check for updates on startup (after a short delay)
        QTimer.singleShot(3000, self.check_for_updates)
        
        # Timer for periodic updates
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_display)
    
    def show_setup_dialog_if_needed(self):
        """Show setup dialog if Arduino CLI is not available"""
        if not self.arduino_manager.is_arduino_cli_installed():
            self.logger.log("Arduino CLI not found, showing setup dialog")
            
            dialog = SetupDialog(self.arduino_manager, self)
            result = dialog.exec()
            
            if result == QDialog.Rejected:
                self.logger.log("Setup was cancelled or failed")
                QMessageBox.warning(
                    self, 
                    "Setup Incomplete", 
                    "Arduino CLI setup was not completed. Some features may not work properly.\n\n"
                    "You can manually install Arduino CLI and required libraries, or restart the application to try setup again."
                )
        else:
            self.logger.log("Arduino CLI found, skipping setup dialog")
        
    def handle_step_update(self, step, message):
        """Handle step updates from background threads"""
        self.current_step = step
        self.update_step_status()
        if message:
            ui_message = self.logger.log_step(message)
            self.log_message_to_ui(ui_message)
        
    def setup_ui(self):
        """Setup the user interface with tabs"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        
        # Title
        title_label = QLabel("Load Cell & IMU Calibration Wizard")
        title_label.setFont(QFont("Arial", 18, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("QLabel { color: #2196F3; margin: 10px; }")
        main_layout.addWidget(title_label)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # Create tabs
        setup_load_cell_tab(self)
        setup_imu_tab(self)
        setup_upload_firmware_tab(self)
        
    def update_step_status(self):
        """Update the visual status of steps"""
        # Reset all steps
        self.step1.set_current(False)
        self.step1.set_completed(False)
        self.step2.set_current(False)
        self.step2.set_completed(False)
        
        # Enable/disable groups
        self.step1_group.setEnabled(True)
        self.step2_group.setEnabled(False)
        self.calibration_status_group.setEnabled(True)
        
        if self.current_step == 1:
            self.step1.set_current(True)
            self.step1_group.setEnabled(True)
        elif self.current_step == 2:
            self.step1.set_completed(True)
            self.step2.set_current(True)
            self.step2_group.setEnabled(True)
        elif self.current_step >= 3:  # All completed
            self.step1.set_completed(True)
            self.step2.set_completed(True)
    
    # Mars ID Management Methods
    def set_mars_id(self, mars_id):
        """Set Mars ID and sync across all tabs"""
        self.current_mars_id = mars_id
        self.sync_mars_id_to_all_tabs()
        self.save_mars_id()
        self.logger.log(f"Mars ID set to: {mars_id}")
    
    def sync_mars_id_to_all_tabs(self):
        """Synchronize Mars ID across all tabs"""
        # Update Load Cell tab Mars ID field
        if hasattr(self, 'mars_id_input'):
            self.mars_id_input.blockSignals(True)
            self.mars_id_input.setText(self.current_mars_id)
            self.mars_id_input.blockSignals(False)
        
        # Update IMU tab Mars ID field  
        if hasattr(self, 'imu_mars_id_input'):
            self.imu_mars_id_input.blockSignals(True)
            self.imu_mars_id_input.setText(self.current_mars_id)
            self.imu_mars_id_input.blockSignals(False)
            
        # Update Firmware Upload tab Mars ID display
        if hasattr(self, 'firmware_mars_id_label'):
            display_text = self.current_mars_id if self.current_mars_id else "Not Set"
            self.firmware_mars_id_label.setText(display_text)
            
        # Update window title with Mars ID
        if self.current_mars_id:
            base_title = f"Mars Calibration v{self.current_version}"
            self.setWindowTitle(f"{base_title} - Mars ID: {self.current_mars_id}")
        else:
            self.setWindowTitle(f"Mars Calibration v{self.current_version} - Load Cell & IMU Calibration System")
    
    def validate_mars_id(self, mars_id):
        """Validate Mars ID format - must be a non-negative integer"""
        if not mars_id:
            return False, "Mars ID cannot be empty"
        
        try:
            mars_id_int = int(mars_id)
            if mars_id_int < 0:
                return False, "Mars ID must be a non-negative integer (0 or greater)"
            if mars_id_int > 9999:
                return False, "Mars ID must be 9999 or less"
            return True, ""
        except ValueError:
            return False, "Mars ID must be a valid integer"
    
    def get_mars_filename_prefix(self):
        """Get filename prefix with Mars ID"""
        if self.current_mars_id:
            # Format as zero-padded 4-digit number for better sorting
            try:
                mars_id_int = int(self.current_mars_id)
                return f"Mars_{mars_id_int:04d}_"
            except ValueError:
                return f"Mars_{self.current_mars_id}_"
        return "Mars_Unknown_"
    
    def save_mars_id(self):
        """Save Mars ID to persistent storage"""
        try:
            mars_id_file = self.user_data.get_directory('root') / 'mars_id.txt'
            with open(mars_id_file, 'w') as f:
                f.write(self.current_mars_id)
        except Exception as e:
            self.logger.log_error(f"Failed to save Mars ID: {str(e)}")
    
    def load_saved_mars_id(self):
        """Load previously saved Mars ID"""
        try:
            mars_id_file = self.user_data.get_directory('root') / 'mars_id.txt'
            if mars_id_file.exists():
                with open(mars_id_file, 'r') as f:
                    saved_mars_id = f.read().strip()
                if saved_mars_id:
                    self.current_mars_id = saved_mars_id
                    self.sync_mars_id_to_all_tabs()
                    self.logger.log(f"Loaded saved Mars ID: {saved_mars_id}")
        except Exception as e:
            self.logger.log_error(f"Failed to load saved Mars ID: {str(e)}")
    
    # Load Cell Methods
    def upload_calibration_code(self):
        """Upload unified calibration Arduino code"""
        self.logger.log_upload("Starting unified calibration code upload")
        
        if not os.path.exists(self.unified_calibration_file):
            error_msg = f"Unified calibration file not found: {self.unified_calibration_file}"
            self.logger.log_error(error_msg)
            QMessageBox.warning(self, "Warning", error_msg)
            return
            
        if not self.port_combo.currentText():
            error_msg = "No port selected for upload"
            self.logger.log_error(error_msg)
            QMessageBox.warning(self, "Warning", "Please select a port first!")
            return
            
        # Disconnect serial if connected
        if self.is_connected:
            ui_message = self.logger.log("Disconnecting serial for upload")
            self.log_message_to_ui(ui_message)
            self.disconnect_serial()
            time.sleep(1)
            
        # Show progress bar
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.upload_cal_button.setEnabled(False)
        
        # Capture current selections
        selected_port = self.port_combo.currentText()
        selected_board = self.board_combo.currentText()
        
        self.logger.log_upload(f"Upload parameters - Port: {selected_port}, Board: {selected_board}")
        ui_message = self.logger.log_upload(f"Starting unified calibration upload to {selected_port}")
        self.log_message_to_ui(ui_message)
        
        # Run upload in separate thread
        threading.Thread(target=self._upload_thread, args=(self.unified_calibration_file, selected_board, selected_port, "unified_calibration"), daemon=True).start()
        
    def upload_firmware_code(self):
        """Upload firmware Arduino code"""
        self.logger.log_upload("Starting firmware code upload")
        
        if not os.path.exists(self.firmware_file):
            error_msg = f"Firmware file not found: {self.firmware_file}"
            self.logger.log_error(error_msg)
            QMessageBox.warning(self, "Warning", error_msg)
            return
            
        if not self.port_combo.currentText():
            error_msg = "No port selected for firmware upload"
            self.logger.log_error(error_msg)
            QMessageBox.warning(self, "Warning", "Please select a port first!")
            return
            
        # Disconnect serial if connected
        if self.is_connected:
            ui_message = self.logger.log("Disconnecting serial for firmware upload")
            self.log_message_to_ui(ui_message)
            self.disconnect_serial()
            time.sleep(1)
            
        # Show progress bar
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.upload_firmware_button.setEnabled(False)
        
        # Capture current selections
        selected_port = self.port_combo.currentText()
        selected_board = self.board_combo.currentText()
        
        self.logger.log_upload(f"Firmware upload parameters - Port: {selected_port}, Board: {selected_board}")
        ui_message = self.logger.log_upload(f"Starting firmware upload to {selected_port}")
        self.log_message_to_ui(ui_message)
        
        # Run upload in separate thread
        threading.Thread(target=self._upload_thread, args=(self.firmware_file, selected_board, selected_port, "firmware"), daemon=True).start()
        
    def update_firmware_code(self):
        """Update firmware.ino file with current calibration factor"""
        self.logger.log_calibration("Starting firmware update with calibration factor")
        
        if not os.path.exists(self.firmware_file):
            error_msg = f"Firmware file not found: {self.firmware_file}"
            self.logger.log_error(error_msg)
            QMessageBox.warning(self, "Warning", error_msg)
            return
            
        if self.current_calibration_factor == 1.0:
            error_msg = "No calibration factor available for firmware update"
            self.logger.log_error(error_msg)
            QMessageBox.warning(self, "Warning", "No calibration factor available. Please complete calibration first!")
            return
            
        try:
            self.logger.log(f"Reading firmware file: {self.firmware_file}")
            
            # Read the original firmware file
            with open(self.firmware_file, 'r') as file:
                content = file.read()
            
            # Update the calibration factor line
            pattern = r'float calibration_factor\s*=\s*[\d\.-]+;'
            replacement = f'float calibration_factor = {self.current_calibration_factor:.2f}; // Mars ID: {self.current_mars_id}'
            
            updated_content = re.sub(pattern, replacement, content)
            
            # Also try to update Mars ID comment if it exists, otherwise add it
            mars_id_pattern = r'// Mars ID:.*'
            if re.search(mars_id_pattern, updated_content):
                updated_content = re.sub(mars_id_pattern, f'// Mars ID: {self.current_mars_id}', updated_content)
            else:
                # Add Mars ID comment at the top after any existing header comments
                lines = updated_content.split('\n')
                insert_index = 0
                for i, line in enumerate(lines):
                    if not line.strip().startswith('//') and not line.strip().startswith('/*') and line.strip():
                        insert_index = i
                        break
                lines.insert(insert_index, f'// Mars ID: {self.current_mars_id}')
                updated_content = '\n'.join(lines)
            
            # Check if replacement was made
            if 'calibration_factor' in content:
                # Create backup with Mars ID
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                mars_prefix = self.get_mars_filename_prefix()
                backup_filename = f"{mars_prefix}firmware_backup_{timestamp}.ino"
                backup_path = os.path.join(os.path.dirname(self.firmware_file), backup_filename)
                with open(backup_path, 'w') as backup_file:
                    backup_file.write(content)
                
                # Write updated content
                with open(self.firmware_file, 'w') as file:
                    file.write(updated_content)
                
                success_msg = f"Updated firmware with calibration factor: {self.current_calibration_factor:.2f}"
                backup_msg = f"Backup saved as: {backup_path}"
                
                self.logger.log_success(success_msg)
                self.logger.log(backup_msg)
                
                ui_message1 = self.logger.log_calibration(success_msg)
                ui_message2 = self.logger.log(backup_msg)
                
                self.log_message_to_ui(ui_message1)
                self.log_message_to_ui(ui_message2)
                
                self.upload_firmware_button.setEnabled(True)
                
                QMessageBox.information(self, "Success", 
                    f"Firmware updated with calibration factor: {self.current_calibration_factor:.2f}")
            else:
                error_msg = "Could not find calibration_factor line in firmware file"
                self.logger.log_error(error_msg)
                QMessageBox.warning(self, "Warning", error_msg + "!")
                
        except Exception as e:
            error_msg = f"Failed to update firmware file: {str(e)}"
            self.logger.log_error(error_msg)
            QMessageBox.critical(self, "Error", error_msg)
            ui_message = self.logger.log_error(error_msg)
            self.log_message_to_ui(ui_message)
            
    def _upload_thread(self, sketch_path, board, port, upload_type):
        """Upload thread function"""
        try:
            self.log_signal.emit(self.logger.log_upload(f"{upload_type.title()} Upload parameters:"))
            self.log_signal.emit(self.logger.log_upload(f"  File: {sketch_path}"))
            self.log_signal.emit(self.logger.log_upload(f"  Board: {board}"))
            self.log_signal.emit(self.logger.log_upload(f"  Port: {port}"))
            
            # Use local arduino-cli.exe
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            arduino_cli_path = os.path.join(base_path, "arduino-cli.exe")
            
            # Check if local arduino-cli.exe exists
            if not os.path.exists(arduino_cli_path):
                self.log_signal.emit(self.logger.log_error("arduino-cli.exe not found in program directory!"))
                # Emit signal to show download dialog (must be done from main thread)
                self.log_signal.emit(self.logger.log_error("Checking for Arduino CLI download option..."))
                # Call main thread to show dialog
                from PySide6.QtCore import QTimer
                QTimer.singleShot(0, lambda: self.show_arduino_cli_download_dialog())
                return
            
            # Install required cores if needed
            if "mbed_nano" in board:
                self.log_signal.emit(self.logger.log_upload("Checking Arduino Nano core installation..."))
                self.log_signal.emit(self.logger.log_upload("This may take several minutes on first run - please wait..."))
                core_install_cmd = f'"{arduino_cli_path}" core install arduino:mbed_nano'
                try:
                    result = subprocess.run(core_install_cmd, shell=True, capture_output=True, text=True, timeout=300)  # 5 minute timeout
                    if result.returncode == 0:
                        self.log_signal.emit(self.logger.log_upload("Arduino Nano core installation check complete"))
                    else:
                        self.log_signal.emit(self.logger.log_warning(f"Arduino Nano core install result: {result.stderr}"))
                except subprocess.TimeoutExpired:
                    self.log_signal.emit(self.logger.log_error("Core installation timed out after 5 minutes. Please check your internet connection and try again."))
            elif "teensy" in board:
                self.log_signal.emit(self.logger.log_upload("Checking Teensy core installation..."))
                self.log_signal.emit(self.logger.log_upload("This may take several minutes on first run - please wait..."))
                core_install_cmd = f'"{arduino_cli_path}" core install teensy:avr'
                try:
                    result = subprocess.run(core_install_cmd, shell=True, capture_output=True, text=True, timeout=300)  # 5 minute timeout
                    if result.returncode == 0:
                        self.log_signal.emit(self.logger.log_upload("Teensy core installation check complete"))
                    else:
                        self.log_signal.emit(self.logger.log_warning(f"Teensy core install result: {result.stderr}"))
                        # Try alternative Teensy installation
                        self.log_signal.emit(self.logger.log_upload("Trying alternative Teensy core installation..."))
                        alt_core_cmd = f'"{arduino_cli_path}" core install arduino:teensy'
                        alt_result = subprocess.run(alt_core_cmd, shell=True, capture_output=True, text=True, timeout=300)
                        if alt_result.returncode == 0:
                            self.log_signal.emit(self.logger.log_success("Alternative Teensy core installation successful"))
                        else:
                            self.log_signal.emit(self.logger.log_error("Teensy core installation failed. Please install Teensyduino manually."))
                except subprocess.TimeoutExpired:
                    self.log_signal.emit(self.logger.log_error("Core installation timed out after 5 minutes. Please check your internet connection and try again."))
            
            # Compile command
            compile_cmd = f'"{arduino_cli_path}" compile --fqbn {board} "{sketch_path}"'
            
            # Upload command
            upload_cmd = f'"{arduino_cli_path}" upload -p {port} --fqbn {board} "{sketch_path}"'
            
            # Execute commands
            self.log_signal.emit(self.logger.log_upload(f"Compiling {upload_type} sketch..."))
            try:
                result = subprocess.run(compile_cmd, shell=True, capture_output=True, text=True, timeout=120)  # 2 minute timeout
                
                if result.returncode == 0:
                    self.log_signal.emit(self.logger.log_success(f"{upload_type.title()} compilation successful!"))
                    self.log_signal.emit(self.logger.log_upload(f"Uploading {upload_type} to {port}..."))
                    
                    result = subprocess.run(upload_cmd, shell=True, capture_output=True, text=True, timeout=60)  # 1 minute timeout
                    
                    if result.returncode == 0:
                        self.log_signal.emit(self.logger.log_success(f"{upload_type.title()} upload successful!"))

                        # Update step progress using signal (only for Load Cell tab, not IMU tab)
                        if upload_type in ["calibration", "unified_calibration"]:
                            self.step_update_signal.emit(2, "✓ Step 1 completed! Now connect to serial and calibrate.")
                        elif upload_type == "firmware":
                            self.step_update_signal.emit(4, "✓ All steps completed! Load cell is ready to use.")
                        # Note: unified_calibration_imu upload doesn't trigger step updates (IMU tab has no steps)
                        
                    else:
                        self.log_signal.emit(self.logger.log_error(f"{upload_type.title()} upload failed: {result.stderr}"))
                        if "mbed_nano" in board:
                            self.log_signal.emit(self.logger.log_warning("Note: Make sure to double-press the reset button on Nano 33 BLE to enter bootloader mode"))
                        elif "teensy" in board:
                            self.log_signal.emit(self.logger.log_warning("Note: Make sure Teensy is in programming mode. Press the program button on Teensy if needed"))
                            self.log_signal.emit(self.logger.log_warning("Tip: Try using Teensy Loader application if upload continues to fail"))
                else:
                    self.log_signal.emit(self.logger.log_error(f"{upload_type.title()} compilation failed: {result.stderr}"))
                    
            except subprocess.TimeoutExpired:
                self.log_signal.emit(self.logger.log_error(f"{upload_type.title()} operation timed out. Please check connections and try again."))
                
        except Exception as e:
            self.log_signal.emit(self.logger.log_error(f"{upload_type.title()} upload error: {str(e)}"))
        finally:
            # Hide progress bar and re-enable button
            self.progress_bar.setVisible(False)
            if upload_type in ["calibration", "unified_calibration"]:
                self.upload_cal_button.setEnabled(True)
            elif upload_type in ["IMU", "unified_calibration_imu"]:
                self.upload_imu_button.setEnabled(True)
            else:
                self.upload_firmware_button.setEnabled(True)

    def show_arduino_cli_download_dialog(self):
        """Show dialog asking user to download Arduino CLI"""
        import webbrowser

        reply = QMessageBox.question(
            self,
            "Arduino CLI Not Found",
            "Arduino CLI (arduino-cli.exe) is required for uploading firmware.\n\n"
            "Would you like to download it now?\n\n"
            "Click 'Yes' to open the download page in your browser, or "
            "'No' to close this dialog.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )

        if reply == QMessageBox.Yes:
            # Open Arduino CLI download page
            self.logger.log("Opening Arduino CLI download page...")
            webbrowser.open("https://github.com/arduino/arduino-cli/releases")

            # Show instructions dialog
            QMessageBox.information(
                self,
                "Arduino CLI Download",
                "A browser window has opened to the Arduino CLI download page.\n\n"
                "INSTRUCTIONS:\n"
                "1. Download the Windows version (arduino-cli_Windows_64bit.zip)\n"
                "2. Extract the ZIP file\n"
                "3. Copy 'arduino-cli.exe' to the same folder as this application\n"
                "4. Restart this application and try uploading again\n\n"
                f"Application folder: {os.path.dirname(os.path.dirname(os.path.abspath(__file__)))}"
            )
        else:
            self.logger.log("User declined Arduino CLI download")

    def refresh_ports(self):
        """Refresh available serial ports"""
        self.logger.log("Refreshing serial ports")
        self.port_combo.clear()
        if hasattr(self, 'imu_port_combo'):
            self.imu_port_combo.clear()
        ports = serial.tools.list_ports.comports()
        
        # Add debug information
        ports_msg = f"Found {len(ports)} serial ports"
        ui_message = self.logger.log(ports_msg)
        self.log_message_to_ui(ui_message)
        
        teensy_ports = []
        other_ports = []
        
        for port in ports:
            port_info = f"{port.device}"
            if port.description:
                port_info += f" - {port.description}"
            if port.manufacturer:
                port_info += f" ({port.manufacturer})"
            
            # Check if this is a Teensy device
            is_teensy = False
            if port.description and any(keyword in port.description.lower() for keyword in ['teensy', 'pjrc']):
                is_teensy = True
                teensy_ports.append(port)
            elif port.manufacturer and 'pjrc' in port.manufacturer.lower():
                is_teensy = True
                teensy_ports.append(port)
            elif port.vid == 0x16C0 and port.pid in [0x0483, 0x0486, 0x04D0, 0x04D1]:  # Common Teensy VID/PIDs
                is_teensy = True
                teensy_ports.append(port)
            else:
                other_ports.append(port)
            
            self.port_combo.addItem(port.device)
            if hasattr(self, 'imu_port_combo'):
                self.imu_port_combo.addItem(port.device)
            
            if is_teensy:
                port_log = f"  {port_info} [TEENSY DETECTED]"
                ui_message = self.logger.log_success(port_log)
            else:
                port_log = f"  {port_info}"
                ui_message = self.logger.log(port_log)
            self.log_message_to_ui(ui_message)
        
        # Auto-select first port for Arduino Nano 33 BLE if available, otherwise Teensy
        nano_ports = [p for p in ports if p.description and 'nano 33 ble' in p.description.lower()]
        
        if nano_ports:
            selected_port = nano_ports[0].device
            self.port_combo.setCurrentText(selected_port)
            if hasattr(self, 'imu_port_combo'):
                self.imu_port_combo.setCurrentText(selected_port)
            ui_message = self.logger.log_success(f"Auto-selected Nano 33 BLE port: {selected_port}")
            self.log_message_to_ui(ui_message)
        elif teensy_ports:
            selected_port = teensy_ports[0].device
            self.port_combo.setCurrentText(selected_port)
            if hasattr(self, 'imu_port_combo'):
                self.imu_port_combo.setCurrentText(selected_port)
            ui_message = self.logger.log_success(f"Auto-selected Teensy port: {selected_port}")
            self.log_message_to_ui(ui_message)
        # Otherwise auto-select COM10 if available
        elif any(port.device == "COM10" for port in other_ports):
            self.port_combo.setCurrentText("COM10")
            if hasattr(self, 'imu_port_combo'):
                self.imu_port_combo.setCurrentText("COM10")
            ui_message = self.logger.log("Auto-selected COM10")
            self.log_message_to_ui(ui_message)
        
        if len(ports) == 0:
            ui_message = self.logger.log_warning("No serial ports detected!")
            self.log_message_to_ui(ui_message)
        elif len(teensy_ports) == 0:
            ui_message = self.logger.log_warning("No Teensy devices detected. Make sure Teensy is connected and drivers are installed.")
            self.log_message_to_ui(ui_message)
            
    def toggle_connection(self):
        """Connect or disconnect from serial port"""
        if not self.is_connected:
            self.connect_serial()
        else:
            self.disconnect_serial()
            
    def connect_serial(self):
        """Connect to serial port"""
        if not self.port_combo.currentText():
            error_msg = "No port selected for serial connection"
            self.logger.log_error(error_msg)
            QMessageBox.warning(self, "Warning", "Please select a port!")
            return
            
        selected_port = self.port_combo.currentText()
        baudrate = self.baudrate_spin.value()
        
        self.logger.log_serial(f"Attempting connection to {selected_port} at {baudrate} baud", "CONNECT")
            
        try:
            # Create worker thread
            self.serial_thread = QThread()
            self.serial_worker = SerialWorker(selected_port, baudrate)
            self.serial_worker.moveToThread(self.serial_thread)
            
            # Connect signals
            self.serial_worker.data_received.connect(self.handle_serial_data)
            self.serial_worker.connection_lost.connect(self.handle_connection_lost)
            self.serial_thread.started.connect(self.serial_worker.start_connection)
            
            # Start thread
            self.serial_thread.start()
            
            # Update UI
            self.is_connected = True
            self.connect_button.setText("Disconnect from Serial")
            self.connect_button.setStyleSheet("QPushButton { background: #f44336; color: white; }")
            self.tare_button.setEnabled(True)
            self.calibrate_button.setEnabled(True)
            self.send_mass_button.setEnabled(True)
            
            success_msg = f"Connected to {selected_port}"
            ui_message = self.logger.log_success(success_msg)
            self.log_message_to_ui(ui_message)
            
        except Exception as e:
            error_msg = f"Connection failed: {str(e)}"
            self.logger.log_error(error_msg)
            QMessageBox.critical(self, "Error", error_msg)
            
    def disconnect_serial(self):
        """Disconnect from serial port"""
        self.logger.log_serial("Disconnecting from serial port", "DISCONNECT")
        
        if self.serial_worker:
            self.serial_worker.stop_connection()
        if self.serial_thread:
            self.serial_thread.quit()
            self.serial_thread.wait()
            
        self.is_connected = False
        self.connect_button.setText("Connect to Serial")
        self.connect_button.setStyleSheet("")
        self.tare_button.setEnabled(False)
        self.calibrate_button.setEnabled(False)
        self.send_mass_button.setEnabled(False)
        
        ui_message = self.logger.log("Disconnected from serial")
        self.log_message_to_ui(ui_message)
        
    def handle_serial_data(self, data):
        """Handle incoming serial data"""
        ui_message = self.logger.log_serial(data, "RX")
        self.log_message_to_ui(f"Arduino: {data}")
        
        # Check for calibration factor in the data
        if "calibration value has been set to:" in data.lower():
            try:
                # Extract calibration factor
                parts = data.split(":")
                if len(parts) > 1:
                    cal_factor = float(parts[1].split(",")[0].strip())
                    self.current_calibration_factor = cal_factor
                    self.cal_factor_label.setText(f"Calibration Factor: {cal_factor:.2f}")
                    self.cal_factor_label.setStyleSheet("QLabel { background: #d4edda; padding: 10px; border: 1px solid #c3e6cb; color: #155724; }")
                    
                    # Log calibration success
                    cal_msg = f"Calibration factor received: {cal_factor:.2f}"
                    self.logger.log_calibration(cal_msg)
                    
                    step_msg = f"✓ Step 2 completed! Calibration factor: {cal_factor:.2f}"
                    ui_message = self.logger.log_step(step_msg)
                    self.log_message_to_ui(ui_message)
                    
                    # Update status and proceed to completed state
                    self.current_step = 3
                    self.update_step_status()
                    
                    # Update calibration status display
                    self.calibration_status_label.setText(f"✓ Load cell calibration saved successfully!\nCalibration Factor: {cal_factor:.2f}\n\nGo to 'Upload Firmware' tab to upload final firmware.")
                    self.calibration_status_label.setStyleSheet("""
                    QLabel { 
                        background: #e8f5e8; 
                        color: #2e7d32; 
                        padding: 15px; 
                        border: 2px solid #4caf50; 
                        border-radius: 8px;
                        font-weight: bold;
                        font-size: 11pt;
                    }
                    """)
                    
                    QMessageBox.information(self, "Calibration Saved", 
                        f"Calibration saved successfully!\nCalibration Factor: {cal_factor:.2f}\n\nYou can now go to the 'Upload Firmware' tab.")
            except:
                pass
                
    def handle_connection_lost(self):
        """Handle lost connection"""
        self.logger.log_error("Serial connection lost")
        self.disconnect_serial()
        QMessageBox.warning(self, "Warning", "Connection lost!")
        
    def send_tare(self):
        """Send tare command"""
        if self.serial_worker:
            self.serial_worker.send_data("t")
            ui_message = self.logger.log_serial("t", "TX")
            self.log_message_to_ui("Sent: t (tare)")
            
    def start_calibration(self):
        """Start calibration process"""
        if self.serial_worker:
            self.serial_worker.send_data("r")
            ui_message = self.logger.log_serial("r", "TX")
            self.log_message_to_ui("Sent: r (start calibration)")
            
    def send_known_mass(self):
        """Send known mass value"""
        if self.serial_worker:
            mass = self.known_mass_spin.value()
            self.serial_worker.send_data(f"{mass}\n")
            ui_message = self.logger.log_serial(f"{mass}", "TX")
            self.log_message_to_ui(f"Sent: {mass} (known mass)")
            
    def log_message_to_ui(self, message):
        """Add message to serial output (UI only)"""
        self.serial_output.append(message)
        
        # Auto-scroll to bottom
        cursor = self.serial_output.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.serial_output.setTextCursor(cursor)
        
    def clear_serial_output(self):
        """Clear serial output"""
        self.logger.log("Serial output cleared by user")
        self.serial_output.clear()
        
    def update_display(self):
        """Update display periodically"""
        pass
    
    # Update Management Methods
    def check_for_updates(self):
        """Check for application updates in background."""
        try:
            self.logger.log("Checking for application updates...")
            
            # Create and start update checker thread
            self.update_checker = UpdateChecker(self.current_version)
            self.update_checker.update_available.connect(self.show_update_dialog)
            self.update_checker.check_completed.connect(self.update_check_completed)
            self.update_checker.start()
            
        except Exception as e:
            self.logger.log_error(f"Update check failed: {str(e)}")
    
    def show_update_dialog(self, update_info):
        """Show update notification dialog."""
        try:
            self.logger.log(f"Update available: v{update_info['version']}")
            
            # Create and show update dialog
            self.update_dialog = UpdateNotificationDialog(
                update_info, 
                self.current_version, 
                self
            )
            self.update_dialog.show()
            
        except Exception as e:
            self.logger.log_error(f"Failed to show update dialog: {str(e)}")
    
    def update_check_completed(self):
        """Handle update check completion."""
        self.logger.log("Update check completed")
        
        # Clean up update checker
        if self.update_checker:
            self.update_checker.deleteLater()
            self.update_checker = None
    
    # IMU Methods
    def upload_imu_code(self):
        """Upload unified calibration Arduino code (same as load cell)"""
        self.logger.log_imu("Starting unified calibration code upload for IMU")
        
        if not os.path.exists(self.unified_calibration_file):
            error_msg = f"Unified calibration file not found: {self.unified_calibration_file}"
            self.logger.log_error(error_msg)
            QMessageBox.warning(self, "Warning", error_msg)
            return
            
        if not self.imu_port_combo.currentText():
            error_msg = "No port selected for IMU upload"
            self.logger.log_error(error_msg)
            QMessageBox.warning(self, "Warning", "Please select a port first!")
            return
            
        # Disconnect IMU serial if connected
        if self.is_imu_connected:
            ui_message = self.logger.log("Disconnecting IMU for upload")
            self.log_imu_message_to_ui(ui_message)
            self.disconnect_imu_serial()
            time.sleep(1)
            
        # Show progress bar
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.upload_imu_button.setEnabled(False)
        
        # Capture current selections
        selected_port = self.imu_port_combo.currentText()
        selected_board = self.imu_board_combo.currentText()
        
        self.logger.log_imu(f"IMU upload parameters - Port: {selected_port}, Board: {selected_board}")
        ui_message = self.logger.log_imu(f"Starting unified calibration upload to {selected_port}")
        self.log_imu_message_to_ui(ui_message)
        
        # Handle auto-detect board
        if selected_board == "auto-detect":
            detected_board = self.detect_board_on_port(selected_port)
            if detected_board:
                selected_board = detected_board
                self.log_imu_message_to_ui(f"Auto-detected board: {selected_board}")
            else:
                self.log_imu_message_to_ui("Auto-detection failed, using default: arduino:mbed_nano:nano33ble")
                selected_board = "arduino:mbed_nano:nano33ble"
        
        # Run upload in separate thread
        threading.Thread(target=self._upload_thread, args=(self.unified_calibration_file, selected_board, selected_port, "unified_calibration_imu"), daemon=True).start()
    
    def detect_board_on_port(self, port):
        """Auto-detect board type on specified port"""
        try:
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            arduino_cli_path = os.path.join(base_path, "arduino-cli.exe")
            
            # Run board list command and parse output
            result = subprocess.run(f'"{arduino_cli_path}" board list', shell=True, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines[1:]:  # Skip header
                    parts = line.split()
                    if len(parts) >= 4 and parts[0] == port:
                        # Found the port, check if FQBN is available
                        if len(parts) >= 5:
                            return parts[4]  # Return the FQBN
                        break
            
            return None
            
        except Exception as e:
            self.logger.log_error(f"Board detection error: {str(e)}")
            return None
        
    def toggle_imu_connection(self):
        """Connect or disconnect from IMU port"""
        if not self.is_imu_connected:
            self.connect_imu_serial()
        else:
            self.disconnect_imu_serial()
            
    def connect_imu_serial(self):
        """Connect to IMU port"""
        if not self.imu_port_combo.currentText():
            error_msg = "No port selected for IMU connection"
            self.logger.log_error(error_msg)
            QMessageBox.warning(self, "Warning", "Please select a port!")
            return
            
        selected_port = self.imu_port_combo.currentText()
        baudrate = 115200  # IMU uses fixed 115200 baud
        
        self.logger.log_imu(f"Attempting IMU connection to {selected_port} at {baudrate} baud")
            
        try:
            # Create IMU worker thread
            self.imu_thread = QThread()
            self.imu_worker = IMUDataWorker(selected_port, baudrate)
            self.imu_worker.moveToThread(self.imu_thread)
            
            # Connect signals
            self.imu_worker.data_received.connect(self.handle_imu_data)
            self.imu_worker.connection_lost.connect(self.handle_imu_connection_lost)
            self.imu_thread.started.connect(self.imu_worker.start_connection)
            
            # Start thread
            self.imu_thread.start()
            
            # Update UI
            self.is_imu_connected = True
            self.imu_connect_button.setText("Disconnect IMU")
            self.imu_connect_button.setStyleSheet("QPushButton { background: #f44336; color: white; }")
            self.start_imu_cal_button.setEnabled(True)
            
            success_msg = f"Connected to IMU at {selected_port}"
            ui_message = self.logger.log_success(success_msg)
            self.log_imu_message_to_ui(ui_message)
            
        except Exception as e:
            error_msg = f"IMU connection failed: {str(e)}"
            self.logger.log_error(error_msg)
            QMessageBox.critical(self, "Error", error_msg)
            
    def disconnect_imu_serial(self):
        """Disconnect from IMU port"""
        self.logger.log_imu("Disconnecting from IMU port")
        
        if self.imu_worker:
            self.imu_worker.stop_connection()
        if self.imu_thread:
            self.imu_thread.quit()
            self.imu_thread.wait()
            
        self.is_imu_connected = False
        self.imu_calibration_started = False  # Reset calibration state
        self.imu_connect_button.setText("Connect to IMU")
        self.imu_connect_button.setStyleSheet("")
        self.start_imu_cal_button.setEnabled(False)
        
        ui_message = self.logger.log("Disconnected from IMU")
        self.log_imu_message_to_ui(ui_message)
        
    def handle_imu_data(self, data):
        """Handle incoming IMU data"""
        if "error" in data:
            ui_message = self.logger.log_error(data["error"])
            self.log_imu_message_to_ui(ui_message)
        elif "raw_message" in data:
            ui_message = self.logger.log_imu(data["raw_message"])
            self.log_imu_message_to_ui(f"Arduino: {data['raw_message']}")
        else:
            # Update current IMU data
            self.current_imu_data = data
            
            # Update visualizations
            self.update_imu_visualizations(data)
            
            # Update offsets display
            self.update_offsets_display(data)
            
    def update_imu_visualizations(self, data):
        """Update IMU visualization widgets"""
        try:
            # Update angle indicators
            self.roll_indicator.set_angle(data['roll'])
            self.pitch_indicator.set_angle(data['pitch'])
            self.yaw_indicator.set_angle(data['yaw'])
            
            # Update attitude indicator
            self.attitude_indicator.set_attitude(data['pitch'], data['roll'])
            
            # Update LCD displays
            self.ax_lcd.display(f"{data['ax']:.3f}")
            self.ay_lcd.display(f"{data['ay']:.3f}")
            self.az_lcd.display(f"{data['az']:.3f}")
            
        except KeyError as e:
            self.logger.log_error(f"Missing IMU data field: {e}")
            
    def update_offsets_display(self, data):
        """Update offset display labels and store current offsets (4-offset formula-based - X/Y/Z offsets not displayed)"""
        try:
            # Store offset data for reference (not displayed in UI for 4-offset system)
            self.current_offset_x = data.get('offset_x', 0.0)
            self.current_offset_y = data.get('offset_y', 0.0)
            self.current_offset_z = data.get('offset_z', 0.0)

            # Note: X/Y/Z offset labels removed from UI for 4-offset formula-based system
            # The new system directly calculates pitch/roll offsets from accelerometer data

        except KeyError:
            pass
            
    def handle_imu_connection_lost(self):
        """Handle lost IMU connection"""
        self.logger.log_error("IMU connection lost")
        self.disconnect_imu_serial()
        QMessageBox.warning(self, "Warning", "IMU connection lost!")
        
    def start_imu_calibration(self):
        """Start IMU calibration process and auto-save when complete"""
        if self.imu_worker:
            self.imu_worker.send_data("c")
            self.imu_calibration_started = True
            self.start_imu_cal_button.setEnabled(False)  # Disable during calibration
            ui_message = self.logger.log_imu("Starting IMU calibration - place device flat and still")
            self.log_imu_message_to_ui("Sent: c (start IMU calibration)")
            
            # Set timer to auto-save after calibration completes (Arduino takes ~10 seconds)
            QTimer.singleShot(12000, self.auto_save_imu_calibration)
    
    def auto_save_imu_calibration(self):
        """Automatically save IMU calibration after completion (4-offset formula-based)"""
        if not self.current_imu_data:
            # Calibration may not be complete, try again in 2 seconds
            QTimer.singleShot(2000, self.auto_save_imu_calibration)
            return

        # Save the current IMU offsets using 4-offset formula-based method
        current_pitch = self.current_imu_data.get('pitch', 0.0)
        current_roll = self.current_imu_data.get('roll', 0.0)

        imu_names = ["IMU 1", "IMU 2", "IMU 3"]
        current_imu_name = imu_names[self.current_imu_index]

        if self.current_imu_index == 0:  # IMU 1 - saves PITCH + ROLL
            self.angle_offset1 = current_pitch
            self.angle_offset2 = current_roll
            self.angle_offset1_label.setText(f"{self.angle_offset1:.6f}")
            self.angle_offset2_label.setText(f"{self.angle_offset2:.6f}")

        elif self.current_imu_index == 1:  # IMU 2 - saves ROLL ONLY (relative to IMU1)
            # IMU2 only stores relative roll offset
            self.angle_offset3 = current_roll
            self.angle_offset3_label.setText(f"{self.angle_offset3:.6f}")

        elif self.current_imu_index == 2:  # IMU 3 - saves ROLL ONLY (relative to IMU1 and IMU2)
            # IMU3 only stores relative roll offset
            self.angle_offset4 = current_roll
            self.angle_offset4_label.setText(f"{self.angle_offset4:.6f}")

        # Re-enable the button and show success message
        self.start_imu_cal_button.setEnabled(True)
        ui_message = self.logger.log_imu(f"✓ {current_imu_name} calibration completed and saved automatically!")
        self.log_imu_message_to_ui(ui_message)

        # Update final firmware tab with all calibration values
        self.update_final_tab_status()
            
    def update_firmware_with_offsets(self):
        """Update variable.h in marsfire with 4 calculated IMU offsets"""
        try:
            # Read variable.h file from marsfire (with UTF-8 encoding to prevent Unicode errors)
            variable_h_file = os.path.join(self.firmware_v2_dir, 'variable.h')
            with open(variable_h_file, 'r', encoding='utf-8') as f:
                variable_content = f.read()

            # Update 4 IMU offset values in variable.h using #define format
            # Using the calculated offsets (angles_offset1-4)
            variable_content = self.update_define_in_firmware(variable_content, 'IMU1PITCHOFFSET', self.angle_offset1)
            variable_content = self.update_define_in_firmware(variable_content, 'IMU1ROLLOFFSET', self.angle_offset2)
            variable_content = self.update_define_in_firmware(variable_content, 'IMU2ROLLOFFSET', self.angle_offset3)
            variable_content = self.update_define_in_firmware(variable_content, 'IMU3ROLLOFFSET', self.angle_offset4)

            # Write updated variable.h file (with UTF-8 encoding to prevent Unicode errors)
            with open(variable_h_file, 'w', encoding='utf-8') as f:
                f.write(variable_content)

            # Enable upload button if it exists
            if hasattr(self, 'upload_firmware_button'):
                self.upload_firmware_button.setEnabled(True)

            ui_message = self.logger.log_imu(f"Updated marsfire with 4 calculated IMU offsets:")
            self.log_imu_message_to_ui(ui_message)
            self.log_imu_message_to_ui(f"  IMU1 Pitch: {self.angle_offset1:.6f} rad")
            self.log_imu_message_to_ui(f"  IMU1 Roll:  {self.angle_offset2:.6f} rad")
            self.log_imu_message_to_ui(f"  IMU2 Roll:  {self.angle_offset3:.6f} rad")
            self.log_imu_message_to_ui(f"  IMU3 Roll:  {self.angle_offset4:.6f} rad")
            QMessageBox.information(self, "Success", "Marsfire updated with 4 calculated IMU offsets!")

        except Exception as e:
            error_msg = f"Failed to update marsfire: {str(e)}"
            self.logger.log_error(error_msg)
            self.log_imu_message_to_ui(error_msg)
            QMessageBox.critical(self, "Error", error_msg)
    
    def update_offset_in_firmware(self, content, offset_name, offset_value):
        """Update a specific offset value in firmware content"""
        import re
        pattern = rf'(float\s+{offset_name}\s*=\s*)[^;]+;'
        replacement = rf'\g<1>{offset_value:.6f};'
        return re.sub(pattern, replacement, content)

    def update_define_in_firmware(self, content, define_name, define_value):
        """Update a specific #define value in firmware variable.h"""
        import re
        # Pattern matches: #define NAME value // comment
        pattern = rf'(#define\s+{define_name}\s+)[^\s/]+(\s*//.*)?$'
        replacement = rf'\g<1>{define_value:.6f}\g<2>'
        return re.sub(pattern, replacement, content, flags=re.MULTILINE)

    def calculate_imu_offsets_from_accel(self, ax1, ay1, az1, ax2, ay2, az2, ax3, ay3, az3):
        """
        Calculate 4 IMU offsets from raw accelerometer data using firmware formulas.

        Method: When device is placed flat and level during calibration, we apply
        the firmware angle calculation formulas with offset=0. The resulting angles
        ARE the offset values (since true angles should be 0 when flat).

        This matches the firmware formulas exactly:
        - IMU1 Pitch: atan2(ax1, sqrt(ay1^2 + az1^2))
        - IMU1 Roll:  atan2(-az1/cos(pitch1), ay1/cos(pitch1)) * -1
        - IMU2 Roll:  atan2(-az2/cos(pitch2), ay2/cos(pitch2)) * -1, adjusted for IMU1 roll
        - IMU3 Roll:  atan2(-ax3/cos(pitch3), ay3/cos(pitch3)) * -1, adjusted for IMU1&2 rolls

        Args: Raw accelerometer values from 3 IMUs
        Returns: tuple of 4 offsets (pitch1, roll1, roll2, roll3) in radians
        """
        import math

        # ===== IMU1 PITCH OFFSET =====
        # Formula: Theta1 = atan2(ax1, sqrt(ay1^2 + az1^2)) - IMU1PITCHOFFSET
        # When flat with offset=0: offset = atan2(ax1, sqrt(ay1^2 + az1^2))
        norm1 = math.sqrt(ay1**2 + az1**2)
        imu1_pitch_offset = math.atan2(ax1, norm1)

        # ===== IMU1 ROLL OFFSET =====
        # Formula: Theta2 = atan2(-az1/cos(Theta1), ay1/cos(Theta1)) * -1 - IMU1ROLLOFFSET
        # When flat with offset=0: offset = atan2(-az1/cos(Theta1), ay1/cos(Theta1)) * -1
        cos_pitch1 = math.cos(imu1_pitch_offset)
        if abs(cos_pitch1) > 0.001:  # Avoid division by zero
            imu1_roll_offset = math.atan2(-az1/cos_pitch1, ay1/cos_pitch1) * -1
        else:
            imu1_roll_offset = 0.0

        # ===== IMU2 ROLL OFFSET =====
        # Formula: Theta3 = atan2(-az2/cos(Theta2_calc), ay2/cos(Theta2_calc)) * -1 - IMU2ROLLOFFSET
        #          Theta3 -= Theta2  (subtract IMU1's roll)
        # Calculate pitch from IMU2 (note: we don't use its pitch in firmware, only roll)
        norm2 = math.sqrt(ay2**2 + az2**2)
        pitch2_calc = math.atan2(ax2, norm2)
        cos_pitch2 = math.cos(pitch2_calc)

        if abs(cos_pitch2) > 0.001:  # Avoid division by zero
            imu2_roll_raw = math.atan2(-az2/cos_pitch2, ay2/cos_pitch2) * -1
        else:
            imu2_roll_raw = 0.0

        # Account for IMU1 roll subtraction in firmware (Theta3 -= Theta2)
        imu2_roll_offset = imu2_roll_raw - imu1_roll_offset

        # ===== IMU3 ROLL OFFSET =====
        # Formula: Theta4 = atan2(-ax3/cos(Theta3_calc), ay3/cos(Theta3_calc)) * -1 - IMU3ROLLOFFSET
        #          Theta4 -= Theta2  (subtract IMU1's roll)
        #          Theta4 -= Theta3  (subtract IMU2's adjusted roll)
        norm3 = math.sqrt(ax3**2 + ay3**2)
        pitch3_calc = math.atan2(-az3, norm3)
        cos_pitch3 = math.cos(pitch3_calc)

        if abs(cos_pitch3) > 0.001:  # Avoid division by zero
            imu3_roll_raw = math.atan2(-ax3/cos_pitch3, ay3/cos_pitch3) * -1
        else:
            imu3_roll_raw = 0.0

        # Account for IMU1 and IMU2 roll subtractions in firmware
        imu3_roll_offset = imu3_roll_raw - imu1_roll_offset - imu2_roll_offset

        return imu1_pitch_offset, imu1_roll_offset, imu2_roll_offset, imu3_roll_offset

    def upload_updated_firmware(self):
        """Upload the updated firmware to Arduino"""
        selected_port = self.imu_port_combo.currentText()  # Use same port as IMU
        selected_board = self.imu_board_combo.currentText()
        
        if not selected_port:
            QMessageBox.warning(self, "Warning", "Please select a port first!")
            return
            
        try:
            ui_message = self.logger.log_step(f"Uploading updated firmware to {selected_port} using {selected_board}")
            self.log_imu_message_to_ui(ui_message)
            
            # Use same upload process as other Arduino uploads
            from arduino_compile import ArduinoCompiler
            compiler = ArduinoCompiler()
            
            success = compiler.upload_sketch(self.firmware_file, selected_board, selected_port)
            
            if success:
                ui_message = self.logger.log_step("Updated firmware uploaded successfully!")
                self.log_imu_message_to_ui(ui_message)
                QMessageBox.information(self, "Success", "Updated firmware uploaded successfully!\n\nYour Arduino now has both load cell and IMU functionality with calibrated offsets.")
            else:
                error_msg = "Failed to upload updated firmware. Check connections and try again."
                self.logger.log_error(error_msg)
                self.log_imu_message_to_ui(error_msg)
                QMessageBox.critical(self, "Error", error_msg)
                
        except Exception as e:
            error_msg = f"Upload failed: {str(e)}"
            self.logger.log_error(error_msg)
            self.log_imu_message_to_ui(error_msg)
            QMessageBox.critical(self, "Error", error_msg)
            
    def log_imu_message_to_ui(self, message):
        """Add message to IMU serial output (UI only)"""
        self.imu_serial_output.append(message)
        
        # Auto-scroll to bottom
        cursor = self.imu_serial_output.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.imu_serial_output.setTextCursor(cursor)
        
    def clear_imu_output(self):
        """Clear IMU serial output"""
        self.logger.log("IMU output cleared by user")
        self.imu_serial_output.clear()
        
    # 3-IMU System Methods
    def on_imu_selection_changed(self, text):
        """Handle IMU selection change"""
        if "IMU 1" in text:
            self.current_imu_index = 0
        elif "IMU 2" in text:
            self.current_imu_index = 1
        elif "IMU 3" in text:
            self.current_imu_index = 2
        
        # Reset calibration state when changing IMU selection
        self.imu_calibration_started = False

        imu_name = text.split(" (")[0]  # Extract just "IMU 1", "IMU 2", etc.
        ui_message = self.logger.log_imu(f"Selected {imu_name} for calibration")
        self.log_imu_message_to_ui(ui_message)
        
        # Update UI to show current IMU capabilities (4-offset formula-based)
        if self.current_imu_index == 0:  # IMU 1 - pitch + roll
            self.log_imu_message_to_ui("Note: IMU 1 calibrates PITCH + ROLL (using formula-based method)")
        elif self.current_imu_index == 1:  # IMU 2 - roll only
            self.log_imu_message_to_ui("Note: IMU 2 calibrates ROLL only (relative to IMU1)")
        elif self.current_imu_index == 2:  # IMU 3 - roll only
            self.log_imu_message_to_ui("Note: IMU 3 calibrates ROLL only (relative to IMU1 and IMU2)")
        
        self.log_imu_message_to_ui("Note: Disconnect and reconnect IMU physically for new calibration")
            
    def save_current_imu_offsets(self):
        """Save current IMU calibration as angle offsets (4-offset formula-based)"""
        if not self.current_imu_data:
            QMessageBox.warning(self, "Warning", "No IMU data available. Please connect and calibrate first.")
            return

        # Get current pitch and roll from live data
        current_pitch = self.current_imu_data.get('pitch', 0.0)
        current_roll = self.current_imu_data.get('roll', 0.0)

        imu_names = ["IMU 1", "IMU 2", "IMU 3"]
        current_imu_name = imu_names[self.current_imu_index]

        if self.current_imu_index == 0:  # IMU 1 - saves PITCH + ROLL
            self.angle_offset1 = current_pitch
            self.angle_offset2 = current_roll
            self.angle_offset1_label.setText(f"{self.angle_offset1:.6f}")
            self.angle_offset2_label.setText(f"{self.angle_offset2:.6f}")
            ui_message = self.logger.log_imu(f"Saved {current_imu_name} offsets (formula-based):")
            ui_message += f"\n  Pitch: {self.angle_offset1:.6f} rad\n  Roll: {self.angle_offset2:.6f} rad"

        elif self.current_imu_index == 1:  # IMU 2 - saves ROLL ONLY (relative to IMU1)
            # IMU2 only stores relative roll offset
            self.angle_offset3 = current_roll
            self.angle_offset3_label.setText(f"{self.angle_offset3:.6f}")
            ui_message = self.logger.log_imu(f"Saved {current_imu_name} offset (formula-based, Roll only):")
            ui_message += f"\n  Roll: {self.angle_offset3:.6f} rad (relative to IMU1)"

        elif self.current_imu_index == 2:  # IMU 3 - saves ROLL ONLY (relative to IMU1 and IMU2)
            # IMU3 only stores relative roll offset
            self.angle_offset4 = current_roll
            self.angle_offset4_label.setText(f"{self.angle_offset4:.6f}")
            ui_message = self.logger.log_imu(f"Saved {current_imu_name} offset (formula-based, Roll only):")
            ui_message += f"\n  Roll: {self.angle_offset4:.6f} rad (relative to IMU1+IMU2)"

        self.log_imu_message_to_ui(ui_message)

        # Check if all IMUs are calibrated
        self.check_all_imus_calibrated()

        QMessageBox.information(self, "Success", f"{current_imu_name} angle offsets saved successfully!")
        
    def check_all_imus_calibrated(self):
        """Check if all 4 IMU offsets have been calculated and saved"""
        # New formula-based method uses 4 offsets: IMU1 pitch, IMU1 roll, IMU2 roll, IMU3 roll
        if (self.angle_offset1 != 0.0 and self.angle_offset2 != 0.0 and
            self.angle_offset3 != 0.0 and self.angle_offset4 != 0.0):
            ui_message = self.logger.log_imu("All 3 IMUs calibrated (4 offsets)! Go to Upload Firmware tab.")
            self.log_imu_message_to_ui(ui_message)
    
    def update_final_tab_status(self):
        """Update the final tab with current calibration status"""
        # Update load cell factor display
        if hasattr(self, 'final_calibration_factor_label'):
            if self.current_calibration_factor != 1.0:
                self.final_calibration_factor_label.setText(f"{self.current_calibration_factor:.2f}")
            else:
                self.final_calibration_factor_label.setText("Not Calibrated")

        # Update 4 IMU offset labels (formula-based: IMU1 pitch, IMU1 roll, IMU2 roll, IMU3 roll)
        if hasattr(self, 'final_angle_offset1_label'):
            self.final_angle_offset1_label.setText(f"{self.angle_offset1:.6f}")
        if hasattr(self, 'final_angle_offset2_label'):
            self.final_angle_offset2_label.setText(f"{self.angle_offset2:.6f}")
        if hasattr(self, 'final_angle_offset3_label'):
            self.final_angle_offset3_label.setText(f"{self.angle_offset3:.6f}")
        if hasattr(self, 'final_angle_offset4_label'):
            self.final_angle_offset4_label.setText(f"{self.angle_offset4:.6f}")
        # Legacy offsets (if UI still references them)
        if hasattr(self, 'final_angle_offset5_label'):
            self.final_angle_offset5_label.setText("N/A")
        if hasattr(self, 'final_angle_offset6_label'):
            self.final_angle_offset6_label.setText("N/A")

        # Check if we have complete calibration data (4 offsets required)
        has_loadcell = self.current_calibration_factor != 1.0
        has_all_imus = (self.angle_offset1 != 0.0 and self.angle_offset2 != 0.0 and
                       self.angle_offset3 != 0.0 and self.angle_offset4 != 0.0)

        # Enable buttons in final tab if we have calibration data
        if hasattr(self, 'update_firmware_with_values_button'):
            self.update_firmware_with_values_button.setEnabled(has_loadcell and has_all_imus)
        if hasattr(self, 'upload_final_firmware_button'):
            self.upload_final_firmware_button.setEnabled(has_loadcell and has_all_imus)
    
    # TOML Management Methods
    def save_current_calibration(self):
        """Save current calibration data to TOML file with timestamp"""
        try:
            # Create calibration data dictionary
            # Using 4-offset formula-based calculation:
            # - IMU1: pitch + roll
            # - IMU2: roll only (relative to IMU1)
            # - IMU3: roll only (relative to IMU1 and IMU2)
            calibration_data = {
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "version": "2.0",
                    "description": "Load Cell and 3-IMU Calibration Data (4 formula-based offsets)",
                    "mars_id": self.current_mars_id if self.current_mars_id else "Unknown"
                },
                "load_cell": {
                    "calibration_factor": float(self.current_calibration_factor)
                },
                "imu_offsets": {
                    "imu1_pitch_offset": float(self.angle_offset1),
                    "imu1_roll_offset": float(self.angle_offset2),
                    "imu2_roll_offset": float(self.angle_offset3),
                    "imu3_roll_offset": float(self.angle_offset4)
                }
            }
            
            # Generate filename with Mars ID and timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            mars_prefix = self.get_mars_filename_prefix()
            filename = f"{mars_prefix}calibration_{timestamp}.toml"
            filepath = os.path.join(self.calibrations_dir, filename)
            
            # Save to TOML file
            with open(filepath, 'w', encoding='utf-8') as f:
                toml.dump(calibration_data, f)
            
            self.logger.log(f"Calibration saved to: {filename}")
            QMessageBox.information(self, "Success", f"Calibration saved successfully!\n{filename}")
            
            # Refresh the history table
            self.refresh_calibration_history()
            
        except Exception as e:
            error_msg = f"Failed to save calibration: {str(e)}"
            self.logger.log_error(error_msg)
            QMessageBox.critical(self, "Error", error_msg)
    
    def refresh_calibration_history(self):
        """Refresh the calibration history table from TOML files"""
        try:
            # Clear existing table
            self.calibration_history_table.setRowCount(0)

            # Find all TOML calibration files (matches Mars_####_calibration_*.toml or calibration_*.toml)
            toml_files = glob.glob(os.path.join(self.calibrations_dir, "*calibration_*.toml"))
            toml_files.sort(reverse=True)  # Most recent first

            print(f"\n[CALIBRATION HISTORY] Found {len(toml_files)} calibration files")
            print(f"[CALIBRATION HISTORY] Looking in: {self.calibrations_dir}")
            self.logger.log(f"Found {len(toml_files)} calibration files")

            # Populate table
            for i, filepath in enumerate(toml_files):
                print(f"[CALIBRATION HISTORY] Processing file {i}: {os.path.basename(filepath)}")
                try:
                    print(f"[CALIBRATION HISTORY] Opening file for reading...")
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = toml.load(f)
                    print(f"[CALIBRATION HISTORY] Successfully parsed TOML file")

                    # Extract data
                    metadata = data.get("metadata", {})
                    timestamp = metadata.get("timestamp", "Unknown")
                    mars_id = metadata.get("mars_id", "Unknown")
                    loadcell_factor = data.get("load_cell", {}).get("calibration_factor", 0.0)
                    imu_data = data.get("imu_offsets", {})

                    print(f"[CALIBRATION HISTORY] Extracted data:")
                    print(f"  Mars ID: {mars_id}")
                    print(f"  Timestamp: {timestamp}")
                    print(f"  Load Factor: {loadcell_factor}")
                    print(f"  IMU Data Keys: {list(imu_data.keys())}")

                    # Format timestamp for display
                    try:
                        dt = datetime.fromisoformat(timestamp)
                        display_time = dt.strftime("%Y-%m-%d %H:%M:%S")
                    except Exception as ts_err:
                        display_time = timestamp
                        self.logger.log_error(f"Timestamp parse error: {str(ts_err)}")

                    # Format Mars ID for display
                    display_mars_id = str(mars_id) if mars_id != "Unknown" else "Unknown"

                    # Add row to table
                    print(f"[CALIBRATION HISTORY] Inserting row {i} into table")
                    self.calibration_history_table.insertRow(i)

                    print(f"[CALIBRATION HISTORY] Setting column 0 (Mars ID): {display_mars_id}")
                    self.calibration_history_table.setItem(i, 0, QTableWidgetItem(display_mars_id))

                    print(f"[CALIBRATION HISTORY] Setting column 1 (Date/Time): {display_time}")
                    self.calibration_history_table.setItem(i, 1, QTableWidgetItem(display_time))

                    # Load cell factor
                    if loadcell_factor != 0.0:
                        cal_str = f"{loadcell_factor:.2f}"
                    else:
                        cal_str = "NA"
                    self.calibration_history_table.setItem(i, 2, QTableWidgetItem(cal_str))

                    # Detect format: v2.0 (4 offsets) or v1.0 (6 offsets)
                    version = metadata.get("version", "1.0")

                    # Extract 4-offset values (works for both formats)
                    if version == "2.0":
                        # New format: direct 4-offset names
                        imu1_pitch = imu_data.get('imu1_pitch_offset', 0.0)
                        imu1_roll = imu_data.get('imu1_roll_offset', 0.0)
                        imu2_roll = imu_data.get('imu2_roll_offset', 0.0)
                        imu3_roll = imu_data.get('imu3_roll_offset', 0.0)
                    else:
                        # Legacy v1.0 format: convert 6 offsets to 4-offset display
                        # Display IMU1 pitch, IMU1 roll, IMU2 roll, IMU3 roll
                        imu1_pitch = imu_data.get('imu1_pitch', 0.0)
                        imu1_roll = imu_data.get('imu1_roll', 0.0)
                        imu2_roll = imu_data.get('imu2_roll', 0.0)
                        imu3_roll = imu_data.get('imu3_roll', 0.0)

                    # Display 4 offsets only
                    imu1_pitch_str = f"{imu1_pitch:.6f}" if imu1_pitch != 0.0 else "NA"
                    self.calibration_history_table.setItem(i, 3, QTableWidgetItem(imu1_pitch_str))

                    imu1_roll_str = f"{imu1_roll:.6f}" if imu1_roll != 0.0 else "NA"
                    self.calibration_history_table.setItem(i, 4, QTableWidgetItem(imu1_roll_str))

                    imu2_roll_str = f"{imu2_roll:.6f}" if imu2_roll != 0.0 else "NA"
                    self.calibration_history_table.setItem(i, 5, QTableWidgetItem(imu2_roll_str))

                    imu3_roll_str = f"{imu3_roll:.6f}" if imu3_roll != 0.0 else "NA"
                    self.calibration_history_table.setItem(i, 6, QTableWidgetItem(imu3_roll_str))

                    # Store filepath in row data for loading (now in Mars ID column)
                    self.calibration_history_table.item(i, 0).setData(Qt.UserRole, filepath)

                    self.logger.log(f"Loaded calibration row {i}: Mars ID={display_mars_id}, Load Factor={cal_str}")

                except Exception as e:
                    print(f"[CALIBRATION HISTORY] ERROR in file loop: {str(e)}")
                    import traceback
                    print(f"[CALIBRATION HISTORY] Traceback: {traceback.format_exc()}")
                    self.logger.log_error(f"Error reading {os.path.basename(filepath)}: {str(e)}")
                    self.logger.log_error(f"Traceback: {traceback.format_exc()}")
                    continue

            print(f"[CALIBRATION HISTORY] Refresh complete: {len(toml_files)} files loaded")
            self.logger.log(f"Calibration history refresh complete: {len(toml_files)} files loaded")

        except Exception as e:
            print(f"[CALIBRATION HISTORY] ERROR in outer try: {str(e)}")
            import traceback
            print(f"[CALIBRATION HISTORY] Traceback: {traceback.format_exc()}")
            error_msg = f"Failed to refresh calibration history: {str(e)}"
            self.logger.log_error(error_msg)
            self.logger.log_error(f"Traceback: {traceback.format_exc()}")
    
    def load_selected_calibration(self):
        """Load the selected calibration from the history table and display values"""
        try:
            selected_items = self.calibration_history_table.selectedItems()
            if not selected_items:
                QMessageBox.warning(self, "Warning", "Please select a calibration to load.")
                return

            # Get filepath from the first column (Mars ID column) of selected row
            row = selected_items[0].row()
            filepath_item = self.calibration_history_table.item(row, 0)
            filepath = filepath_item.data(Qt.UserRole)

            if not filepath or not os.path.exists(filepath):
                QMessageBox.warning(self, "Warning", "Calibration file not found.")
                return

            # Load TOML data
            with open(filepath, 'r', encoding='utf-8') as f:
                data = toml.load(f)

            # Update current calibration values
            self.current_calibration_factor = data.get("load_cell", {}).get("calibration_factor", 1.0)
            imu_data = data.get("imu_offsets", {})

            # Support both old (v1.0 - 6 offsets) and new (v2.0 - 4 offsets) formats
            metadata = data.get("metadata", {})
            version = metadata.get("version", "1.0")

            if version == "2.0":
                # New format with 4 formula-based offsets
                self.angle_offset1 = imu_data.get("imu1_pitch_offset", 0.0)
                self.angle_offset2 = imu_data.get("imu1_roll_offset", 0.0)
                self.angle_offset3 = imu_data.get("imu2_roll_offset", 0.0)
                self.angle_offset4 = imu_data.get("imu3_roll_offset", 0.0)
                # Set unused offsets to 0
                self.angle_offset5 = 0.0
                self.angle_offset6 = 0.0
            else:
                # Legacy format with 6 offsets
                self.angle_offset1 = imu_data.get("imu1_pitch", 0.0)
                self.angle_offset2 = imu_data.get("imu1_roll", 0.0)
                self.angle_offset3 = imu_data.get("imu2_pitch", 0.0)
                self.angle_offset4 = imu_data.get("imu2_roll", 0.0)
                self.angle_offset5 = imu_data.get("imu3_pitch", 0.0)
                self.angle_offset6 = imu_data.get("imu3_roll", 0.0)

            # Update IMU tab labels for currently set offsets
            if hasattr(self, 'angle_offset1_label'):
                self.angle_offset1_label.setText(f"{self.angle_offset1:.6f}")
            if hasattr(self, 'angle_offset2_label'):
                self.angle_offset2_label.setText(f"{self.angle_offset2:.6f}")
            if hasattr(self, 'angle_offset3_label'):
                self.angle_offset3_label.setText(f"{self.angle_offset3:.6f}")
            if hasattr(self, 'angle_offset4_label'):
                self.angle_offset4_label.setText(f"{self.angle_offset4:.6f}")

            # Update all display labels (including final tab)
            self.update_final_tab_status()

            filename = os.path.basename(filepath)
            mars_id = metadata.get("mars_id", "Unknown")

            # Log detailed information about loaded calibration
            self.logger.log(f"Loaded calibration from: {filename}")
            self.logger.log(f"  Mars ID: {mars_id}")
            self.logger.log(f"  Load Cell Factor: {self.current_calibration_factor:.2f}")
            self.logger.log(f"  Format version: {version}")

            if version == "2.0":
                self.logger.log(f"  IMU1 Pitch Offset: {self.angle_offset1:.6f} rad")
                self.logger.log(f"  IMU1 Roll Offset:  {self.angle_offset2:.6f} rad")
                self.logger.log(f"  IMU2 Roll Offset:  {self.angle_offset3:.6f} rad")
                self.logger.log(f"  IMU3 Roll Offset:  {self.angle_offset4:.6f} rad")

                success_msg = (f"Calibration loaded successfully (v2.0 - Formula-based)!\n\n"
                              f"File: {filename}\n"
                              f"Mars ID: {mars_id}\n\n"
                              f"Load Cell Factor: {self.current_calibration_factor:.2f}\n"
                              f"IMU1 Pitch: {self.angle_offset1:.6f} rad\n"
                              f"IMU1 Roll:  {self.angle_offset2:.6f} rad\n"
                              f"IMU2 Roll:  {self.angle_offset3:.6f} rad\n"
                              f"IMU3 Roll:  {self.angle_offset4:.6f} rad\n\n"
                              f"Ready to upload firmware!")
            else:
                self.logger.log(f"  IMU1 Pitch: {self.angle_offset1:.4f}, Roll: {self.angle_offset2:.4f}")
                self.logger.log(f"  IMU2 Pitch: {self.angle_offset3:.4f}, Roll: {self.angle_offset4:.4f}")
                self.logger.log(f"  IMU3 Pitch: {self.angle_offset5:.4f}, Roll: {self.angle_offset6:.4f}")

                success_msg = (f"Calibration loaded successfully (v1.0 - Legacy)!\n\n"
                              f"File: {filename}\n"
                              f"Mars ID: {mars_id}\n\n"
                              f"Load Cell Factor: {self.current_calibration_factor:.2f}\n"
                              f"IMU1 - Pitch: {self.angle_offset1:.4f}, Roll: {self.angle_offset2:.4f}\n"
                              f"IMU2 - Pitch: {self.angle_offset3:.4f}, Roll: {self.angle_offset4:.4f}\n"
                              f"IMU3 - Pitch: {self.angle_offset5:.4f}, Roll: {self.angle_offset6:.4f}\n\n"
                              f"Ready to upload firmware!")

            QMessageBox.information(self, "Success", success_msg)

        except Exception as e:
            error_msg = f"Failed to load calibration: {str(e)}"
            self.logger.log_error(error_msg)
            QMessageBox.critical(self, "Error", error_msg)
    
    def update_firmware_with_current_values(self):
        """Update marsfire variable.h with current calibration values using formula-based 4 offsets"""
        try:
            # Verify we have valid calibration data
            if self.current_calibration_factor == 1.0:
                QMessageBox.warning(self, "Warning", "Please load or perform Load Cell calibration first.")
                return

            has_all_imus = (self.angle_offset1 != 0.0 and self.angle_offset2 != 0.0 and
                           self.angle_offset3 != 0.0 and self.angle_offset4 != 0.0)

            if not has_all_imus:
                QMessageBox.warning(self, "Warning", "Please load or perform all IMU calibrations first.")
                return

            # Read variable.h file from marsfire (with UTF-8 encoding to prevent Unicode errors)
            variable_h_file = os.path.join(self.firmware_v2_dir, 'variable.h')
            with open(variable_h_file, 'r', encoding='utf-8') as f:
                variable_content = f.read()

            # Update load cell calibration factor
            variable_content = self.update_define_in_firmware(variable_content, 'LOACELL_CALIB_FACTOR', self.current_calibration_factor)

            # Update 4 IMU offset values in variable.h using #define format
            # These are calculated using the firmware formulas (see calculate_imu_offsets_from_accel)
            variable_content = self.update_define_in_firmware(variable_content, 'IMU1PITCHOFFSET', self.angle_offset1)
            variable_content = self.update_define_in_firmware(variable_content, 'IMU1ROLLOFFSET', self.angle_offset2)
            # Note: marsfire still has IMU2PITCHOFFSET/IMU2ROLLOFFSET/IMU3PITCHOFFSET/IMU3ROLLOFFSET
            # We're using the new 4-offset system, so we update only the roll offsets for IMU2 and IMU3
            # IMU2PITCHOFFSET stays 0.00, we only use IMU2ROLLOFFSET
            variable_content = self.update_define_in_firmware(variable_content, 'IMU2ROLLOFFSET', self.angle_offset3)
            # IMU3PITCHOFFSET stays 0.00, we only use IMU3ROLLOFFSET
            variable_content = self.update_define_in_firmware(variable_content, 'IMU3ROLLOFFSET', self.angle_offset4)

            # Write updated variable.h file (with UTF-8 encoding to prevent Unicode errors)
            with open(variable_h_file, 'w', encoding='utf-8') as f:
                f.write(variable_content)

            # Success message with all updated values
            ui_message = self.logger.log(f"✓ Updated marsfire variable.h with all calibration values:")
            ui_message += f"\n  Load Cell Factor: {self.current_calibration_factor:.2f}"
            ui_message += f"\n  IMU1 Pitch: {self.angle_offset1:.6f} rad"
            ui_message += f"\n  IMU1 Roll:  {self.angle_offset2:.6f} rad"
            ui_message += f"\n  IMU2 Roll:  {self.angle_offset3:.6f} rad"
            ui_message += f"\n  IMU3 Roll:  {self.angle_offset4:.6f} rad"

            self.logger.log(ui_message)
            QMessageBox.information(self, "Success",
                f"Marsfire variable.h updated successfully!\n\n"
                f"Updated Values:\n"
                f"• Load Cell Factor: {self.current_calibration_factor:.2f}\n"
                f"• IMU1 Pitch: {self.angle_offset1:.6f} rad\n"
                f"• IMU1 Roll:  {self.angle_offset2:.6f} rad\n"
                f"• IMU2 Roll:  {self.angle_offset3:.6f} rad\n"
                f"• IMU3 Roll:  {self.angle_offset4:.6f} rad\n\n"
                f"Ready to upload marsfire firmware!")

        except Exception as e:
            error_msg = f"Failed to update firmware: {str(e)}"
            self.logger.log_error(error_msg)
            QMessageBox.critical(self, "Error", error_msg)

    def upload_final_firmware(self):
        """Upload the final firmware with all calibration data"""
        selected_port = self.final_port_combo.currentText()
        selected_board = self.final_board_combo.currentText()

        if not selected_port:
            QMessageBox.warning(self, "Warning", "Please select a port first!")
            return

        try:
            # First update firmware with current values
            self.update_firmware_with_current_values()

            # Log upload start
            ui_message = self.logger.log_step(f"Uploading final firmware to {selected_port} using {selected_board}")
            self.log_upload_message_to_ui(ui_message)

            # Upload the firmware
            from arduino_compile import ArduinoCompiler
            compiler = ArduinoCompiler()

            success = compiler.upload_sketch(self.firmware_file, selected_board, selected_port)

            if success:
                ui_message = self.logger.log_step("Final firmware uploaded successfully!")
                self.log_upload_message_to_ui(ui_message)
                QMessageBox.information(self, "Success",
                    "Final firmware uploaded successfully!\n\n"
                    "Your Mars device now has fully calibrated load cell and IMU functionality.")
            else:
                error_msg = "Failed to upload final firmware. Check connections and try again."
                self.logger.log_error(error_msg)
                self.log_upload_message_to_ui(error_msg)
                QMessageBox.critical(self, "Error", error_msg)

        except Exception as e:
            error_msg = f"Upload failed: {str(e)}"
            self.logger.log_error(error_msg)
            self.log_upload_message_to_ui(error_msg)
            QMessageBox.critical(self, "Error", error_msg)

    def log_upload_message_to_ui(self, message):
        """Add message to upload firmware status output"""
        if hasattr(self, 'upload_status_text'):
            self.upload_status_text.append(message)

            # Auto-scroll to bottom
            from PySide6.QtGui import QTextCursor
            cursor = self.upload_status_text.textCursor()
            cursor.movePosition(QTextCursor.End)
            self.upload_status_text.setTextCursor(cursor)
            
    def closeEvent(self, event):
        """Handle application close"""
        self.logger.log_step("Application closing")
        if self.is_connected:
            self.disconnect_serial()
        if self.is_imu_connected:
            self.disconnect_imu_serial()
        
        # Clean up temp files
        self.user_data.cleanup_temp_files()
        
        # Write session end
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        footer = f"\n{'='*60}\nSESSION END: {timestamp}\n{'='*60}\n"
        self.logger.write_to_file(footer)
        
        event.accept()