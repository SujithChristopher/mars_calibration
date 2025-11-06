"""
Upload Firmware tab UI components for final calibration data management.
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, 
                               QLabel, QPushButton, QTableWidget, QTableWidgetItem,
                               QTextEdit, QComboBox, QGridLayout, QHeaderView)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


def setup_upload_firmware_tab(main_window):
    """Setup Upload Firmware tab for final calibration management"""
    # Create tab widget
    upload_tab = QWidget()
    main_window.tab_widget.addTab(upload_tab, "Upload Firmware")
    
    # Main layout
    main_layout = QVBoxLayout(upload_tab)
    
    # Mars ID Section
    mars_id_group = QGroupBox("Mars Device Information")
    mars_id_layout = QGridLayout(mars_id_group)
    
    mars_id_layout.addWidget(QLabel("Mars ID:"), 0, 0)
    main_window.firmware_mars_id_label = QLabel("Not Set")
    main_window.firmware_mars_id_label.setStyleSheet("""
    QLabel {
        background: palette(base);
        color: palette(text);
        padding: 8px;
        border: 2px solid palette(mid);
        border-radius: 4px;
        font-family: 'Consolas', 'Monaco', monospace;
        font-size: 11pt;
        font-weight: bold;
        min-width: 120px;
    }
    """)
    mars_id_layout.addWidget(main_window.firmware_mars_id_label, 0, 1)
    
    mars_id_note = QLabel("💡 Mars ID is automatically included in all filenames and calibration data")
    mars_id_note.setStyleSheet("QLabel { color: #666; font-size: 10px; }")
    mars_id_layout.addWidget(mars_id_note, 1, 0, 1, 2)
    
    main_layout.addWidget(mars_id_group)
    
    # Load Cell Calibration Status
    loadcell_group = QGroupBox("Load Cell Calibration Status")
    loadcell_layout = QGridLayout(loadcell_group)
    
    loadcell_layout.addWidget(QLabel("Calibration Factor:"), 0, 0)
    main_window.final_calibration_factor_label = QLabel("Not Calibrated")
    main_window.final_calibration_factor_label.setStyleSheet("""
    QLabel {
        background: palette(base);
        color: palette(text);
        padding: 8px;
        border: 2px solid palette(mid);
        border-radius: 4px;
        font-family: 'Consolas', 'Monaco', monospace;
        font-size: 11pt;
        font-weight: bold;
        min-width: 120px;
    }
    """)
    loadcell_layout.addWidget(main_window.final_calibration_factor_label, 0, 1)
    
    main_layout.addWidget(loadcell_group)
    
    # Middle section - IMU Calibration Status
    imu_group = QGroupBox("IMU Calibration Status")
    imu_layout = QGridLayout(imu_group)
    
    # IMU angle offset labels
    imu_offset_style = """
    QLabel {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 palette(highlight), stop:1 palette(base));
        color: palette(highlighted-text);
        padding: 8px;
        border: 2px solid palette(highlight);
        border-radius: 4px;
        font-family: 'Consolas', 'Monaco', monospace;
        font-size: 10pt;
        font-weight: bold;
        min-width: 80px;
    }
    """
    
    # IMU 1
    imu_layout.addWidget(QLabel("IMU 1 Pitch:"), 0, 0)
    main_window.final_angle_offset1_label = QLabel("Not Set")
    main_window.final_angle_offset1_label.setStyleSheet(imu_offset_style)
    imu_layout.addWidget(main_window.final_angle_offset1_label, 0, 1)
    
    imu_layout.addWidget(QLabel("IMU 1 Roll:"), 0, 2)
    main_window.final_angle_offset2_label = QLabel("Not Set")
    main_window.final_angle_offset2_label.setStyleSheet(imu_offset_style)
    imu_layout.addWidget(main_window.final_angle_offset2_label, 0, 3)
    
    # IMU 2
    imu_layout.addWidget(QLabel("IMU 2 Pitch:"), 1, 0)
    main_window.final_angle_offset3_label = QLabel("Not Set")
    main_window.final_angle_offset3_label.setStyleSheet(imu_offset_style)
    imu_layout.addWidget(main_window.final_angle_offset3_label, 1, 1)
    
    imu_layout.addWidget(QLabel("IMU 2 Roll:"), 1, 2)
    main_window.final_angle_offset4_label = QLabel("Not Set")
    main_window.final_angle_offset4_label.setStyleSheet(imu_offset_style)
    imu_layout.addWidget(main_window.final_angle_offset4_label, 1, 3)
    
    # IMU 3
    imu_layout.addWidget(QLabel("IMU 3 Pitch:"), 2, 0)
    main_window.final_angle_offset5_label = QLabel("Not Set")
    main_window.final_angle_offset5_label.setStyleSheet(imu_offset_style)
    imu_layout.addWidget(main_window.final_angle_offset5_label, 2, 1)

    imu_layout.addWidget(QLabel("IMU 3 Roll:"), 2, 2)
    main_window.final_angle_offset6_label = QLabel("Not Set")
    main_window.final_angle_offset6_label.setStyleSheet(imu_offset_style)
    imu_layout.addWidget(main_window.final_angle_offset6_label, 2, 3)
    
    main_layout.addWidget(imu_group)
    
    # Calibration History Section
    history_group = QGroupBox("Calibration History (TOML Files)")
    history_layout = QVBoxLayout(history_group)
    
    # Buttons for history management
    history_buttons_layout = QHBoxLayout()
    
    main_window.refresh_history_button = QPushButton("Refresh History")
    main_window.refresh_history_button.clicked.connect(main_window.refresh_calibration_history)
    history_buttons_layout.addWidget(main_window.refresh_history_button)
    
    main_window.load_calibration_button = QPushButton("Load Selected Calibration")
    main_window.load_calibration_button.clicked.connect(main_window.load_selected_calibration)
    main_window.load_calibration_button.setEnabled(False)
    history_buttons_layout.addWidget(main_window.load_calibration_button)
    
    main_window.save_current_calibration_button = QPushButton("Save Current Calibration")
    main_window.save_current_calibration_button.clicked.connect(main_window.save_current_calibration)
    main_window.save_current_calibration_button.setStyleSheet("QPushButton { background: #2196F3; color: white; padding: 8px; font-weight: bold; }")
    history_buttons_layout.addWidget(main_window.save_current_calibration_button)
    
    history_layout.addLayout(history_buttons_layout)
    
    # Calibration history table
    main_window.calibration_history_table = QTableWidget()
    main_window.calibration_history_table.setColumnCount(9)
    main_window.calibration_history_table.setHorizontalHeaderLabels([
        "Mars ID", "Date/Time", "Load Factor", "IMU1 P", "IMU1 R", "IMU2 P", "IMU2 R", "IMU3 P", "IMU3 R"
    ])
    
    # Make table fill the width
    header = main_window.calibration_history_table.horizontalHeader()
    header.setSectionResizeMode(QHeaderView.Stretch)

    # Make table read-only (no editing)
    from PySide6.QtWidgets import QAbstractItemView
    main_window.calibration_history_table.setEditTriggers(QAbstractItemView.NoEditTriggers)

    main_window.calibration_history_table.setSelectionBehavior(QTableWidget.SelectRows)
    main_window.calibration_history_table.itemSelectionChanged.connect(
        lambda: main_window.load_calibration_button.setEnabled(
            len(main_window.calibration_history_table.selectedItems()) > 0
        )
    )
    
    history_layout.addWidget(main_window.calibration_history_table)
    
    main_layout.addWidget(history_group)
    
    # Firmware Upload Section
    firmware_group = QGroupBox("Final Firmware Upload")
    firmware_layout = QVBoxLayout(firmware_group)
    
    # Board and port selection
    upload_settings_layout = QGridLayout()
    
    upload_settings_layout.addWidget(QLabel("Board:"), 0, 0)
    main_window.final_board_combo = QComboBox()
    main_window.final_board_combo.addItems([
        "teensy:avr:teensy41",
        "auto-detect",
        "arduino:mbed_nano:nano33ble",
        "arduino:samd:nano_33_iot",
        "arduino:avr:uno", 
        "arduino:avr:nano", 
        "arduino:mbed_nano:nanorp2040connect"
    ])
    main_window.final_board_combo.setCurrentText("teensy:avr:teensy41")
    upload_settings_layout.addWidget(main_window.final_board_combo, 0, 1)
    
    upload_settings_layout.addWidget(QLabel("Port:"), 0, 2)
    main_window.final_port_combo = QComboBox()
    upload_settings_layout.addWidget(main_window.final_port_combo, 0, 3)
    
    main_window.final_refresh_ports_button = QPushButton("Refresh Ports")
    main_window.final_refresh_ports_button.clicked.connect(main_window.refresh_ports)
    upload_settings_layout.addWidget(main_window.final_refresh_ports_button, 0, 4)
    
    firmware_layout.addLayout(upload_settings_layout)
    
    # Final upload buttons
    upload_buttons_layout = QHBoxLayout()
    
    main_window.update_firmware_with_values_button = QPushButton("Update Firmware with Current Values")
    main_window.update_firmware_with_values_button.clicked.connect(main_window.update_firmware_with_current_values)
    main_window.update_firmware_with_values_button.setEnabled(False)
    upload_buttons_layout.addWidget(main_window.update_firmware_with_values_button)
    
    main_window.upload_final_firmware_button = QPushButton("Upload Final Firmware")
    main_window.upload_final_firmware_button.clicked.connect(main_window.upload_final_firmware)
    main_window.upload_final_firmware_button.setEnabled(False)
    main_window.upload_final_firmware_button.setStyleSheet("QPushButton { background: #FF5722; color: white; padding: 12px; font-weight: bold; font-size: 12pt; }")
    upload_buttons_layout.addWidget(main_window.upload_final_firmware_button)
    
    firmware_layout.addLayout(upload_buttons_layout)
    
    # Status display
    main_window.upload_status_text = QTextEdit()
    main_window.upload_status_text.setReadOnly(True)
    main_window.upload_status_text.setFont(QFont("Courier", 9))
    main_window.upload_status_text.setMaximumHeight(150)
    firmware_layout.addWidget(main_window.upload_status_text)
    
    main_layout.addWidget(firmware_group)