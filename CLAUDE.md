# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Load Cell Calibration system with a GUI application for Arduino-based load cells. The system provides a complete workflow for uploading calibration code, performing calibration, and uploading final firmware.

## Architecture

- **main.py**: Main PySide6 GUI application with step-by-step calibration wizard
- **arduino_compile.py**: Arduino compilation utility using pyduinocli (not actively used)
- **calibration/calibration.ino**: Arduino calibration firmware that simulates HX711 load cell behavior
- **firmware/firmware.ino**: Final Arduino firmware with HX711 integration
- **arduino-cli.exe**: Local Arduino CLI executable for compilation and upload
- **logs/**: Session logs with detailed timestamped activities

## Key Components

### GUI Application (main.py)
- **LoadCellCalibrationGUI**: Main window class with 3-step wizard interface
- **SerialWorker**: QThread worker for non-blocking serial communication  
- **StepIndicator**: Custom progress indicator widgets
- **Logger**: Centralized logging to file and UI

### Arduino Firmware
- **calibration.ino**: Simulates load cell behavior, handles tare/calibration commands
- **firmware.ino**: Production firmware with configurable calibration factor

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

## Workflow

1. **Step 1**: Upload calibration.ino to Arduino
2. **Step 2**: Connect via serial, perform tare and calibration 
3. **Step 3**: Update firmware.ino with calibration factor and upload

## File Structure

```
mars_loadcell/
├── main.py                    # Main GUI application
├── arduino_compile.py         # Arduino compilation utility
├── arduino-cli.exe           # Arduino CLI executable
├── calibration/
│   └── calibration.ino       # Calibration firmware
├── firmware/
│   ├── firmware.ino          # Production firmware
│   └── firmware.ino.backup   # Backup created during updates
├── compiled_output/          # Arduino compilation output
└── logs/
    └── logs.txt             # Session logs
```

## Important Notes

- The system creates automatic backups when updating firmware with calibration factors
- All operations are logged with timestamps for debugging
- Serial communication runs in separate thread to prevent UI blocking  
- Supports both real HX711 hardware and simulation mode
- Arduino cores are automatically installed as needed during upload process