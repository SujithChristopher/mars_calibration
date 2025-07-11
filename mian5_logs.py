import sys
import os
import subprocess
import threading
import time
import serial
import serial.tools.list_ports
from datetime import datetime
from PySide6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                               QWidget, QPushButton, QLabel, QLineEdit, QTextEdit, 
                               QComboBox, QGroupBox, QSpinBox, QDoubleSpinBox,
                               QMessageBox, QProgressBar, QSplitter, QFrame)
from PySide6.QtCore import QTimer, Signal, QObject, QThread, Qt
from PySide6.QtGui import QFont, QTextCursor, QPalette


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


class SerialWorker(QObject):
    """Worker thread for handling serial communication"""
    data_received = Signal(str)
    connection_lost = Signal()
    
    def __init__(self, port, baudrate):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.serial_connection = None
        self.running = False
        
    def start_connection(self):
        """Start serial connection and reading loop"""
        try:
            self.serial_connection = serial.Serial(self.port, self.baudrate, timeout=1)
            self.running = True
            self.read_loop()
        except Exception as e:
            self.data_received.emit(f"Connection error: {str(e)}")
            
    def read_loop(self):
        """Continuously read from serial port"""
        while self.running and self.serial_connection:
            try:
                if self.serial_connection.in_waiting:
                    data = self.serial_connection.readline().decode('utf-8').strip()
                    if data:
                        self.data_received.emit(data)
            except Exception as e:
                self.connection_lost.emit()
                break
                
    def send_data(self, data):
        """Send data to serial port"""
        if self.serial_connection and self.serial_connection.is_open:
            try:
                self.serial_connection.write(data.encode('utf-8'))
                return True
            except Exception as e:
                self.data_received.emit(f"Send error: {str(e)}")
                return False
        return False
        
    def stop_connection(self):
        """Stop serial connection"""
        self.running = False
        if self.serial_connection:
            self.serial_connection.close()


class StepIndicator(QWidget):
    """Custom widget for showing step progress with checkmarks"""
    def __init__(self, step_number, title, description):
        super().__init__()
        self.step_number = step_number
        self.title = title
        self.description = description
        self.is_completed = False
        self.is_current = False
        self.setup_ui()
        
    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Step circle/checkmark
        self.step_label = QLabel()
        self.step_label.setFixedSize(40, 40)
        self.step_label.setAlignment(Qt.AlignCenter)
        self.step_label.setStyleSheet("""
            QLabel {
                border: 2px solid #ccc;
                border-radius: 20px;
                background-color: #f0f0f0;
                color: #666;
                font-weight: bold;
                font-size: 16px;
            }
        """)
        self.step_label.setText(str(self.step_number))
        
        # Text content
        text_layout = QVBoxLayout()
        
        self.title_label = QLabel(self.title)
        self.title_label.setFont(QFont("Arial", 12, QFont.Bold))
        
        self.desc_label = QLabel(self.description)
        self.desc_label.setFont(QFont("Arial", 10))
        self.desc_label.setStyleSheet("color: #666;")
        
        text_layout.addWidget(self.title_label)
        text_layout.addWidget(self.desc_label)
        text_layout.addStretch()
        
        layout.addWidget(self.step_label)
        layout.addLayout(text_layout)
        layout.addStretch()
        
        self.update_appearance()
        
    def set_completed(self, completed=True):
        self.is_completed = completed
        self.update_appearance()
        
    def set_current(self, current=True):
        self.is_current = current
        self.update_appearance()
        
    def update_appearance(self):
        if self.is_completed:
            self.step_label.setStyleSheet("""
                QLabel {
                    border: 2px solid #4CAF50;
                    border-radius: 20px;
                    background-color: #4CAF50;
                    color: white;
                    font-weight: bold;
                    font-size: 16px;
                }
            """)
            self.step_label.setText("✓")
            self.title_label.setStyleSheet("color: #4CAF50;")
        elif self.is_current:
            self.step_label.setStyleSheet("""
                QLabel {
                    border: 2px solid #2196F3;
                    border-radius: 20px;
                    background-color: #2196F3;
                    color: white;
                    font-weight: bold;
                    font-size: 16px;
                }
            """)
            self.step_label.setText(str(self.step_number))
            self.title_label.setStyleSheet("color: #2196F3; font-weight: bold;")
        else:
            self.step_label.setStyleSheet("""
                QLabel {
                    border: 2px solid #ccc;
                    border-radius: 20px;
                    background-color: #f0f0f0;
                    color: #666;
                    font-weight: bold;
                    font-size: 16px;
                }
            """)
            self.step_label.setText(str(self.step_number))
            self.title_label.setStyleSheet("color: #333;")


class LoadCellCalibrationGUI(QMainWindow):
    # Add signals for thread-safe logging and step updates
    log_signal = Signal(str)
    step_update_signal = Signal(int, str)  # step number, message
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Load Cell Calibration Wizard")
        self.setGeometry(100, 100, 1200, 800)
        
        # Serial connection variables
        self.serial_worker = None
        self.serial_thread = None
        self.is_connected = False
        self.current_calibration_factor = 1.0
        
        # Step tracking
        self.current_step = 1
        
        # Initialize logger
        log_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs", "logs.txt")
        self.logger = Logger(log_file_path)
        self.logger.log_step("Application started")
        
        # Default file paths
        self.calibration_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "calibration", "calibration.ino")
        self.firmware_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "firmware", "firmware.ino")
        
        self.logger.log(f"Calibration file path: {self.calibration_file}")
        self.logger.log(f"Firmware file path: {self.firmware_file}")
        
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
        """Setup the user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        
        # Title
        title_label = QLabel("Load Cell Calibration Wizard")
        title_label.setFont(QFont("Arial", 18, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("QLabel { color: #2196F3; margin: 10px; }")
        main_layout.addWidget(title_label)
        
        # Create splitter for resizable panels
        splitter = QSplitter()
        main_layout.addWidget(splitter)
        
        # Left panel - Steps and Controls
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # Progress Steps
        steps_group = QGroupBox("Progress")
        steps_layout = QVBoxLayout(steps_group)
        
        self.step1 = StepIndicator(1, "Upload Calibration Code", "Upload calibration.ino to Arduino")
        self.step2 = StepIndicator(2, "Calibrate Load Cell", "Run calibration process and get factor")
        self.step3 = StepIndicator(3, "Upload Final Firmware", "Upload firmware.ino with calibration factor")
        
        steps_layout.addWidget(self.step1)
        steps_layout.addWidget(self.step2)
        steps_layout.addWidget(self.step3)
        
        left_layout.addWidget(steps_group)
        
        # Connection Settings
        connection_group = QGroupBox("Connection Settings")
        connection_layout = QVBoxLayout(connection_group)
        
        # Port selection
        port_layout = QHBoxLayout()
        port_layout.addWidget(QLabel("Port:"))
        self.port_combo = QComboBox()
        self.refresh_ports_button = QPushButton("Refresh")
        self.refresh_ports_button.clicked.connect(self.refresh_ports)
        port_layout.addWidget(self.port_combo)
        port_layout.addWidget(self.refresh_ports_button)
        connection_layout.addLayout(port_layout)
        
        # Board selection
        board_layout = QHBoxLayout()
        board_layout.addWidget(QLabel("Board:"))
        self.board_combo = QComboBox()
        self.board_combo.addItems([
            "arduino:avr:uno", 
            "arduino:avr:nano", 
            "arduino:mbed_nano:nano33ble",
            "arduino:mbed_nano:nanorp2040connect",
            "esp32:esp32:esp32",
            "teensy:avr:teensy41"
        ])
        self.board_combo.setCurrentText("arduino:mbed_nano:nano33ble")
        board_layout.addWidget(self.board_combo)
        connection_layout.addLayout(board_layout)
        
        # Baudrate
        baudrate_layout = QHBoxLayout()
        baudrate_layout.addWidget(QLabel("Baudrate:"))
        self.baudrate_spin = QSpinBox()
        self.baudrate_spin.setRange(9600, 2000000)
        self.baudrate_spin.setValue(115200)
        baudrate_layout.addWidget(self.baudrate_spin)
        connection_layout.addLayout(baudrate_layout)
        
        left_layout.addWidget(connection_group)
        
        # Step 1: Upload Calibration
        self.step1_group = QGroupBox("Step 1: Upload Calibration Code")
        step1_layout = QVBoxLayout(self.step1_group)
        
        # File display
        cal_file_layout = QHBoxLayout()
        cal_file_layout.addWidget(QLabel("File:"))
        self.cal_file_label = QLabel(self.calibration_file)
        self.cal_file_label.setStyleSheet("QLabel { background: #f0f0f0; padding: 5px; border: 1px solid #ccc; }")
        cal_file_layout.addWidget(self.cal_file_label)
        step1_layout.addLayout(cal_file_layout)
        
        self.upload_cal_button = QPushButton("Upload Calibration Code")
        self.upload_cal_button.setStyleSheet("QPushButton { background: #2196F3; color: white; padding: 10px; font-weight: bold; }")
        self.upload_cal_button.clicked.connect(self.upload_calibration_code)
        step1_layout.addWidget(self.upload_cal_button)
        
        left_layout.addWidget(self.step1_group)
        
        # Step 2: Calibration
        self.step2_group = QGroupBox("Step 2: Calibrate Load Cell")
        step2_layout = QVBoxLayout(self.step2_group)
        
        # Connection button
        self.connect_button = QPushButton("Connect to Serial")
        self.connect_button.clicked.connect(self.toggle_connection)
        step2_layout.addWidget(self.connect_button)
        
        # Current calibration factor display
        self.cal_factor_label = QLabel("Calibration Factor: Not set")
        self.cal_factor_label.setFont(QFont("Arial", 12, QFont.Bold))
        self.cal_factor_label.setStyleSheet("QLabel { background: #fff3cd; padding: 10px; border: 1px solid #ffeaa7; }")
        step2_layout.addWidget(self.cal_factor_label)
        
        # Known mass input
        mass_layout = QHBoxLayout()
        mass_layout.addWidget(QLabel("Known Mass (g):"))
        self.known_mass_spin = QDoubleSpinBox()
        self.known_mass_spin.setRange(0.1, 10000.0)
        self.known_mass_spin.setValue(100.0)
        self.known_mass_spin.setDecimals(1)
        mass_layout.addWidget(self.known_mass_spin)
        step2_layout.addLayout(mass_layout)
        
        # Calibration buttons
        cal_buttons_layout = QHBoxLayout()
        
        self.tare_button = QPushButton("Tare (t)")
        self.tare_button.clicked.connect(self.send_tare)
        self.tare_button.setEnabled(False)
        cal_buttons_layout.addWidget(self.tare_button)
        
        self.calibrate_button = QPushButton("Start Calibration (r)")
        self.calibrate_button.clicked.connect(self.start_calibration)
        self.calibrate_button.setEnabled(False)
        cal_buttons_layout.addWidget(self.calibrate_button)
        
        self.send_mass_button = QPushButton("Send Known Mass")
        self.send_mass_button.clicked.connect(self.send_known_mass)
        self.send_mass_button.setEnabled(False)
        cal_buttons_layout.addWidget(self.send_mass_button)
        
        step2_layout.addLayout(cal_buttons_layout)
        
        left_layout.addWidget(self.step2_group)
        
        # Step 3: Upload Firmware
        self.step3_group = QGroupBox("Step 3: Upload Final Firmware")
        step3_layout = QVBoxLayout(self.step3_group)
        
        # File display
        firm_file_layout = QHBoxLayout()
        firm_file_layout.addWidget(QLabel("File:"))
        self.firm_file_label = QLabel(self.firmware_file)
        self.firm_file_label.setStyleSheet("QLabel { background: #f0f0f0; padding: 5px; border: 1px solid #ccc; }")
        firm_file_layout.addWidget(self.firm_file_label)
        step3_layout.addLayout(firm_file_layout)
        
        self.update_firmware_button = QPushButton("Update Firmware with Cal Factor")
        self.update_firmware_button.clicked.connect(self.update_firmware_code)
        self.update_firmware_button.setEnabled(False)
        step3_layout.addWidget(self.update_firmware_button)
        
        self.upload_firmware_button = QPushButton("Upload Final Firmware")
        self.upload_firmware_button.setStyleSheet("QPushButton { background: #4CAF50; color: white; padding: 10px; font-weight: bold; }")
        self.upload_firmware_button.clicked.connect(self.upload_firmware_code)
        self.upload_firmware_button.setEnabled(False)
        step3_layout.addWidget(self.upload_firmware_button)
        
        left_layout.addWidget(self.step3_group)
        
        # Progress bar (shared)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        left_layout.addWidget(self.progress_bar)
        
        # Add stretch to push everything to top
        left_layout.addStretch()
        
        # Right panel - Serial Monitor
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        monitor_group = QGroupBox("Serial Monitor")
        monitor_layout = QVBoxLayout(monitor_group)
        
        # Serial output display
        self.serial_output = QTextEdit()
        self.serial_output.setReadOnly(True)
        self.serial_output.setFont(QFont("Courier", 10))
        monitor_layout.addWidget(self.serial_output)
        
        # Clear button
        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self.clear_serial_output)
        monitor_layout.addWidget(self.clear_button)
        
        right_layout.addWidget(monitor_group)
        
        # Add panels to splitter
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([400, 800])  # Set initial sizes
        
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
            import re
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
            arduino_cli_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "arduino-cli.exe")
            
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
                    self.log_signal.emit(self.logger.log_upload("Core installation check complete"))
                else:
                    self.log_signal.emit(self.logger.log_warning(f"Core install result: {result.stderr}"))
            
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
            else:
                self.log_signal.emit(self.logger.log_error(f"{upload_type.title()} compilation failed: {result.stderr}"))
                
        except Exception as e:
            self.log_signal.emit(self.logger.log_error(f"{upload_type.title()} upload error: {str(e)}"))
        finally:
            # Hide progress bar and re-enable button
            self.progress_bar.setVisible(False)
            if upload_type == "calibration":
                self.upload_cal_button.setEnabled(True)
            else:
                self.upload_firmware_button.setEnabled(True)
            
    def refresh_ports(self):
        """Refresh available serial ports"""
        self.logger.log("Refreshing serial ports")
        self.port_combo.clear()
        ports = serial.tools.list_ports.comports()
        
        # Add debug information
        ports_msg = f"Found {len(ports)} serial ports"
        ui_message = self.logger.log(ports_msg)
        self.log_message_to_ui(ui_message)
        
        for port in ports:
            port_info = f"{port.device}"
            if port.description:
                port_info += f" - {port.description}"
            if port.manufacturer:
                port_info += f" ({port.manufacturer})"
                
            self.port_combo.addItem(port.device)
            port_log = f"  {port_info}"
            ui_message = self.logger.log(port_log)
            self.log_message_to_ui(ui_message)
            
            # Auto-select COM10 if available
            if port.device == "COM10":
                self.port_combo.setCurrentText("COM10")
                ui_message = self.logger.log("Auto-selected COM10")
                self.log_message_to_ui(ui_message)
        
        if len(ports) == 0:
            ui_message = self.logger.log_warning("No serial ports detected!")
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
        
    def log_message(self, message):
        """Legacy method for compatibility - logs to both file and UI"""
        ui_message = self.logger.log(message)
        self.log_message_to_ui(ui_message)
        
    def clear_serial_output(self):
        """Clear serial output"""
        self.logger.log("Serial output cleared by user")
        self.serial_output.clear()
        
    def update_display(self):
        """Update display periodically"""
        pass
        
    def closeEvent(self, event):
        """Handle application close"""
        self.logger.log_step("Application closing")
        if self.is_connected:
            self.disconnect_serial()
        
        # Write session end
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        footer = f"\n{'='*60}\nSESSION END: {timestamp}\n{'='*60}\n"
        self.logger.write_to_file(footer)
        
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = LoadCellCalibrationGUI()
    window.show()
    sys.exit(app.exec())