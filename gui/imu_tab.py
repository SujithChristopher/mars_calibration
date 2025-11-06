"""
IMU calibration tab UI components.
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QSplitter, 
                               QGroupBox, QLabel, QPushButton, QComboBox, 
                               QTextEdit, QGridLayout, QLCDNumber, QLineEdit)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor, QIntValidator

from gui.widgets.angle_indicator import AngleIndicator
from gui.widgets.attitude_indicator import AttitudeIndicator


def setup_imu_tab(main_window):
    """Setup IMU calibration tab"""
    # Create tab widget
    imu_tab = QWidget()
    main_window.tab_widget.addTab(imu_tab, "IMU Calibration")
    
    # Create splitter for resizable panels
    splitter = QSplitter()
    tab_layout = QVBoxLayout(imu_tab)
    tab_layout.addWidget(splitter)
    
    # Left panel - Controls and Connection
    left_panel = QWidget()
    left_layout = QVBoxLayout(left_panel)
    
    # Mars ID Settings (synchronized with Load Cell tab)
    imu_mars_id_group = QGroupBox("Mars Device ID")
    imu_mars_id_layout = QVBoxLayout(imu_mars_id_group)
    
    imu_mars_id_input_layout = QHBoxLayout()
    imu_mars_id_input_layout.addWidget(QLabel("Mars ID:"))
    main_window.imu_mars_id_input = QLineEdit()
    main_window.imu_mars_id_input.setPlaceholderText("Enter Mars device ID (e.g., 1, 42, 123)")
    
    # Set integer validator for non-negative integers
    imu_int_validator = QIntValidator(0, 9999)
    main_window.imu_mars_id_input.setValidator(imu_int_validator)
    main_window.imu_mars_id_input.setMaxLength(4)
    
    def on_imu_mars_id_changed():
        mars_id = main_window.imu_mars_id_input.text().strip()
        if mars_id:
            is_valid, error_msg = main_window.validate_mars_id(mars_id)
            if is_valid:
                main_window.set_mars_id(mars_id)
                main_window.imu_mars_id_input.setStyleSheet("QLineEdit { background: #e8f5e8; }")
            else:
                main_window.imu_mars_id_input.setStyleSheet("QLineEdit { background: #ffe8e8; }")
                main_window.imu_mars_id_input.setToolTip(error_msg)
        else:
            main_window.imu_mars_id_input.setStyleSheet("")
            main_window.imu_mars_id_input.setToolTip("")
    
    main_window.imu_mars_id_input.textChanged.connect(on_imu_mars_id_changed)
    imu_mars_id_input_layout.addWidget(main_window.imu_mars_id_input)
    imu_mars_id_layout.addLayout(imu_mars_id_input_layout)
    
    imu_mars_id_info = QLabel("💡 Synchronized with Load Cell tab - same Mars ID applies to both")
    imu_mars_id_info.setStyleSheet("QLabel { color: #666; font-size: 10px; }")
    imu_mars_id_layout.addWidget(imu_mars_id_info)
    
    left_layout.addWidget(imu_mars_id_group)
    
    # IMU Connection Settings
    imu_connection_group = QGroupBox("IMU Connection Settings")
    imu_connection_layout = QVBoxLayout(imu_connection_group)
    
    # Port selection for IMU
    imu_port_layout = QHBoxLayout()
    imu_port_layout.addWidget(QLabel("Port:"))
    main_window.imu_port_combo = QComboBox()
    main_window.refresh_imu_ports_button = QPushButton("Refresh")
    main_window.refresh_imu_ports_button.clicked.connect(main_window.refresh_ports)
    imu_port_layout.addWidget(main_window.imu_port_combo)
    imu_port_layout.addWidget(main_window.refresh_imu_ports_button)
    imu_connection_layout.addLayout(imu_port_layout)
    
    # Board selection for IMU
    imu_board_layout = QHBoxLayout()
    imu_board_layout.addWidget(QLabel("Board:"))
    main_window.imu_board_combo = QComboBox()
    main_window.imu_board_combo.addItems([
        "teensy:avr:teensy41",
        "auto-detect",
        "arduino:mbed_nano:nano33ble",
        "arduino:samd:nano_33_iot",
        "arduino:avr:uno", 
        "arduino:avr:nano", 
        "arduino:mbed_nano:nanorp2040connect"
    ])
    # Set Teensy 4.1 as default
    main_window.imu_board_combo.setCurrentText("teensy:avr:teensy41")
    imu_board_layout.addWidget(main_window.imu_board_combo)
    imu_connection_layout.addLayout(imu_board_layout)
    
    left_layout.addWidget(imu_connection_group)
    
    # Unified Calibration Upload Section
    imu_upload_group = QGroupBox("Upload Unified Calibration Program")
    imu_upload_layout = QVBoxLayout(imu_upload_group)
    
    # Unified Calibration File display
    imu_file_layout = QHBoxLayout()
    imu_file_layout.addWidget(QLabel("File:"))
    main_window.imu_file_label = QLabel("calibration.ino (Load Cell + IMU)")
    main_window.imu_file_label.setStyleSheet("""
    QLabel { 
        background: palette(base); 
        padding: 8px; 
        border: 2px solid palette(mid); 
        border-radius: 4px;
        color: palette(link); 
        font-weight: bold; 
        font-family: 'Consolas', 'Monaco', monospace;
    }
    """)
    imu_file_layout.addWidget(main_window.imu_file_label)
    imu_upload_layout.addLayout(imu_file_layout)
    
    main_window.upload_imu_button = QPushButton("Upload Unified Calibration")
    main_window.upload_imu_button.setStyleSheet("QPushButton { background: #FF9800; color: white; padding: 10px; font-weight: bold; }")
    main_window.upload_imu_button.clicked.connect(main_window.upload_imu_code)
    imu_upload_layout.addWidget(main_window.upload_imu_button)
    
    left_layout.addWidget(imu_upload_group)
    
    # IMU Control Section
    imu_control_group = QGroupBox("Sequential IMU Calibration Controls (4-Offset Formula-Based)")
    imu_control_layout = QVBoxLayout(imu_control_group)

    # Formula-based calibration info
    formula_info = QLabel(
        "Formula-Based Method: Place device FLAT and LEVEL, then calibrate.\n"
        "Offsets calculated using firmware angle formulas.\n"
        "IMU1: Pitch+Roll | IMU2: Roll only | IMU3: Roll only"
    )
    formula_info.setStyleSheet("QLabel { color: #0066cc; font-size: 9px; font-style: italic; padding: 5px; }")
    imu_control_layout.addWidget(formula_info)
    
    # IMU Selection
    imu_selection_layout = QHBoxLayout()
    imu_selection_layout.addWidget(QLabel("Current IMU:"))
    main_window.current_imu_combo = QComboBox()
    # 4-Offset formula-based: IMU1 has pitch+roll, IMU2&3 have roll only
    main_window.current_imu_combo.addItems(["IMU 1 (Pitch+Roll)", "IMU 2 (Roll Only)", "IMU 3 (Roll Only)"])
    main_window.current_imu_combo.currentTextChanged.connect(main_window.on_imu_selection_changed)
    imu_selection_layout.addWidget(main_window.current_imu_combo)
    imu_control_layout.addLayout(imu_selection_layout)
    
    # IMU Connection button
    main_window.imu_connect_button = QPushButton("Connect to IMU")
    main_window.imu_connect_button.clicked.connect(main_window.toggle_imu_connection)
    imu_control_layout.addWidget(main_window.imu_connect_button)
    
    # IMU Control buttons
    imu_buttons_layout = QGridLayout()
    
    main_window.start_imu_cal_button = QPushButton("Calibrate & Save Current IMU")
    main_window.start_imu_cal_button.clicked.connect(main_window.start_imu_calibration)
    main_window.start_imu_cal_button.setEnabled(False)
    main_window.start_imu_cal_button.setStyleSheet("QPushButton { background: #4CAF50; color: white; padding: 10px; font-weight: bold; }")
    imu_buttons_layout.addWidget(main_window.start_imu_cal_button, 0, 0, 1, 2)  # Span 2 columns
    
    imu_control_layout.addLayout(imu_buttons_layout)

    # Saved IMU offsets display (4-Offset Formula-Based)
    saved_offsets_group = QGroupBox("Saved IMU Angle Offsets (4-Offset Formula-Based)")
    saved_offsets_layout = QGridLayout(saved_offsets_group)

    # Theme-adaptive styling for different IMUs with distinct colors
    imu1_style = """
    QLabel {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 palette(highlight), stop:1 palette(base));
        color: palette(highlighted-text);
        padding: 8px;
        border: 2px solid palette(highlight);
        border-radius: 4px;
        font-family: 'Consolas', 'Monaco', monospace;
        font-size: 11pt;
        font-weight: bold;
        min-width: 80px;
    }
    """

    imu2_style = """
    QLabel {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 palette(button), stop:1 palette(base));
        color: palette(button-text);
        padding: 8px;
        border: 2px solid palette(button);
        border-radius: 4px;
        font-family: 'Consolas', 'Monaco', monospace;
        font-size: 11pt;
        font-weight: bold;
        min-width: 80px;
    }
    """

    imu3_style = """
    QLabel {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 palette(mid), stop:1 palette(base));
        color: palette(text);
        padding: 8px;
        border: 2px solid palette(mid);
        border-radius: 4px;
        font-family: 'Consolas', 'Monaco', monospace;
        font-size: 11pt;
        font-weight: bold;
        min-width: 80px;
    }
    """

    # 4-Offset Formula-Based Display
    # Row 0: IMU 1 Pitch + IMU 1 Roll
    saved_offsets_layout.addWidget(QLabel("IMU 1 Pitch:"), 0, 0)
    main_window.angle_offset1_label = QLabel("0.000000")
    main_window.angle_offset1_label.setStyleSheet(imu1_style)
    saved_offsets_layout.addWidget(main_window.angle_offset1_label, 0, 1)

    saved_offsets_layout.addWidget(QLabel("IMU 1 Roll:"), 0, 2)
    main_window.angle_offset2_label = QLabel("0.000000")
    main_window.angle_offset2_label.setStyleSheet(imu1_style)
    saved_offsets_layout.addWidget(main_window.angle_offset2_label, 0, 3)

    # Row 1: IMU 2 Roll + IMU 3 Roll (no pitch, only roll offsets)
    saved_offsets_layout.addWidget(QLabel("IMU 2 Roll:"), 1, 0)
    main_window.angle_offset3_label = QLabel("0.000000")
    main_window.angle_offset3_label.setStyleSheet(imu2_style)
    saved_offsets_layout.addWidget(main_window.angle_offset3_label, 1, 1)

    saved_offsets_layout.addWidget(QLabel("IMU 3 Roll:"), 1, 2)
    main_window.angle_offset4_label = QLabel("0.000000")
    main_window.angle_offset4_label.setStyleSheet(imu3_style)
    saved_offsets_layout.addWidget(main_window.angle_offset4_label, 1, 3)

    # Legacy offset labels (kept for backward compatibility in code but not displayed)
    main_window.angle_offset5_label = QLabel("N/A")
    main_window.angle_offset6_label = QLabel("N/A")
    
    imu_control_layout.addWidget(saved_offsets_group)
    
    left_layout.addWidget(imu_control_group)
    
    # Add stretch to push everything to top
    left_layout.addStretch()
    
    # Right panel - Visualizations and Monitor
    right_panel = QWidget()
    right_layout = QVBoxLayout(right_panel)
    
    # Angle visualizations
    viz_group = QGroupBox("Angle Visualization")
    viz_layout = QVBoxLayout(viz_group)
    
    # Attitude indicator
    attitude_layout = QHBoxLayout()
    main_window.attitude_indicator = AttitudeIndicator()
    attitude_layout.addWidget(main_window.attitude_indicator)
    
    # Individual angle indicators
    angles_layout = QHBoxLayout()
    main_window.roll_indicator = AngleIndicator("Roll", -180, 180, QColor(244, 67, 54))
    main_window.pitch_indicator = AngleIndicator("Pitch", -90, 90, QColor(76, 175, 80))
    main_window.yaw_indicator = AngleIndicator("Yaw", -180, 180, QColor(33, 150, 243))
    
    angles_layout.addWidget(main_window.roll_indicator)
    angles_layout.addWidget(main_window.pitch_indicator)
    angles_layout.addWidget(main_window.yaw_indicator)
    attitude_layout.addLayout(angles_layout)
    
    viz_layout.addLayout(attitude_layout)
    right_layout.addWidget(viz_group)
    
    # IMU Data Display
    data_group = QGroupBox("Raw Accelerometer Data")
    data_layout = QGridLayout(data_group)
    
    # Raw acceleration values with LCD displays - theme adaptive
    data_layout.addWidget(QLabel("AX:"), 0, 0)
    main_window.ax_lcd = QLCDNumber(6)
    main_window.ax_lcd.setDigitCount(6)
    main_window.ax_lcd.setStyleSheet("QLCDNumber { background: palette(highlight); color: palette(highlighted-text); border: 1px solid palette(mid); }")
    data_layout.addWidget(main_window.ax_lcd, 0, 1)
    
    data_layout.addWidget(QLabel("AY:"), 1, 0)
    main_window.ay_lcd = QLCDNumber(6)
    main_window.ay_lcd.setDigitCount(6)
    main_window.ay_lcd.setStyleSheet("QLCDNumber { background: palette(button); color: palette(button-text); border: 1px solid palette(mid); }")
    data_layout.addWidget(main_window.ay_lcd, 1, 1)
    
    data_layout.addWidget(QLabel("AZ:"), 2, 0)
    main_window.az_lcd = QLCDNumber(6)
    main_window.az_lcd.setDigitCount(6)
    main_window.az_lcd.setStyleSheet("QLCDNumber { background: palette(dark); color: palette(bright-text); border: 1px solid palette(mid); }")
    data_layout.addWidget(main_window.az_lcd, 2, 1)
    
    right_layout.addWidget(data_group)
    
    # IMU Serial Monitor
    imu_monitor_group = QGroupBox("IMU Serial Monitor")
    imu_monitor_layout = QVBoxLayout(imu_monitor_group)
    
    # IMU Serial output display
    main_window.imu_serial_output = QTextEdit()
    main_window.imu_serial_output.setReadOnly(True)
    main_window.imu_serial_output.setFont(QFont("Courier", 9))
    main_window.imu_serial_output.setMaximumHeight(200)
    imu_monitor_layout.addWidget(main_window.imu_serial_output)
    
    # Clear IMU button
    main_window.clear_imu_button = QPushButton("Clear IMU Monitor")
    main_window.clear_imu_button.clicked.connect(main_window.clear_imu_output)
    imu_monitor_layout.addWidget(main_window.clear_imu_button)
    
    right_layout.addWidget(imu_monitor_group)
    
    # Add panels to splitter
    splitter.addWidget(left_panel)
    splitter.addWidget(right_panel)
    
    # Set responsive sizes based on screen ratio
    # For 16:10 and 16:9 screens, use proportional sizing
    total_width = 1200  # Default window width
    left_width = int(total_width * 0.35)   # 35% for controls
    right_width = int(total_width * 0.65)  # 65% for visualizations
    splitter.setSizes([left_width, right_width])
    
    # Set minimum sizes to prevent panels from being too small
    left_panel.setMinimumWidth(300)
    right_panel.setMinimumWidth(400)