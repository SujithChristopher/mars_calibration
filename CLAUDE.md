# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Load Cell & IMU Calibration system with a GUI application for Arduino-based sensors. The system provides complete workflows for:
1. Load cell calibration with HX711 sensors
2. IMU (Inertial Measurement Unit) calibration using accelerometer data for pitch, roll, and yaw offset calibration

## Architecture

- **main.py**: Main PySide6 GUI application with tabbed interface for load cell and IMU calibration
- **arduino_compile.py**: Arduino compilation utility using pyduinocli (not actively used)
- **calibration/calibration.ino**: Arduino calibration firmware that simulates HX711 load cell behavior
- **firmware/firmware.ino**: Final Arduino firmware with HX711 integration
- **imu_program/imu_program.ino**: IMU calibration program for Arduino Nano 33 BLE with LSM9DS1 sensor
- **arduino-cli.exe**: Local Arduino CLI executable for compilation and upload
- **logs/**: Session logs with detailed timestamped activities

## Key Components

### GUI Application (main.py)
- **LoadCellCalibrationGUI**: Main window class with tabbed interface
- **SerialWorker**: QThread worker for non-blocking load cell serial communication  
- **IMUDataWorker**: QThread worker for non-blocking IMU serial communication and data parsing
- **StepIndicator**: Custom progress indicator widgets for load cell workflow
- **AngleIndicator**: Custom circular angle visualization widgets
- **AttitudeIndicator**: 3D attitude visualization with artificial horizon
- **Logger**: Centralized logging to file and UI

### Arduino Firmware
- **calibration.ino**: Simulates load cell behavior, handles tare/calibration commands
- **firmware.ino**: Production firmware with configurable calibration factor
- **imu_program.ino**: IMU calibration firmware with accelerometer offset calculation and EEPROM storage

## Common Development Tasks

### Running the Application
```bash
python main.py
```

### Dependencies
- PySide6 (Qt GUI framework)
- pyserial (Serial communication)
- pyduinocli (Arduino compilation - optional)

### Arduino Development
- Uses local `arduino-cli.exe` for compilation and upload
- Supports multiple boards: Arduino Uno, Nano, Nano 33 BLE, Teensy 4.1, ESP32
- Default board: `teensy:avr:teensy41`

### Serial Communication
- Default baud rate: 115200
- Auto-detects and prioritizes Teensy devices
- Fallback to COM10 if available

## Workflows

### Load Cell Calibration Workflow
1. **Step 1**: Upload calibration.ino to Arduino
2. **Step 2**: Connect via serial, perform tare and calibration 
3. **Step 3**: Update firmware.ino with calibration factor and upload

### IMU Calibration Workflow
1. **Upload**: Upload imu_program.ino to Arduino Nano 33 BLE
2. **Connect**: Connect to IMU via serial at 115200 baud
3. **Calibrate**: Place device flat and level, start calibration to find accelerometer offsets
4. **Save**: Save calibration offsets to EEPROM for persistent storage
5. **Monitor**: Real-time visualization of pitch, roll, yaw angles and raw accelerometer data

## File Structure

```
mars_loadcell/
├── main.py                    # Main GUI application
├── arduino_compile.py         # Arduino compilation utility
├── arduino-cli.exe           # Arduino CLI executable
├── calibration/
│   └── calibration.ino       # Load cell calibration firmware
├── firmware/
│   ├── firmware.ino          # Production load cell firmware
│   └── firmware.ino.backup   # Backup created during updates
├── imu_program/
│   └── imu_program.ino       # IMU calibration firmware for Nano 33 BLE
├── compiled_output/          # Arduino compilation output
└── logs/
    └── logs.txt             # Session logs
```

## Important Notes

- The system creates automatic backups when updating firmware with calibration factors
- All operations are logged with timestamps for debugging
- Serial communication runs in separate threads to prevent UI blocking  
- Load cell system supports both real HX711 hardware and simulation mode
- IMU system uses real LSM9DS1 sensor on Arduino Nano 33 BLE
- IMU calibration calculates accelerometer offsets for accurate pitch/roll/yaw measurements
- Arduino cores are automatically installed as needed during upload process
- Default board changed to Arduino Nano 33 BLE for IMU compatibility
- Both load cell and IMU can use the same or different Arduino devices