# Mars Calibration System

A comprehensive GUI application for calibrating load cells and IMU sensors with automated Arduino programming capabilities.

## Features

- **Load Cell Calibration**: Complete workflow for HX711-based load cell calibration
- **IMU Calibration**: Multi-IMU calibration system for pitch, roll, and yaw offset calculation
- **Arduino Integration**: Automatic Arduino CLI management and sketch uploading
- **Data Management**: TOML-based calibration data storage with timestamps
- **Cross-Platform**: Works on Windows, macOS, and Linux
- **Standalone Distribution**: Self-contained executable with automatic dependency management

## Quick Start

### Option 1: Download Release (Recommended)
1. Download the latest release for your platform from the [Releases page](https://github.com/SujithChristopher/mars_calibration/releases)
2. Extract the archive
3. Run `MarsCalibration.exe` (Windows) or `MarsCalibration` (Linux/macOS)
4. Follow the first-time setup wizard

### Option 2: Run from Source
```bash
# Clone the repository
git clone https://github.com/SujithChristopher/mars_calibration.git
cd mars_calibration

# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

## System Requirements

- **Operating System**: Windows 10/11, macOS 10.14+, or Linux (Ubuntu 18.04+)
- **Hardware**: USB port for Arduino connection
- **Network**: Internet connection for first-time setup (Arduino CLI download ~50MB)
- **Arduino**: Compatible boards (Teensy 4.1, Arduino Nano 33 BLE, Uno, etc.)

## First-Time Setup

On first run, the application will:

1. **Check for Arduino CLI** - Downloads and installs if not present
2. **Install Board Packages** - Teensy, Arduino, ESP32 support
3. **Install Libraries** - LSM9DS1, HX711, and other required libraries
4. **Setup Data Directories** - Creates local storage for logs and calibrations

This is a one-time process that takes 2-5 minutes depending on your internet connection.

## Usage Workflow

### 1. Load Cell Calibration
1. Go to **Load Cell Calibration** tab
2. Upload calibration sketch to Arduino
3. Connect to serial port and run calibration with known mass
4. Calibration factor is automatically calculated

### 2. IMU Calibration
1. Go to **IMU Calibration** tab
2. Upload IMU sketch to Arduino Nano 33 BLE
3. Select IMU (1, 2, or 3) and connect
4. Place device flat and run **"Calibrate & Save Current IMU"**
5. Repeat for each IMU (disconnect/reconnect between IMUs)

### 3. Final Firmware Upload
1. Go to **Upload Firmware** tab
2. Review all calibration values
3. Save calibration to TOML file with timestamp
4. Update firmware with all calibration data
5. Upload final firmware to production Arduino

## Data Storage

The application stores data in platform-specific locations:

- **Windows**: `%APPDATA%\MarsCalibration\`
- **macOS**: `~/Library/Application Support/MarsCalibration/`
- **Linux**: `~/.local/share/MarsCalibration/`

### Directory Structure
```
MarsCalibration/
├── logs/                    # Application logs
├── calibrations/            # TOML calibration files
├── arduino-cli/            # Arduino CLI installation
├── arduino_sketches/       # Copied Arduino sketches
└── temp/                   # Temporary files
```

## Supported Hardware

### Arduino Boards
- Teensy 4.1 (recommended)
- Arduino Nano 33 BLE
- Arduino Uno/Nano
- ESP32 boards
- Custom boards via FQBN

### Sensors
- **Load Cells**: HX711-compatible strain gauge load cells
- **IMU**: LSM9DS1 (built-in on Nano 33 BLE)
- **Alternative IMUs**: MPU6050, MPU9250 (with code modifications)

## Development

### Building from Source
```bash
# Install development dependencies
pip install -r requirements.txt

# Run in development mode
python main.py

# Build executable
python build.py
```

### Building Releases
The project includes GitHub Actions for automated builds:

```bash
# Create a new release
git tag v1.0.0
git push origin v1.0.0
```

This triggers automated builds for Windows, macOS, and Linux.

### Manual Build
```bash
# Install PyInstaller
pip install pyinstaller

# Build executable
pyinstaller mars_calibration.spec

# The executable will be in dist/
```

## Architecture

The application uses a modular architecture:

- **GUI**: PySide6-based interface with tabbed workflow
- **Arduino Manager**: Automated Arduino CLI management and sketch handling
- **Data Management**: TOML-based configuration and calibration storage
- **Serial Communication**: Multi-threaded serial handling for real-time data
- **User Data**: Cross-platform user data directory management

## Configuration

### Arduino CLI
- Automatically downloaded to user data directory
- Board packages and libraries auto-installed
- Can use system-wide Arduino CLI if preferred

### Calibration Files
TOML format with timestamp and metadata:
```toml
[metadata]
timestamp = "2024-01-15T10:30:00"
version = "1.0"

[load_cell]
calibration_factor = 2280.50

[imu_offsets]
imu1_pitch = -0.0234
imu1_roll = 0.0156
imu2_pitch = 0.0089
imu2_roll = -0.0201
imu3_roll = 0.0134
```

## Troubleshooting

### Common Issues

**Arduino CLI Download Fails**
- Check internet connection
- Try running as administrator (Windows)
- Manually install Arduino CLI from [arduino.cc/pro/cli](https://arduino.cc/pro/cli)

**Serial Port Not Found**
- Install Arduino device drivers
- Check device manager (Windows) or `dmesg` (Linux)
- Try different USB ports/cables

**Compilation Errors**
- Ensure board packages are installed
- Check Arduino sketch syntax
- Verify library dependencies

**Permission Errors**
- Run as administrator (Windows) or use `sudo` (Linux)
- Check file permissions in user data directory

### Debug Mode
Run with debug flag for verbose logging:
```bash
python main.py --debug
```

### Log Files
Check logs for detailed error information:
- Location: `[User Data]/logs/application.log`
- Contains: Serial communication, Arduino operations, errors

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests if applicable
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/SujithChristopher/mars_calibration/issues)
- **Discussions**: [GitHub Discussions](https://github.com/SujithChristopher/mars_calibration/discussions)
- **Wiki**: [Project Wiki](https://github.com/SujithChristopher/mars_calibration/wiki)

## Acknowledgments

- Arduino community for excellent hardware and software ecosystem
- PySide6 team for the robust GUI framework
- All contributors and testers who helped improve this software