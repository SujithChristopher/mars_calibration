import sys
import os
import subprocess
import threading
import time
import serial
import serial.tools.list_ports
from PySide6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                               QWidget, QPushButton, QLabel, QLineEdit, QTextEdit, 
                               QComboBox, QGroupBox, QSpinBox, QDoubleSpinBox,
                               QMessageBox, QProgressBar, QSplitter)
from PySide6.QtCore import QTimer, Signal, QObject, QThread
from PySide6.QtGui import QFont, QTextCursor


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


class LoadCellCalibrationGUI(QMainWindow):
    # Add signal for thread-safe logging
    log_signal = Signal(str)
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Load Cell Calibration Tool")
        self.setGeometry(100, 100, 1000, 700)
        
        # Serial connection variables
        self.serial_worker = None
        self.serial_thread = None
        self.is_connected = False
        self.current_calibration_factor = 1.0
        
        # Connect log signal to log method
        self.log_signal.connect(self.log_message)
        
        # Setup UI
        self.setup_ui()
        self.refresh_ports()
        
        # Timer for periodic updates
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_display)
        
    def setup_ui(self):
        """Setup the user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        
        # Create splitter for resizable panels
        splitter = QSplitter()
        main_layout.addWidget(splitter)
        
        # Left panel - Controls
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # Arduino Programming Section
        arduino_group = QGroupBox("Arduino Programming")
        arduino_layout = QVBoxLayout(arduino_group)
        
        # Arduino file selection
        file_layout = QHBoxLayout()
        self.arduino_file_edit = QLineEdit()
        self.arduino_file_edit.setPlaceholderText("Select Arduino .ino file...")
        self.browse_button = QPushButton("Browse")
        self.browse_button.clicked.connect(self.browse_arduino_file)
        file_layout.addWidget(self.arduino_file_edit)
        file_layout.addWidget(self.browse_button)
        arduino_layout.addLayout(file_layout)
        
        # Board selection
        board_layout = QHBoxLayout()
        board_layout.addWidget(QLabel("Board:"))
        self.board_combo = QComboBox()
        self.board_combo.addItems([
            "arduino:avr:uno", 
            "arduino:avr:nano", 
            "arduino:mbed_nano:nano33ble",
            "arduino:mbed_nano:nanorp2040connect",
            "esp32:esp32:esp32"
        ])
        # Set Nano 33 BLE as default
        self.board_combo.setCurrentText("arduino:mbed_nano:nano33ble")
        board_layout.addWidget(self.board_combo)
        arduino_layout.addLayout(board_layout)
        
        # Upload button
        self.upload_button = QPushButton("Upload to Arduino")
        self.upload_button.clicked.connect(self.upload_arduino_code)
        arduino_layout.addWidget(self.upload_button)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        arduino_layout.addWidget(self.progress_bar)
        
        left_layout.addWidget(arduino_group)
        
        # Serial Connection Section
        serial_group = QGroupBox("Serial Connection")
        serial_layout = QVBoxLayout(serial_group)
        
        # Port selection
        port_layout = QHBoxLayout()
        port_layout.addWidget(QLabel("Port:"))
        self.port_combo = QComboBox()
        self.refresh_ports_button = QPushButton("Refresh")
        self.refresh_ports_button.clicked.connect(self.refresh_ports)
        port_layout.addWidget(self.port_combo)
        port_layout.addWidget(self.refresh_ports_button)
        serial_layout.addLayout(port_layout)
        
        # Baudrate selection
        baudrate_layout = QHBoxLayout()
        baudrate_layout.addWidget(QLabel("Baudrate:"))
        self.baudrate_spin = QSpinBox()
        self.baudrate_spin.setRange(9600, 2000000)
        self.baudrate_spin.setValue(115200)
        baudrate_layout.addWidget(self.baudrate_spin)
        serial_layout.addLayout(baudrate_layout)
        
        # Connection button
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.toggle_connection)
        serial_layout.addWidget(self.connect_button)
        
        left_layout.addWidget(serial_group)
        
        # Calibration Section
        calibration_group = QGroupBox("Calibration")
        calibration_layout = QVBoxLayout(calibration_group)
        
        # Current calibration factor display
        self.cal_factor_label = QLabel("Calibration Factor: 1.0")
        self.cal_factor_label.setFont(QFont("Arial", 12, QFont.Bold))
        calibration_layout.addWidget(self.cal_factor_label)
        
        # Known mass input
        mass_layout = QHBoxLayout()
        mass_layout.addWidget(QLabel("Known Mass (g):"))
        self.known_mass_spin = QDoubleSpinBox()
        self.known_mass_spin.setRange(0.1, 10000.0)
        self.known_mass_spin.setValue(100.0)
        self.known_mass_spin.setDecimals(1)
        mass_layout.addWidget(self.known_mass_spin)
        calibration_layout.addLayout(mass_layout)
        
        # Control buttons
        button_layout = QVBoxLayout()
        
        self.tare_button = QPushButton("Tare (t)")
        self.tare_button.clicked.connect(self.send_tare)
        self.tare_button.setEnabled(False)
        button_layout.addWidget(self.tare_button)
        
        self.calibrate_button = QPushButton("Start Calibration (r)")
        self.calibrate_button.clicked.connect(self.start_calibration)
        self.calibrate_button.setEnabled(False)
        button_layout.addWidget(self.calibrate_button)
        
        self.send_mass_button = QPushButton("Send Known Mass")
        self.send_mass_button.clicked.connect(self.send_known_mass)
        self.send_mass_button.setEnabled(False)
        button_layout.addWidget(self.send_mass_button)
        
        calibration_layout.addLayout(button_layout)
        
        left_layout.addWidget(calibration_group)
        
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
        splitter.setSizes([300, 700])  # Set initial sizes
        
    def browse_arduino_file(self):
        """Browse for Arduino .ino file"""
        from PySide6.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Arduino File", "", "Arduino Files (*.ino)")
        if file_path:
            self.arduino_file_edit.setText(file_path)
            
    def upload_arduino_code(self):
        """Upload Arduino code using arduino-cli"""
        if not self.arduino_file_edit.text():
            QMessageBox.warning(self, "Warning", "Please select an Arduino file first!")
            return
            
        if not self.port_combo.currentText():
            QMessageBox.warning(self, "Warning", "Please select a port first!")
            return
            
        # Disconnect serial if connected (prevents port conflicts)
        if self.is_connected:
            self.log_message("Disconnecting serial for upload...")
            self.disconnect_serial()
            time.sleep(1)  # Give time for port to be released
            
        # Show progress bar
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.upload_button.setEnabled(False)
        
        # Capture current selections before starting thread
        selected_port = self.port_combo.currentText()
        selected_board = self.board_combo.currentText()
        selected_file = self.arduino_file_edit.text()
        
        self.log_message(f"Starting upload to {selected_port}")
        
        # Run upload in separate thread
        threading.Thread(target=self._upload_thread, args=(selected_file, selected_board, selected_port), daemon=True).start()
        
    def _upload_thread(self, sketch_path, board, port):
        """Upload thread function"""
        try:
            self.log_signal.emit(f"Upload parameters:")
            self.log_signal.emit(f"  File: {sketch_path}")
            self.log_signal.emit(f"  Board: {board}")
            self.log_signal.emit(f"  Port: {port}")
            
            # Use local arduino-cli.exe
            arduino_cli_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "arduino-cli.exe")
            
            # Check if local arduino-cli.exe exists
            if not os.path.exists(arduino_cli_path):
                self.log_signal.emit("arduino-cli.exe not found in program directory!")
                self.log_signal.emit("Please place arduino-cli.exe in the same folder as this program.")
                return
            
            # Install required cores if needed
            if "mbed_nano" in board:
                self.log_signal.emit("Checking Arduino Nano core installation...")
                core_install_cmd = f'"{arduino_cli_path}" core install arduino:mbed_nano'
                result = subprocess.run(core_install_cmd, shell=True, capture_output=True, text=True)
                if result.returncode == 0:
                    self.log_signal.emit("Core installation check complete")
                else:
                    self.log_signal.emit(f"Core install result: {result.stderr}")
            
            # Compile command
            compile_cmd = f'"{arduino_cli_path}" compile --fqbn {board} "{sketch_path}"'
            
            # Upload command - explicitly specify the port
            upload_cmd = f'"{arduino_cli_path}" upload -p {port} --fqbn {board} "{sketch_path}"'
            
            # Execute commands
            self.log_signal.emit("Compiling sketch...")
            self.log_signal.emit(f"Using: {arduino_cli_path}")
            self.log_signal.emit(f"Compile command: {compile_cmd}")
            
            result = subprocess.run(compile_cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                self.log_signal.emit("Compilation successful!")
                self.log_signal.emit(f"Uploading to {port}...")
                self.log_signal.emit(f"Upload command: {upload_cmd}")
                
                result = subprocess.run(upload_cmd, shell=True, capture_output=True, text=True)
                
                if result.returncode == 0:
                    self.log_signal.emit("Upload successful!")
                    self.log_signal.emit(f"Arduino programmed on {port}")
                else:
                    self.log_signal.emit(f"Upload failed: {result.stderr}")
                    self.log_signal.emit(f"Upload stdout: {result.stdout}")
                    if "mbed_nano" in board:
                        self.log_signal.emit("Note: Make sure to double-press the reset button on Nano 33 BLE to enter bootloader mode")
            else:
                self.log_signal.emit(f"Compilation failed: {result.stderr}")
                self.log_signal.emit(f"Compile stdout: {result.stdout}")
                if "mbed_nano" in board and "core not installed" in result.stderr.lower():
                    self.log_signal.emit("Installing Arduino Nano core...")
                    core_result = subprocess.run(f'"{arduino_cli_path}" core install arduino:mbed_nano', 
                                               shell=True, capture_output=True, text=True)
                    if core_result.returncode == 0:
                        self.log_signal.emit("Core installed. Please try uploading again.")
                    else:
                        self.log_signal.emit(f"Failed to install core automatically. Please run: {arduino_cli_path} core install arduino:mbed_nano")
                
        except Exception as e:
            self.log_signal.emit(f"Upload error: {str(e)}")
        finally:
            # Hide progress bar and re-enable button
            self.progress_bar.setVisible(False)
            self.upload_button.setEnabled(True)
            
    def refresh_ports(self):
        """Refresh available serial ports"""
        self.port_combo.clear()
        ports = serial.tools.list_ports.comports()
        
        # Add debug information
        self.log_message(f"Found {len(ports)} serial ports:")
        
        for port in ports:
            port_info = f"{port.device}"
            if port.description:
                port_info += f" - {port.description}"
            if port.manufacturer:
                port_info += f" ({port.manufacturer})"
                
            self.port_combo.addItem(port.device)
            self.log_message(f"  {port_info}")
            
            # Auto-select COM10 if available
            if port.device == "COM10":
                self.port_combo.setCurrentText("COM10")
                self.log_message(f"Auto-selected COM10")
        
        if len(ports) == 0:
            self.log_message("No serial ports detected!")
        
        # Test if COM10 specifically exists
        try:
            test_port = serial.Serial("COM10", 115200, timeout=0.1)
            test_port.close()
            self.log_message("COM10 is available and accessible")
        except Exception as e:
            self.log_message(f"COM10 test failed: {str(e)}")
            
    def toggle_connection(self):
        """Connect or disconnect from serial port"""
        if not self.is_connected:
            self.connect_serial()
        else:
            self.disconnect_serial()
            
    def connect_serial(self):
        """Connect to serial port"""
        if not self.port_combo.currentText():
            QMessageBox.warning(self, "Warning", "Please select a port!")
            return
            
        try:
            # Create worker thread
            self.serial_thread = QThread()
            self.serial_worker = SerialWorker(
                self.port_combo.currentText(), 
                self.baudrate_spin.value()
            )
            self.serial_worker.moveToThread(self.serial_thread)
            
            # Connect signals
            self.serial_worker.data_received.connect(self.handle_serial_data)
            self.serial_worker.connection_lost.connect(self.handle_connection_lost)
            self.serial_thread.started.connect(self.serial_worker.start_connection)
            
            # Start thread
            self.serial_thread.start()
            
            # Update UI
            self.is_connected = True
            self.connect_button.setText("Disconnect")
            self.tare_button.setEnabled(True)
            self.calibrate_button.setEnabled(True)
            self.send_mass_button.setEnabled(True)
            
            self.log_message(f"Connected to {self.port_combo.currentText()}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Connection failed: {str(e)}")
            
    def disconnect_serial(self):
        """Disconnect from serial port"""
        if self.serial_worker:
            self.serial_worker.stop_connection()
        if self.serial_thread:
            self.serial_thread.quit()
            self.serial_thread.wait()
            
        self.is_connected = False
        self.connect_button.setText("Connect")
        self.tare_button.setEnabled(False)
        self.calibrate_button.setEnabled(False)
        self.send_mass_button.setEnabled(False)
        
        self.log_message("Disconnected")
        
    def handle_serial_data(self, data):
        """Handle incoming serial data"""
        self.log_message(f"Arduino: {data}")
        
        # Check for calibration factor in the data
        if "calibration value has been set to:" in data.lower():
            try:
                # Extract calibration factor
                parts = data.split(":")
                if len(parts) > 1:
                    cal_factor = float(parts[1].split(",")[0].strip())
                    self.current_calibration_factor = cal_factor
                    self.cal_factor_label.setText(f"Calibration Factor: {cal_factor:.2f}")
            except:
                pass
                
    def handle_connection_lost(self):
        """Handle lost connection"""
        self.disconnect_serial()
        QMessageBox.warning(self, "Warning", "Connection lost!")
        
    def send_tare(self):
        """Send tare command"""
        if self.serial_worker:
            self.serial_worker.send_data("t")
            self.log_message("Sent: t (tare)")
            
    def start_calibration(self):
        """Start calibration process"""
        if self.serial_worker:
            self.serial_worker.send_data("r")
            self.log_message("Sent: r (start calibration)")
            
    def send_known_mass(self):
        """Send known mass value"""
        if self.serial_worker:
            mass = self.known_mass_spin.value()
            self.serial_worker.send_data(f"{mass}\n")
            self.log_message(f"Sent: {mass} (known mass)")
            
    def log_message(self, message):
        """Add message to serial output"""
        timestamp = time.strftime("%H:%M:%S")
        self.serial_output.append(f"[{timestamp}] {message}")
        
        # Auto-scroll to bottom
        cursor = self.serial_output.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.serial_output.setTextCursor(cursor)
        
    def clear_serial_output(self):
        """Clear serial output"""
        self.serial_output.clear()
        
    def update_display(self):
        """Update display periodically"""
        pass
        
    def closeEvent(self, event):
        """Handle application close"""
        if self.is_connected:
            self.disconnect_serial()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = LoadCellCalibrationGUI()
    window.show()
    sys.exit(app.exec())