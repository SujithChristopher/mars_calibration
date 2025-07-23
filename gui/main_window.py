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

from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QTabWidget, QMessageBox, QLabel
from PySide6.QtCore import QTimer, Signal, QThread, QObject, Qt
from PySide6.QtGui import QFont, QTextCursor

from utils.logger import Logger
from gui.workers.serial_worker import SerialWorker
from gui.workers.imu_worker import IMUDataWorker
from gui.load_cell_tab import setup_load_cell_tab
from gui.imu_tab import setup_imu_tab


class LoadCellCalibrationGUI(QMainWindow):
    # Add signals for thread-safe logging and step updates
    log_signal = Signal(str)
    step_update_signal = Signal(int, str)  # step number, message
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Load Cell & IMU Calibration Wizard")
        self.setGeometry(100, 100, 1200, 800)
        
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
        
        # Step tracking
        self.current_step = 1
        
        # Initialize logger
        log_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logs", "logs.txt")
        self.logger = Logger(log_file_path)
        self.logger.log_step("Application started")
        
        # Default file paths
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.calibration_file = os.path.join(base_path, "calibration", "calibration.ino")
        self.firmware_file = os.path.join(base_path, "firmware", "firmware.ino")
        self.imu_file = os.path.join(base_path, "imu_program", "imu_program.ino")
        
        self.logger.log(f"Calibration file path: {self.calibration_file}")
        self.logger.log(f"Firmware file path: {self.firmware_file}")
        self.logger.log(f"IMU file path: {self.imu_file}")
        
        # Connect signals to methods
        self.log_signal.connect(self.log_message_to_ui)
        self.step_update_signal.connect(self.handle_step_update)
        
        # Setup UI
        self.setup_ui()
        self.refresh_ports()
        self.update_step_status()
        
        # Timer for periodic updates
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_display)
        
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
        
    def update_step_status(self):
        """Update the visual status of steps"""
        # Reset all steps
        self.step1.set_current(False)
        self.step1.set_completed(False)
        self.step2.set_current(False)
        self.step2.set_completed(False)
        self.step3.set_current(False)
        self.step3.set_completed(False)
        
        # Enable/disable groups
        self.step1_group.setEnabled(True)
        self.step2_group.setEnabled(False)
        self.step3_group.setEnabled(False)
        
        if self.current_step == 1:
            self.step1.set_current(True)
            self.step1_group.setEnabled(True)
        elif self.current_step == 2:
            self.step1.set_completed(True)
            self.step2.set_current(True)
            self.step2_group.setEnabled(True)
        elif self.current_step == 3:
            self.step1.set_completed(True)
            self.step2.set_completed(True)
            self.step3.set_current(True)
            self.step3_group.setEnabled(True)
        elif self.current_step == 4:  # All completed
            self.step1.set_completed(True)
            self.step2.set_completed(True)
            self.step3.set_completed(True)
    
    # Load Cell Methods
    def upload_calibration_code(self):
        """Upload calibration Arduino code"""
        self.logger.log_upload("Starting calibration code upload")
        
        if not os.path.exists(self.calibration_file):
            error_msg = f"Calibration file not found: {self.calibration_file}"
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
        ui_message = self.logger.log_upload(f"Starting calibration upload to {selected_port}")
        self.log_message_to_ui(ui_message)
        
        # Run upload in separate thread
        threading.Thread(target=self._upload_thread, args=(self.calibration_file, selected_board, selected_port, "calibration"), daemon=True).start()
        
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
            replacement = f'float calibration_factor = {self.current_calibration_factor:.2f};'
            
            updated_content = re.sub(pattern, replacement, content)
            
            # Check if replacement was made
            if 'calibration_factor' in content:
                # Create backup
                backup_path = self.firmware_file + ".backup"
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
                self.log_signal.emit(self.logger.log_error("Please place arduino-cli.exe in the same folder as this program."))
                return
            
            # Install required cores if needed
            if "mbed_nano" in board:
                self.log_signal.emit(self.logger.log_upload("Checking Arduino Nano core installation..."))
                core_install_cmd = f'"{arduino_cli_path}" core install arduino:mbed_nano'
                result = subprocess.run(core_install_cmd, shell=True, capture_output=True, text=True)
                if result.returncode == 0:
                    self.log_signal.emit(self.logger.log_upload("Arduino Nano core installation check complete"))
                else:
                    self.log_signal.emit(self.logger.log_warning(f"Arduino Nano core install result: {result.stderr}"))
            elif "teensy" in board:
                self.log_signal.emit(self.logger.log_upload("Checking Teensy core installation..."))
                core_install_cmd = f'"{arduino_cli_path}" core install teensy:avr'
                result = subprocess.run(core_install_cmd, shell=True, capture_output=True, text=True)
                if result.returncode == 0:
                    self.log_signal.emit(self.logger.log_upload("Teensy core installation check complete"))
                else:
                    self.log_signal.emit(self.logger.log_warning(f"Teensy core install result: {result.stderr}"))
                    # Try alternative Teensy installation
                    self.log_signal.emit(self.logger.log_upload("Trying alternative Teensy core installation..."))
                    alt_core_cmd = f'"{arduino_cli_path}" core install arduino:teensy'
                    alt_result = subprocess.run(alt_core_cmd, shell=True, capture_output=True, text=True)
                    if alt_result.returncode == 0:
                        self.log_signal.emit(self.logger.log_success("Alternative Teensy core installation successful"))
                    else:
                        self.log_signal.emit(self.logger.log_error("Teensy core installation failed. Please install Teensyduino manually."))
            
            # Compile command
            compile_cmd = f'"{arduino_cli_path}" compile --fqbn {board} "{sketch_path}"'
            
            # Upload command
            upload_cmd = f'"{arduino_cli_path}" upload -p {port} --fqbn {board} "{sketch_path}"'
            
            # Execute commands
            self.log_signal.emit(self.logger.log_upload(f"Compiling {upload_type} sketch..."))
            result = subprocess.run(compile_cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                self.log_signal.emit(self.logger.log_success(f"{upload_type.title()} compilation successful!"))
                self.log_signal.emit(self.logger.log_upload(f"Uploading {upload_type} to {port}..."))
                
                result = subprocess.run(upload_cmd, shell=True, capture_output=True, text=True)
                
                if result.returncode == 0:
                    self.log_signal.emit(self.logger.log_success(f"{upload_type.title()} upload successful!"))
                    
                    # Update step progress using signal
                    if upload_type == "calibration":
                        self.step_update_signal.emit(2, "✓ Step 1 completed! Now connect to serial and calibrate.")
                    elif upload_type == "firmware":
                        self.step_update_signal.emit(4, "✓ All steps completed! Load cell is ready to use.")
                    
                else:
                    self.log_signal.emit(self.logger.log_error(f"{upload_type.title()} upload failed: {result.stderr}"))
                    if "mbed_nano" in board:
                        self.log_signal.emit(self.logger.log_warning("Note: Make sure to double-press the reset button on Nano 33 BLE to enter bootloader mode"))
                    elif "teensy" in board:
                        self.log_signal.emit(self.logger.log_warning("Note: Make sure Teensy is in programming mode. Press the program button on Teensy if needed"))
                        self.log_signal.emit(self.logger.log_warning("Tip: Try using Teensy Loader application if upload continues to fail"))
            else:
                self.log_signal.emit(self.logger.log_error(f"{upload_type.title()} compilation failed: {result.stderr}"))
                
        except Exception as e:
            self.log_signal.emit(self.logger.log_error(f"{upload_type.title()} upload error: {str(e)}"))
        finally:
            # Hide progress bar and re-enable button
            self.progress_bar.setVisible(False)
            if upload_type == "calibration":
                self.upload_cal_button.setEnabled(True)
            elif upload_type == "IMU":
                self.upload_imu_button.setEnabled(True)
            else:
                self.upload_firmware_button.setEnabled(True)
            
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
                    
                    # Move to step 3
                    self.current_step = 3
                    self.update_step_status()
                    self.update_firmware_button.setEnabled(True)
                    
                    step_msg = f"✓ Step 2 completed! Calibration factor: {cal_factor:.2f}"
                    ui_message = self.logger.log_step(step_msg)
                    self.log_message_to_ui(ui_message)
                    
                    QMessageBox.information(self, "Calibration Complete", 
                        f"Calibration successful!\nCalibration Factor: {cal_factor:.2f}\n\nYou can now proceed to Step 3.")
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
    
    # IMU Methods
    def upload_imu_code(self):
        """Upload IMU Arduino code"""
        self.logger.log_imu("Starting IMU code upload")
        
        if not os.path.exists(self.imu_file):
            error_msg = f"IMU file not found: {self.imu_file}"
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
        ui_message = self.logger.log_imu(f"Starting IMU upload to {selected_port}")
        self.log_imu_message_to_ui(ui_message)
        
        # Run upload in separate thread
        threading.Thread(target=self._upload_thread, args=(self.imu_file, selected_board, selected_port, "IMU"), daemon=True).start()
        
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
            self.reset_imu_offsets_button.setEnabled(True)
            self.save_imu_cal_button.setEnabled(True)
            self.load_imu_cal_button.setEnabled(True)
            
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
        self.imu_connect_button.setText("Connect to IMU")
        self.imu_connect_button.setStyleSheet("")
        self.start_imu_cal_button.setEnabled(False)
        self.reset_imu_offsets_button.setEnabled(False)
        self.save_imu_cal_button.setEnabled(False)
        self.load_imu_cal_button.setEnabled(False)
        
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
        """Update offset display labels"""
        try:
            self.offset_x_label.setText(f"{data['offset_x']:.4f}")
            self.offset_y_label.setText(f"{data['offset_y']:.4f}")
            self.offset_z_label.setText(f"{data['offset_z']:.4f}")
        except KeyError:
            pass
            
    def handle_imu_connection_lost(self):
        """Handle lost IMU connection"""
        self.logger.log_error("IMU connection lost")
        self.disconnect_imu_serial()
        QMessageBox.warning(self, "Warning", "IMU connection lost!")
        
    def start_imu_calibration(self):
        """Start IMU calibration process"""
        if self.imu_worker:
            self.imu_worker.send_data("c")
            ui_message = self.logger.log_imu("Starting IMU calibration - place device flat and still")
            self.log_imu_message_to_ui("Sent: c (start IMU calibration)")
            
    def reset_imu_offsets(self):
        """Reset IMU offsets"""
        if self.imu_worker:
            self.imu_worker.send_data("r")
            ui_message = self.logger.log_imu("Resetting IMU offsets")
            self.log_imu_message_to_ui("Sent: r (reset IMU offsets)")
            
    def save_imu_calibration(self):
        """Save IMU calibration to EEPROM"""
        if self.imu_worker:
            self.imu_worker.send_data("s")
            ui_message = self.logger.log_imu("Saving IMU calibration to EEPROM")
            self.log_imu_message_to_ui("Sent: s (save IMU calibration)")
            
    def load_imu_calibration(self):
        """Load IMU calibration from EEPROM"""
        if self.imu_worker:
            self.imu_worker.send_data("l")
            ui_message = self.logger.log_imu("Loading IMU calibration from EEPROM")
            self.log_imu_message_to_ui("Sent: l (load IMU calibration)")
            
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
        
    def closeEvent(self, event):
        """Handle application close"""
        self.logger.log_step("Application closing")
        if self.is_connected:
            self.disconnect_serial()
        if self.is_imu_connected:
            self.disconnect_imu_serial()
        
        # Write session end
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        footer = f"\n{'='*60}\nSESSION END: {timestamp}\n{'='*60}\n"
        self.logger.write_to_file(footer)
        
        event.accept()