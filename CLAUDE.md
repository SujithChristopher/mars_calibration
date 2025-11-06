# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Mars Device Load Cell & IMU Calibration system with a GUI application for Arduino-based sensors. The system provides complete workflows for calibrating multiple Mars devices (up to 10,000 units) with:
1. Load cell calibration with HX711 sensors
2. IMU (Inertial Measurement Unit) calibration using accelerometer data for pitch, roll, and yaw offset calibration
3. Unified calibration program supporting both systems
4. Mars device ID tracking and management

## Architecture

### **Modular Structure (Optimized for Token Efficiency)**
- **main.py**: Streamlined application entry point (~20 lines)
- **gui/main_window.py**: Main window class with core application logic
- **gui/load_cell_tab.py**: Load cell calibration UI components
- **gui/imu_tab.py**: IMU calibration UI components  
- **gui/widgets/**: Custom visualization widgets (AngleIndicator, AttitudeIndicator, StepIndicator)
- **gui/workers/**: Serial communication worker threads (SerialWorker, IMUDataWorker)
- **utils/logger.py**: Centralized logging utility
- **arduino_compile.py**: Arduino compilation utility using pyduinocli (not actively used)

### **Arduino Firmware**
- **calibration/calibration.ino**: **UNIFIED** calibration program supporting both Load Cell and IMU calibration
- **loadcell_calibration/loadcell_calibration.ino**: Legacy Arduino calibration firmware that simulates HX711 load cell behavior
- **firmware/firmware.ino**: Final Arduino firmware with HX711 integration
- **imu_program_teensy/imu_program_teensy.ino**: Legacy IMU calibration program for Teensy 4.1 with MPU6050 sensor
- **arduino-cli.exe**: Local Arduino CLI executable for compilation and upload
- **logs/**: Session logs with detailed timestamped activities

## Key Components

### GUI Application Components
- **LoadCellCalibrationGUI** (gui/main_window.py): Main window class with tabbed interface
- **SerialWorker** (gui/workers/serial_worker.py): QThread worker for non-blocking load cell serial communication  
- **IMUDataWorker** (gui/workers/imu_worker.py): QThread worker for non-blocking IMU serial communication and data parsing
- **StepIndicator** (gui/widgets/step_indicator.py): Custom progress indicator widgets for load cell workflow
- **AngleIndicator** (gui/widgets/angle_indicator.py): Custom circular angle visualization widgets
- **AttitudeIndicator** (gui/widgets/attitude_indicator.py): 3D attitude visualization with artificial horizon
- **Logger** (utils/logger.py): Centralized logging to file and UI

### Arduino Firmware
- **calibration.ino**: **UNIFIED** calibration program with auto-detection (Load Cell + IMU)
- **loadcell_calibration.ino**: Legacy - Simulates load cell behavior, handles tare/calibration commands
- **firmware.ino**: Production firmware with configurable calibration factor and Mars ID
- **imu_program_teensy.ino**: Legacy - IMU calibration firmware with accelerometer offset calculation

### Mars Device Management
- **Mars ID System**: Integer-based device identification (0-9999)
- **Cross-tab Synchronization**: Mars ID syncs across Load Cell, IMU, and Upload Firmware tabs
- **File Organization**: Automatic zero-padded naming (Mars_0042_calibration_20240820_143025.toml)
- **Calibration History**: Full tracking with Mars ID column for multi-device management
- **Persistent Storage**: Mars ID saved and restored between sessions

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

### Unified Calibration Workflow (Recommended)
1. **Set Mars ID**: Enter device ID (e.g., 1, 42, 123) in any tab - syncs across all tabs
2. **Upload Program**: Upload calibration.ino (unified program) from either Load Cell or IMU tab
3. **Load Cell Calibration**: Use 't' for tare, 'r' for calibration, enter known mass
4. **IMU Calibration**: Use 'c' for calibration (place flat), 'x' to reset offsets
5. **Save Data**: All calibration data saved with Mars ID for easy identification
6. **Upload Firmware**: Update firmware.ino with calibration factor and Mars ID, then upload

### Legacy Load Cell Calibration Workflow
1. **Step 1**: Upload loadcell_calibration.ino to Arduino (legacy)
2. **Step 2**: Connect via serial, perform tare and calibration, save calibration factor
3. **Step 3**: Go to Upload Firmware tab to update firmware.ino with calibration factor and upload

### Legacy IMU Calibration Workflow
1. **Upload**: Upload imu_program_teensy.ino to Teensy 4.1 (legacy)
2. **Connect**: Connect to IMU via serial at 115200 baud
3. **Calibrate**: Place device flat and level, start calibration to find accelerometer offsets
4. **Save**: Save calibration offsets to EEPROM for persistent storage
5. **Monitor**: Real-time visualization of pitch, roll, yaw angles and raw accelerometer data

### Mars Device Production Workflow
1. **Device Setup**: Enter unique Mars ID (1, 2, 3, ... up to 9999)
2. **Calibration**: Complete both Load Cell and IMU calibration using unified program
3. **History Tracking**: View calibration history with Mars ID column for device identification
4. **File Management**: All files automatically named with Mars ID prefix
5. **Quality Control**: Load previous calibrations by Mars ID for verification

## File Structure

```
mars_calibration/
├── main.py                    # Streamlined application entry point
├── arduino_compile.py         # Arduino compilation utility  
├── arduino-cli.exe           # Arduino CLI executable
├── calibration/              # **UNIFIED CALIBRATION PROGRAM**
│   └── calibration.ino       # Unified Load Cell + IMU calibration
├── gui/                      # GUI components (modular structure)
│   ├── __init__.py
│   ├── main_window.py        # Main window class with Mars ID management
│   ├── load_cell_tab.py      # Load cell UI components with Mars ID input
│   ├── imu_tab.py           # IMU UI components with Mars ID sync
│   ├── upload_firmware_tab.py # Firmware upload with Mars ID display & history
│   ├── widgets/             # Custom visualization widgets
│   │   ├── __init__.py
│   │   ├── step_indicator.py # Progress indicators
│   │   ├── angle_indicator.py # Circular angle displays
│   │   └── attitude_indicator.py # 3D attitude display
│   └── workers/             # Serial communication threads
│       ├── __init__.py
│       ├── serial_worker.py  # Load cell serial communication
│       └── imu_worker.py     # IMU data parsing and communication
├── utils/                   # Utility classes
│   ├── __init__.py
│   ├── logger.py            # Centralized logging
│   └── user_data.py         # User data management with Mars ID persistence
├── loadcell_calibration/    # Legacy calibration programs
│   └── loadcell_calibration.ino  # Legacy load cell calibration firmware
├── firmware/
│   ├── firmware.ino         # Production load cell firmware with Mars ID
│   └── Mars_####_firmware_backup_*.ino  # Mars ID named backups
├── imu_program_teensy/      # Legacy IMU calibration
│   └── imu_program_teensy.ino # Legacy IMU calibration firmware for Teensy 4.1
├── compiled_output/         # Arduino compilation output
├── calibrations/            # Mars device calibration data
│   └── Mars_####_calibration_*.toml # Mars ID named calibration files
└── logs/
    └── logs.txt            # Session logs
```

## Important Notes

### **System Architecture**
- **Modular Architecture**: Code is split into focused, token-efficient modules for better maintainability
- **Token Optimization**: Smaller files mean Claude can work more efficiently with targeted modifications
- **Unified Calibration**: Single Arduino program handles both Load Cell and IMU calibration with auto-detection
- **Production Ready**: Designed for calibrating multiple Mars devices (up to 10,000 units)

### **Mars Device Management**
- **Integer Mars ID**: Simple numeric IDs (0-9999) with automatic validation and zero-padding
- **Cross-tab Sync**: Mars ID entered in any tab automatically syncs to all other tabs
- **Persistent Storage**: Mars ID saved and restored between application sessions
- **File Organization**: All files automatically named with Mars ID prefix for easy identification
- **Calibration History**: Full tracking table with Mars ID column for multi-device management

### **Technical Features**
- All operations are logged with timestamps for debugging
- Serial communication runs in separate threads to prevent UI blocking  
- Load cell system supports both real HX711 hardware and simulation mode
- IMU system uses real MPU6050 sensor on Teensy 4.1 or LSM9DS1 on Arduino Nano 33 BLE
- IMU calibration calculates accelerometer offsets for accurate pitch/roll/yaw measurements
- Arduino cores are automatically installed as needed during upload process
- System creates automatic backups with Mars ID when updating firmware
- Both load cell and IMU can use the same or different Arduino devices

### **Command Interface (Unified Calibration)**
- **'h'**: Show help and available commands
- **'i'**: Initialize and detect available hardware  
- **'s'**: Show current system status
- **Load Cell Commands**: 't' (tare), 'r' (calibrate), enter weight values
- **IMU Commands**: 'c' (calibrate), 'x' (reset), 'RESET' (software reset)
- **Auto-detection**: System automatically detects available hardware and adjusts mode

## Development Benefits

- **Focused Editing**: Modify specific components without reading entire codebase
- **Parallel Development**: Different components can be worked on independently  
- **Reduced Token Usage**: ~94% reduction in tokens for focused modifications
- **Better Organization**: Logical separation of concerns and responsibilities
- **Easier Testing**: Individual components can be tested in isolation
- **Production Scalability**: Easily manage calibration of thousands of Mars devices
- **Unified Workflow**: Single program reduces complexity and user training requirements

## File Naming Examples

### **Calibration Data Files**
```
Mars_0001_calibration_20240820_100530.toml
Mars_0042_calibration_20240820_143025.toml  
Mars_0123_calibration_20240820_150030.toml
Mars_9999_calibration_20240820_160045.toml
```

### **Firmware Backup Files**
```
Mars_0001_firmware_backup_20240820_100545.ino
Mars_0042_firmware_backup_20240820_143040.ino
Mars_0123_firmware_backup_20240820_150045.ino
```

### **Calibration History Table View**
```
Mars ID | Date/Time           | Load Factor | IMU1 P | IMU1 R | IMU2 P | IMU2 R | IMU3 R
1       | 2024-08-20 10:05:30 | 2043.56    | 0.0012 | -0.0045| 0.0023 | 0.0001 | 0.0034
42      | 2024-08-20 14:30:25 | 2038.91    | 0.0015 | -0.0051| 0.0027 | 0.0002 | 0.0041
123     | 2024-08-20 15:00:30 | 2047.83    | 0.0011 | -0.0038| 0.0021 | 0.0004 | 0.0036
```