"""
IMU calibration tab UI components.
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QSplitter, 
                               QGroupBox, QLabel, QPushButton, QComboBox, 
                               QTextEdit, QGridLayout, QLCDNumber)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

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
    
    # IMU Upload Section
    imu_upload_group = QGroupBox("Upload IMU Program")
    imu_upload_layout = QVBoxLayout(imu_upload_group)
    
    # IMU File display
    imu_file_layout = QHBoxLayout()
    imu_file_layout.addWidget(QLabel("File:"))
    main_window.imu_file_label = QLabel("imu_program_teensy.ino (Simulation)")
    main_window.imu_file_label.setStyleSheet("QLabel { background: #f0f0f0; padding: 5px; border: 1px solid #ccc; color: #2196F3; font-weight: bold; }")
    imu_file_layout.addWidget(main_window.imu_file_label)
    imu_upload_layout.addLayout(imu_file_layout)
    
    main_window.upload_imu_button = QPushButton("Upload IMU Program")
    main_window.upload_imu_button.setStyleSheet("QPushButton { background: #FF9800; color: white; padding: 10px; font-weight: bold; }")
    main_window.upload_imu_button.clicked.connect(main_window.upload_imu_code)
    imu_upload_layout.addWidget(main_window.upload_imu_button)
    
    left_layout.addWidget(imu_upload_group)
    
    # IMU Control Section
    imu_control_group = QGroupBox("IMU Calibration Controls")
    imu_control_layout = QVBoxLayout(imu_control_group)
    
    # IMU Connection button
    main_window.imu_connect_button = QPushButton("Connect to IMU")
    main_window.imu_connect_button.clicked.connect(main_window.toggle_imu_connection)
    imu_control_layout.addWidget(main_window.imu_connect_button)
    
    # IMU Control buttons
    imu_buttons_layout = QGridLayout()
    
    main_window.start_imu_cal_button = QPushButton("Start Calibration (c)")
    main_window.start_imu_cal_button.clicked.connect(main_window.start_imu_calibration)
    main_window.start_imu_cal_button.setEnabled(False)
    imu_buttons_layout.addWidget(main_window.start_imu_cal_button, 0, 0)
    
    main_window.reset_imu_offsets_button = QPushButton("Reset Offsets (r)")
    main_window.reset_imu_offsets_button.clicked.connect(main_window.reset_imu_offsets)
    main_window.reset_imu_offsets_button.setEnabled(False)
    imu_buttons_layout.addWidget(main_window.reset_imu_offsets_button, 0, 1)
    
    main_window.update_firmware_button = QPushButton("Update Firmware with Offsets")
    main_window.update_firmware_button.clicked.connect(main_window.update_firmware_with_offsets)
    main_window.update_firmware_button.setEnabled(False)
    imu_buttons_layout.addWidget(main_window.update_firmware_button, 1, 0)
    
    main_window.upload_firmware_button = QPushButton("Upload Updated Firmware")
    main_window.upload_firmware_button.clicked.connect(main_window.upload_updated_firmware)
    main_window.upload_firmware_button.setEnabled(False)
    imu_buttons_layout.addWidget(main_window.upload_firmware_button, 1, 1)
    
    imu_control_layout.addLayout(imu_buttons_layout)
    
    # Current offsets display
    offsets_group = QGroupBox("Current Offsets")
    offsets_layout = QGridLayout(offsets_group)
    
    offsets_layout.addWidget(QLabel("X Offset:"), 0, 0)
    main_window.offset_x_label = QLabel("0.0000")
    main_window.offset_x_label.setStyleSheet("QLabel { background: #f8f9fa; padding: 5px; border: 1px solid #dee2e6; }")
    offsets_layout.addWidget(main_window.offset_x_label, 0, 1)
    
    offsets_layout.addWidget(QLabel("Y Offset:"), 1, 0)
    main_window.offset_y_label = QLabel("0.0000")
    main_window.offset_y_label.setStyleSheet("QLabel { background: #f8f9fa; padding: 5px; border: 1px solid #dee2e6; }")
    offsets_layout.addWidget(main_window.offset_y_label, 1, 1)
    
    offsets_layout.addWidget(QLabel("Z Offset:"), 2, 0)
    main_window.offset_z_label = QLabel("0.0000")
    main_window.offset_z_label.setStyleSheet("QLabel { background: #f8f9fa; padding: 5px; border: 1px solid #dee2e6; }")
    offsets_layout.addWidget(main_window.offset_z_label, 2, 1)
    
    imu_control_layout.addWidget(offsets_group)
    
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
    
    # Raw acceleration values with LCD displays
    data_layout.addWidget(QLabel("AX:"), 0, 0)
    main_window.ax_lcd = QLCDNumber(6)
    main_window.ax_lcd.setDigitCount(6)
    main_window.ax_lcd.setStyleSheet("QLCDNumber { background-color: #f44336; color: white; }")
    data_layout.addWidget(main_window.ax_lcd, 0, 1)
    
    data_layout.addWidget(QLabel("AY:"), 1, 0)
    main_window.ay_lcd = QLCDNumber(6)
    main_window.ay_lcd.setDigitCount(6)
    main_window.ay_lcd.setStyleSheet("QLCDNumber { background-color: #4CAF50; color: white; }")
    data_layout.addWidget(main_window.ay_lcd, 1, 1)
    
    data_layout.addWidget(QLabel("AZ:"), 2, 0)
    main_window.az_lcd = QLCDNumber(6)
    main_window.az_lcd.setDigitCount(6)
    main_window.az_lcd.setStyleSheet("QLCDNumber { background-color: #2196F3; color: white; }")
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
    splitter.setSizes([350, 850])  # Set initial sizes