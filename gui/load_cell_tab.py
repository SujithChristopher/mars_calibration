"""
Load Cell calibration tab UI components.
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QSplitter, 
                               QGroupBox, QLabel, QPushButton, QComboBox, 
                               QSpinBox, QDoubleSpinBox, QTextEdit, QProgressBar, QLineEdit)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QIntValidator

from gui.widgets.step_indicator import StepIndicator


def setup_load_cell_tab(main_window):
    """Setup Load Cell calibration tab"""
    # Create tab widget
    load_cell_tab = QWidget()
    main_window.tab_widget.addTab(load_cell_tab, "Load Cell Calibration")
    
    # Create splitter for resizable panels
    splitter = QSplitter()
    tab_layout = QVBoxLayout(load_cell_tab)
    tab_layout.addWidget(splitter)
    
    # Left panel - Steps and Controls
    left_panel = QWidget()
    left_layout = QVBoxLayout(left_panel)
    
    # Progress Steps
    steps_group = QGroupBox("Progress")
    steps_layout = QVBoxLayout(steps_group)
    
    main_window.step1 = StepIndicator(1, "Upload Unified Calibration", "Upload calibration.ino (supports both Load Cell & IMU)")
    main_window.step2 = StepIndicator(2, "Calibrate & Save", "Run calibration process and save factor")
    
    steps_layout.addWidget(main_window.step1)
    steps_layout.addWidget(main_window.step2)
    
    left_layout.addWidget(steps_group)
    
    # Mars ID Settings
    mars_id_group = QGroupBox("Mars Device ID")
    mars_id_layout = QVBoxLayout(mars_id_group)
    
    mars_id_input_layout = QHBoxLayout()
    mars_id_input_layout.addWidget(QLabel("Mars ID:"))
    main_window.mars_id_input = QLineEdit()
    main_window.mars_id_input.setPlaceholderText("Enter Mars device ID (e.g., 1, 42, 123)")
    
    # Set integer validator for non-negative integers
    int_validator = QIntValidator(0, 9999)
    main_window.mars_id_input.setValidator(int_validator)
    main_window.mars_id_input.setMaxLength(4)
    
    def on_mars_id_changed():
        mars_id = main_window.mars_id_input.text().strip()
        if mars_id:
            is_valid, error_msg = main_window.validate_mars_id(mars_id)
            if is_valid:
                main_window.set_mars_id(mars_id)
                main_window.mars_id_input.setStyleSheet("QLineEdit { background: #e8f5e8; }")
            else:
                main_window.mars_id_input.setStyleSheet("QLineEdit { background: #ffe8e8; }")
                main_window.mars_id_input.setToolTip(error_msg)
        else:
            main_window.mars_id_input.setStyleSheet("")
            main_window.mars_id_input.setToolTip("")
    
    main_window.mars_id_input.textChanged.connect(on_mars_id_changed)
    mars_id_input_layout.addWidget(main_window.mars_id_input)
    mars_id_layout.addLayout(mars_id_input_layout)
    
    mars_id_info = QLabel("💡 This ID will be used in all tabs and saved with calibration data")
    mars_id_info.setStyleSheet("QLabel { color: #666; font-size: 10px; }")
    mars_id_layout.addWidget(mars_id_info)
    
    left_layout.addWidget(mars_id_group)
    
    # Connection Settings
    connection_group = QGroupBox("Connection Settings")
    connection_layout = QVBoxLayout(connection_group)
    
    # Port selection
    port_layout = QHBoxLayout()
    port_layout.addWidget(QLabel("Port:"))
    main_window.port_combo = QComboBox()
    main_window.refresh_ports_button = QPushButton("Refresh")
    main_window.refresh_ports_button.clicked.connect(main_window.refresh_ports)
    port_layout.addWidget(main_window.port_combo)
    port_layout.addWidget(main_window.refresh_ports_button)
    connection_layout.addLayout(port_layout)
    
    # Board selection
    board_layout = QHBoxLayout()
    board_layout.addWidget(QLabel("Board:"))
    main_window.board_combo = QComboBox()
    main_window.board_combo.addItems([
        "arduino:avr:uno", 
        "arduino:avr:nano", 
        "arduino:mbed_nano:nano33ble",
        "arduino:mbed_nano:nanorp2040connect",
        "teensy:avr:teensy41",
        "esp32:esp32:esp32"
    ])
    # Set Nano 33 BLE as default for IMU compatibility
    main_window.board_combo.setCurrentText("arduino:mbed_nano:nano33ble")
    board_layout.addWidget(main_window.board_combo)
    connection_layout.addLayout(board_layout)
    
    # Baudrate
    baudrate_layout = QHBoxLayout()
    baudrate_layout.addWidget(QLabel("Baudrate:"))
    main_window.baudrate_spin = QSpinBox()
    main_window.baudrate_spin.setRange(9600, 2000000)
    main_window.baudrate_spin.setValue(115200)
    baudrate_layout.addWidget(main_window.baudrate_spin)
    connection_layout.addLayout(baudrate_layout)
    
    left_layout.addWidget(connection_group)
    
    # Step 1: Upload Unified Calibration
    main_window.step1_group = QGroupBox("Step 1: Upload Unified Calibration Program")
    step1_layout = QVBoxLayout(main_window.step1_group)
    
    # File display
    cal_file_layout = QHBoxLayout()
    cal_file_layout.addWidget(QLabel("File:"))
    main_window.cal_file_label = QLabel("calibration.ino (Load Cell + IMU)")
    main_window.cal_file_label.setStyleSheet("QLabel { background: #f0f0f0; padding: 5px; border: 1px solid #ccc; }")
    cal_file_layout.addWidget(main_window.cal_file_label)
    step1_layout.addLayout(cal_file_layout)
    
    main_window.upload_cal_button = QPushButton("Upload Unified Calibration")
    main_window.upload_cal_button.setStyleSheet("QPushButton { background: #2196F3; color: white; padding: 10px; font-weight: bold; }")
    main_window.upload_cal_button.clicked.connect(main_window.upload_calibration_code)
    step1_layout.addWidget(main_window.upload_cal_button)
    
    left_layout.addWidget(main_window.step1_group)
    
    # Step 2: Calibration
    main_window.step2_group = QGroupBox("Step 2: Calibrate Load Cell")
    step2_layout = QVBoxLayout(main_window.step2_group)
    
    # Connection button
    main_window.connect_button = QPushButton("Connect to Serial")
    main_window.connect_button.clicked.connect(main_window.toggle_connection)
    step2_layout.addWidget(main_window.connect_button)
    
    # Current calibration factor display
    main_window.cal_factor_label = QLabel("Calibration Factor: Not set")
    main_window.cal_factor_label.setFont(QFont("Arial", 12, QFont.Bold))
    main_window.cal_factor_label.setStyleSheet("QLabel { background: #fff3cd; padding: 10px; border: 1px solid #ffeaa7; }")
    step2_layout.addWidget(main_window.cal_factor_label)
    
    # Known mass input
    mass_layout = QHBoxLayout()
    mass_layout.addWidget(QLabel("Known Mass (g):"))
    main_window.known_mass_spin = QDoubleSpinBox()
    main_window.known_mass_spin.setRange(0.1, 10000.0)
    main_window.known_mass_spin.setValue(100.0)
    main_window.known_mass_spin.setDecimals(1)
    mass_layout.addWidget(main_window.known_mass_spin)
    step2_layout.addLayout(mass_layout)
    
    # Calibration buttons
    cal_buttons_layout = QHBoxLayout()
    
    main_window.tare_button = QPushButton("Tare (t)")
    main_window.tare_button.clicked.connect(main_window.send_tare)
    main_window.tare_button.setEnabled(False)
    cal_buttons_layout.addWidget(main_window.tare_button)
    
    main_window.calibrate_button = QPushButton("Start Calibration (r)")
    main_window.calibrate_button.clicked.connect(main_window.start_calibration)
    main_window.calibrate_button.setEnabled(False)
    cal_buttons_layout.addWidget(main_window.calibrate_button)
    
    main_window.send_mass_button = QPushButton("Send Known Mass")
    main_window.send_mass_button.clicked.connect(main_window.send_known_mass)
    main_window.send_mass_button.setEnabled(False)
    cal_buttons_layout.addWidget(main_window.send_mass_button)
    
    step2_layout.addLayout(cal_buttons_layout)
    
    left_layout.addWidget(main_window.step2_group)
    
    # Calibration Status
    main_window.calibration_status_group = QGroupBox("Calibration Status")
    status_layout = QVBoxLayout(main_window.calibration_status_group)
    
    # Status message
    main_window.calibration_status_label = QLabel("No calibration completed yet.")
    main_window.calibration_status_label.setStyleSheet("""
    QLabel { 
        background: palette(base); 
        color: palette(text); 
        padding: 15px; 
        border: 2px solid palette(mid); 
        border-radius: 8px;
        font-weight: bold;
        font-size: 11pt;
    }
    """)
    main_window.calibration_status_label.setAlignment(Qt.AlignCenter)
    status_layout.addWidget(main_window.calibration_status_label)
    
    left_layout.addWidget(main_window.calibration_status_group)
    
    # Progress bar (shared)
    main_window.progress_bar = QProgressBar()
    main_window.progress_bar.setVisible(False)
    left_layout.addWidget(main_window.progress_bar)
    
    # Add stretch to push everything to top
    left_layout.addStretch()
    
    # Right panel - Serial Monitor
    right_panel = QWidget()
    right_layout = QVBoxLayout(right_panel)
    
    monitor_group = QGroupBox("Serial Monitor")
    monitor_layout = QVBoxLayout(monitor_group)
    
    # Serial output display
    main_window.serial_output = QTextEdit()
    main_window.serial_output.setReadOnly(True)
    main_window.serial_output.setFont(QFont("Courier", 10))
    monitor_layout.addWidget(main_window.serial_output)
    
    # Clear button
    main_window.clear_button = QPushButton("Clear")
    main_window.clear_button.clicked.connect(main_window.clear_serial_output)
    monitor_layout.addWidget(main_window.clear_button)
    
    right_layout.addWidget(monitor_group)
    
    # Add panels to splitter
    splitter.addWidget(left_panel)
    splitter.addWidget(right_panel)
    splitter.setSizes([400, 800])  # Set initial sizes