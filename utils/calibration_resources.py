"""
Embedded firmware resources for Mars Calibration System.

This module contains Arduino firmware code embedded as Python string constants,
eliminating the need for file copying and ensuring the latest code is always used.
"""

# Mars Unified Calibration Firmware - Supports both Load Cell and IMU calibration
CALIBRATION_INO_CONTENT = r"""/*
  Mars Unified Calibration Program

  This program provides unified calibration for both Load Cell and IMU sensors.
  Supports multiple Arduino boards and auto-detects available hardware.

  Hardware Support:
  - Load Cell: HX711 via HX711_ADC library (real load cell readings)
  - IMU: MPU6050 on I2C (Teensy 4.1, Arduino Nano 33 BLE)

  Pin Configuration:
  - HX711 DOUT: Pin 14
  - HX711 SCK: Pin 15

  Commands:
  - 'h': Show help and available commands
  - 's': Show current system status
  - 'l': Switch to Load Cell mode
  - 'i': Switch to IMU mode

  Load Cell Commands:
  - 't': Tare the load cell
  - 'r': Start load cell calibration
  - Enter weight value during calibration

  IMU Commands:
  - 'c': Start IMU calibration (place device flat and level)
  - 'x': Reset IMU offsets to zero
  - 'RESET': Software reset

  Output Formats:
  - Load Cell: Raw weight values during operation
  - IMU: AX,AY,AZ,ROLL,PITCH,YAW,OFFSET_X,OFFSET_Y,OFFSET_Z
*/

// HX711 Load Cell Library
#include <HX711_ADC.h>

// Board-specific includes
#if defined(ARDUINO_ARCH_MBED_NANO) || defined(ARDUINO_ARCH_MBED)
  // Nano 33 BLE specific includes
  #include <mbed.h>
#endif

// IMU includes (only compile on supported boards)
#if defined(__IMXRT1062__) || defined(ARDUINO_ARCH_MBED_NANO) || defined(ARDUINO_ARCH_MBED)
  #include "Wire.h"
  #include <MPU6050_light.h>
  #include <math.h>
  #define IMU_SUPPORTED
  const float RAD2DEG = 180.0f / PI;
#endif

// System state
enum CalibrationMode {
  MODE_INIT,
  MODE_LOADCELL,
  MODE_IMU
};

struct SystemStatus {
  bool loadcell_available;
  bool imu_available;
  CalibrationMode current_mode;
  bool initialized;
};

SystemStatus system_status = {false, false, MODE_INIT, false};

// HX711 Load Cell pins
const int HX711_dout = 14;
const int HX711_sck = 15;

// HX711_ADC object for real load cell
HX711_ADC LoadCell(HX711_dout, HX711_sck);

// Load Cell calibration variables
float calibrationFactor = 1.0;
bool isTared = false;
bool isLoadCellCalibrating = false;
float knownMass = 0.0;
unsigned long lastPrintTime = 0;
const unsigned long printInterval = 100; // Print every 100ms for real-time updates
unsigned long settleTime = 0;
const unsigned long settleWaitTime = 1000; // Wait 1 second for load cell to settle

// IMU variables
#ifdef IMU_SUPPORTED
MPU6050 mpu(Wire);
bool imuConnected = false;

// I2C Configuration
#if defined(__IMXRT1062__)  // Teensy 4.1
  #define SDA_PIN 18
  #define SCL_PIN 19
#endif

struct CalibrationData {
  float accel_offset_x;
  float accel_offset_y;
  float accel_offset_z;
  bool valid;
};

// 4-Offset Formula-Based IMU Calibration
struct IMUOffsets {
  float imu1_pitch_offset;  // IMU1 Pitch
  float imu1_roll_offset;   // IMU1 Roll
  float imu2_roll_offset;   // IMU2 Roll (relative to IMU1)
  float imu3_roll_offset;   // IMU3 Roll (relative to IMU1 and IMU2)
  bool valid;
};

CalibrationData calibration;
IMUOffsets imu_offsets = {0, 0, 0, 0, false};
bool isIMUCalibrating = false;
int calibrationSamples = 0;
const int MAX_CALIBRATION_SAMPLES = 100;
float calibrationSum[9] = {0, 0, 0, 0, 0, 0, 0, 0, 0}; // Sum for 3 IMUs (ax1, ay1, az1, ax2, ay2, az2, ax3, ay3, az3)
unsigned long lastIMUPrintTime = 0;
const unsigned long imuPrintInterval = 100; // Print every 100ms for IMU
float filteredAccel[3] = {0, 0, 0};
const float filterAlpha = 0.8; // Low-pass filter coefficient
#endif

void setup() {
  Serial.begin(115200);
  #if defined(ARDUINO_ARCH_MBED_NANO) || defined(ARDUINO_ARCH_MBED)
    while (!Serial && millis() < 3000); // Wait up to 3 seconds for serial
  #endif

  delay(1000);

  Serial.println();
  Serial.println("=== Mars Unified Calibration System ===");
  Serial.println("Supports Load Cell + IMU Calibration");
  Serial.println();

  // Initialize random seed
  #if defined(ARDUINO_ARCH_MBED_NANO) || defined(ARDUINO_ARCH_MBED)
    randomSeed(analogRead(A1)); // Use A1 for Nano 33 BLE
  #else
    randomSeed(analogRead(A0)); // Use A0 for other boards
  #endif

  // Initialize system
  initializeSystem();

  // Wait for first data to be ready from load cell
  if (system_status.loadcell_available) {
    Serial.println("Waiting for load cell data...");
    while (!LoadCell.update()) {
      delay(10);
    }
  }

  // Show initial help
  showHelp();

  delay(2000);
}

void loop() {
  // Handle serial commands
  handleSerialCommands();

  // Update active systems based on current mode
  if (system_status.current_mode == MODE_LOADCELL) {
    updateLoadCell();
  }

  #ifdef IMU_SUPPORTED
  if (system_status.current_mode == MODE_IMU) {
    if (system_status.imu_available) {
      updateIMU();
    }
  }
  #endif

  delay(10);
}

void initializeSystem() {
  Serial.println("=== Initializing System ===");

  // Initialize real HX711 load cell
  LoadCell.begin();

  // Uncomment the line below if readings are inverted (negative when should be positive)
  // LoadCell.setReverseOutput();

  // Stabilizing time and tare setting
  unsigned long stabilizingtime = 2000; // precision right after power-up can be improved
  boolean _tare = true;                 // perform tare during startup
  LoadCell.start(stabilizingtime, _tare);

  // Check for timeout or signal errors
  if (LoadCell.getTareTimeoutFlag() || LoadCell.getSignalTimeoutFlag()) {
    Serial.println("[ERROR] Timeout! Check MCU>HX711 wiring and pin designations");
    system_status.loadcell_available = false;
  } else {
    // Set initial calibration factor (user can change this)
    LoadCell.setCalFactor(1.0);
    system_status.loadcell_available = true;
    Serial.println("[OK] HX711 Load Cell initialized successfully");
  }

  #ifdef IMU_SUPPORTED
  // Try to initialize IMU
  system_status.imu_available = initializeIMU();
  if (system_status.imu_available) {
    Serial.println("[OK] IMU (MPU6050) detected and ready");
  } else {
    Serial.println("[ERROR] IMU not available on this board/configuration");
  }
  #else
  Serial.println("[ERROR] IMU not supported on this board");
  #endif

  // Set default mode (prioritize load cell mode if both available)
  if (system_status.loadcell_available && system_status.imu_available) {
    system_status.current_mode = MODE_LOADCELL;
    Serial.println("Hardware: Both Load Cell and IMU detected");
    Serial.println("Mode: Load Cell (use 'l' or 'i' to switch modes)");
  } else if (system_status.imu_available) {
    system_status.current_mode = MODE_IMU;
    Serial.println("Mode: IMU only");
  } else {
    system_status.current_mode = MODE_LOADCELL;
    Serial.println("Mode: Load Cell only");
  }

  system_status.initialized = true;
  Serial.println("=== Initialization Complete ===");
  Serial.println();
}

#ifdef IMU_SUPPORTED
bool initializeIMU() {
  Serial.println("Trying to initialize IMU...");

  // Try custom pins first (Teensy 4.1)
  #if defined(__IMXRT1062__)
  Wire.setSDA(SDA_PIN);
  Wire.setSCL(SCL_PIN);
  #endif

  Wire.begin();
  Wire.setClock(100000); // 100kHz for better reliability

  // Scan I2C bus
  bool deviceFound = scanI2C();
  if (!deviceFound) {
    return false;
  }

  // Try to connect to MPU6050
  uint8_t addresses[] = {0x68, 0x69};
  for (int i = 0; i < 2; i++) {
    mpu.setAddress(addresses[i]);
    byte status = mpu.begin();
    mpu.calcOffsets(true, false);
    if (status == 0) {
      Serial.print("MPU6050 connected at address 0x");
      Serial.println(addresses[i], HEX);

      // Calculate gyroscope offsets
      Serial.println("Calculating gyroscope offsets, keep device still...");
      delay(1000);
      mpu.calcOffsets(true, false);

      // Initialize calibration data
      calibration.accel_offset_x = 0.0;
      calibration.accel_offset_y = 0.0;
      calibration.accel_offset_z = 0.0;
      calibration.valid = false;

      imuConnected = true;
      return true;
    }
  }

  return false;
}

bool scanI2C() {
  int deviceCount = 0;

  for (uint8_t address = 1; address < 127; address++) {
    Wire.beginTransmission(address);
    uint8_t error = Wire.endTransmission();

    if (error == 0) {
      if (address == 0x68 || address == 0x69) {
        deviceCount++;
      }
    }
  }

  return deviceCount > 0;
}
#endif

void updateLoadCell() {
  static boolean newDataReady = false;

  // Check for new data from ADC
  if (LoadCell.update()) {
    newDataReady = true;  // Mark that fresh data is available
  }

  // Only get and print data when fresh data is ready
  if (newDataReady) {
    if (millis() - lastPrintTime > printInterval) {
      if (system_status.current_mode == MODE_LOADCELL) {
        // Only print weight when in load cell only mode
        // getData() automatically applies the calibration factor set via setCalFactor()
        float displayValue = LoadCell.getData();
        Serial.print("Load_cell output val: ");
        Serial.println(displayValue, 2);
      }
      newDataReady = false;  // Clear flag after using the data
      lastPrintTime = millis();
    }
  }
}

#ifdef IMU_SUPPORTED
void updateIMU() {
  if (!imuConnected) return;

  // Update MPU6050 data
  mpu.update();

  // Get raw accelerometer data (in g units)
  float ax = mpu.getAccX();
  float ay = mpu.getAccY();
  float az = mpu.getAccZ();

  // Apply low-pass filter for smoothing
  filteredAccel[0] = filterAlpha * filteredAccel[0] + (1 - filterAlpha) * ax;
  filteredAccel[1] = filterAlpha * filteredAccel[1] + (1 - filterAlpha) * ay;
  filteredAccel[2] = filterAlpha * filteredAccel[2] + (1 - filterAlpha) * az;

  // Apply calibration offsets
  float calibrated_ax = filteredAccel[0] - calibration.accel_offset_x;
  float calibrated_ay = filteredAccel[1] - calibration.accel_offset_y;
  float calibrated_az = filteredAccel[2] - calibration.accel_offset_z;

  // Calculate angles
  float roll = mpu.getAngleX();
  float pitch = mpu.getAngleY();
  float yaw = mpu.getAngleZ();

  // Handle IMU calibration process
  if (isIMUCalibrating) {
    processIMUCalibration(ax, ay, az);
  }

  // Print IMU data at regular intervals (only in IMU mode)
  if (millis() - lastIMUPrintTime >= imuPrintInterval) {
    if (system_status.current_mode == MODE_IMU) {
      // Format: AX,AY,AZ,ROLL,PITCH,YAW,OFFSET_X,OFFSET_Y,OFFSET_Z
      Serial.print(calibrated_ax, 4);
      Serial.print(",");
      Serial.print(calibrated_ay, 4);
      Serial.print(",");
      Serial.print(calibrated_az, 4);
      Serial.print(",");
      Serial.print(roll, 2);
      Serial.print(",");
      Serial.print(pitch, 2);
      Serial.print(",");
      Serial.print(yaw, 2);
      Serial.print(",");
      Serial.print(calibration.accel_offset_x, 4);
      Serial.print(",");
      Serial.print(calibration.accel_offset_y, 4);
      Serial.print(",");
      Serial.print(calibration.accel_offset_z, 4);
      Serial.println();
    }

    lastIMUPrintTime = millis();
  }
}
#endif


void handleSerialCommands() {
  if (Serial.available() > 0) {
    if (isLoadCellCalibrating && knownMass == 0) {
      // Waiting for known mass input during load cell calibration
      float inputMass = Serial.parseFloat();
      if (inputMass > 0) {
        processLoadCellCalibration(inputMass);
      }
    } else {
      // Handle command input
      String input = Serial.readString();
      input.trim();

      if (input.length() == 1) {
        char command = input.charAt(0);
        processCommand(command);
      } else if (input == "RESET") {
        handleSoftwareReset();
      } else {
        // Check if it's a single character in a longer string
        if (input.length() > 0) {
          processCommand(input.charAt(0));
        }
      }
    }
  }
}

void processCommand(char command) {
  switch (command) {
    case 'h':
      showHelp();
      break;

    case 's':
      showSystemStatus();
      break;

    // Mode Switching
    case 'l':
      if (system_status.loadcell_available) {
        system_status.current_mode = MODE_LOADCELL;
        Serial.println(">>> Switched to Load Cell mode");
      } else {
        Serial.println("Load cell not available");
      }
      break;

    case 'i':
      #ifdef IMU_SUPPORTED
      if (system_status.imu_available) {
        system_status.current_mode = MODE_IMU;
        Serial.println(">>> Switched to IMU mode");
      } else {
        Serial.println("IMU not available");
      }
      #else
      Serial.println("IMU not supported on this board");
      #endif
      break;

    // Load Cell Commands
    case 't':
      if (system_status.loadcell_available) {
        performTare();
      } else {
        Serial.println("Load cell not available");
      }
      break;

    case 'r':
      if (system_status.loadcell_available) {
        startLoadCellCalibration();
      } else {
        Serial.println("Load cell not available");
      }
      break;

    // IMU Commands
    #ifdef IMU_SUPPORTED
    case 'c':
      if (system_status.imu_available) {
        startIMUCalibration();
      } else {
        Serial.println("IMU not available");
      }
      break;

    case 'x':
      if (system_status.imu_available) {
        resetIMUCalibration();
      } else {
        Serial.println("IMU not available");
      }
      break;
    #endif

    default:
      Serial.println("Unknown command. Type 'h' for help.");
      break;
  }
}

void showHelp() {
  Serial.println("=== Mars Unified Calibration Commands ===");
  Serial.println("General:");
  Serial.println("  'h' - Show this help");
  Serial.println("  's' - Show system status");
  Serial.println();

  if (system_status.loadcell_available && system_status.imu_available) {
    Serial.println("Mode Switching:");
    Serial.println("  'l' - Switch to Load Cell mode");
    Serial.println("  'i' - Switch to IMU mode");
    Serial.println();
  }

  if (system_status.loadcell_available) {
    Serial.println("Load Cell Commands:");
    Serial.println("  't' - Tare the scale");
    Serial.println("  'r' - Start calibration");
    Serial.println("  During calibration: Enter weight value (e.g., 100.0)");
    Serial.println();
  }

  #ifdef IMU_SUPPORTED
  if (system_status.imu_available) {
    Serial.println("IMU Commands:");
    Serial.println("  'c' - Start calibration (place device flat and level)");
    Serial.println("  'x' - Reset offsets to zero");
    Serial.println("  'RESET' - Software reset");
    Serial.println();
  }
  #endif

  Serial.println("Current mode: " + getModeString());
  Serial.println("=====================================");
}

void showSystemStatus() {
  Serial.println("=== System Status ===");
  Serial.println("Initialized: " + String(system_status.initialized ? "Yes" : "No"));
  Serial.println("Load Cell: " + String(system_status.loadcell_available ? "Available" : "Not Available"));

  #ifdef IMU_SUPPORTED
  Serial.println("IMU: " + String(system_status.imu_available ? "Available" : "Not Available"));
  if (system_status.imu_available) {
    Serial.println("IMU Connected: " + String(imuConnected ? "Yes" : "No"));
  }
  #else
  Serial.println("IMU: Not Supported on this board");
  #endif

  Serial.println("Current Mode: " + getModeString());
  Serial.println("===================");
}

String getModeString() {
  switch (system_status.current_mode) {
    case MODE_INIT: return "Initializing";
    case MODE_LOADCELL: return "Load Cell";
    case MODE_IMU: return "IMU";
    default: return "Unknown";
  }
}

// Load Cell Functions
void performTare() {
  Serial.println("Performing tare...");
  Serial.println("Please wait while the load cell is being zeroed...");

  // Use non-blocking tare method
  LoadCell.tareNoDelay();

  // Wait for tare to complete
  while (!LoadCell.getTareStatus()) {
    LoadCell.update();
    delay(10);
  }

  isTared = true;
  Serial.println("Tare complete");
}

void startLoadCellCalibration() {
  Serial.println("***");
  Serial.println("Start load cell calibration:");
  Serial.println("Place the load cell on a level stable surface.");
  Serial.println("Remove any load applied to the load cell.");
  Serial.println("Send 't' to set the tare offset.");

  isLoadCellCalibrating = true;
  knownMass = 0;

  waitForTare();
}

void waitForTare() {
  bool tareCompleted = false;

  while (!tareCompleted && isLoadCellCalibrating) {
    LoadCell.update();
    handleSerialCommands();

    if (LoadCell.getTareStatus()) {
      Serial.println("Now, place your known mass on the loadcell.");
      Serial.println("Then send the weight of this mass (i.e. 100.0) from serial monitor.");
      tareCompleted = true;
    }

    delay(10);
  }
}

void processLoadCellCalibration(float inputMass) {
  knownMass = inputMass;
  Serial.print("Known mass is: ");
  Serial.println(knownMass, 1);

  // Refresh dataset with current readings (collect fresh data)
  Serial.println("Refreshing dataset... Please keep the mass stable on the load cell.");
  LoadCell.refreshDataSet();

  // Use HX711_ADC library's built-in calibration calculation
  float newCalibrationValue = LoadCell.getNewCalibration(knownMass);

  // Apply the new calibration factor
  LoadCell.setCalFactor(newCalibrationValue);
  calibrationFactor = newCalibrationValue;

  Serial.print("New calibration value has been set to: ");
  Serial.print(newCalibrationValue, 6);
  Serial.println(", use this as calibration value (calFactor) in your project sketch.");
  Serial.println("Calibration complete. Value will be used in production firmware.");
  Serial.println();

  isLoadCellCalibrating = false;
  knownMass = 0;
}

// IMU Functions
#ifdef IMU_SUPPORTED
void startIMUCalibration() {
  Serial.println("*** STARTING IMU CALIBRATION ***");
  Serial.println("Place the device on a flat, level surface and keep it still.");
  Serial.println("Calibration will take about 10 seconds...");
  Serial.println("Calibration started... Keep device perfectly still!");

  isIMUCalibrating = true;
  calibrationSamples = 0;
  calibrationSum[0] = 0;
  calibrationSum[1] = 0;
  calibrationSum[2] = 0;
}

void processIMUCalibration(float ax, float ay, float az) {
  if (calibrationSamples < MAX_CALIBRATION_SAMPLES) {
    // For single IMU: store in slots 0-2
    // In future, could extend to collect from multiple IMUs in slots 3-5, 6-8
    calibrationSum[0] += ax;
    calibrationSum[1] += ay;
    calibrationSum[2] += az;
    calibrationSamples++;

    // Show progress
    if (calibrationSamples % 20 == 0) {
      Serial.print("Calibration progress: ");
      Serial.print((calibrationSamples * 100) / MAX_CALIBRATION_SAMPLES);
      Serial.println("%");
    }
  } else {
    // Calculate average values from single IMU
    float avg_ax = calibrationSum[0] / MAX_CALIBRATION_SAMPLES;
    float avg_ay = calibrationSum[1] / MAX_CALIBRATION_SAMPLES;
    float avg_az = calibrationSum[2] / MAX_CALIBRATION_SAMPLES;

    // Calculate 4-offset using firmware formulas (assuming this is IMU1 for now)
    // Device should be placed flat and level during calibration
    calculateIMUOffsets(avg_ax, avg_ay, avg_az);

    calibration.valid = true;
    isIMUCalibrating = false;

    Serial.println("*** IMU CALIBRATION COMPLETE ***");
    Serial.println("Calculated 4-Offset Values (Formula-Based):");
    Serial.print("IMU1 Pitch Offset: ");
    Serial.println(imu_offsets.imu1_pitch_offset, 6);
    Serial.print("IMU1 Roll Offset: ");
    Serial.println(imu_offsets.imu1_roll_offset, 6);
    Serial.print("IMU2 Roll Offset: ");
    Serial.println(imu_offsets.imu2_roll_offset, 6);
    Serial.print("IMU3 Roll Offset: ");
    Serial.println(imu_offsets.imu3_roll_offset, 6);
    Serial.println("*** Use these 4 offsets in your firmware (variable.h) ***");
    Serial.println();
  }
}

void calculateIMUOffsets(float ax, float ay, float az) {
  // Calculate 4 IMU offsets using firmware formulas
  // Device must be placed flat and level during calibration

  // ===== IMU1 PITCH OFFSET =====
  // Formula: Theta1 = atan2(ax, sqrt(ay^2 + az^2)) - IMU1PITCHOFFSET
  // When flat: offset = atan2(ax, sqrt(ay^2 + az^2))
  float norm = sqrt(ay * ay + az * az);
  imu_offsets.imu1_pitch_offset = atan2(ax, norm);

  // ===== IMU1 ROLL OFFSET =====
  // Formula: Theta2 = atan2(-az/cos(Theta1), ay/cos(Theta1)) * -1 - IMU1ROLLOFFSET
  // When flat: offset = atan2(-az/cos(Theta1), ay/cos(Theta1)) * -1
  float cos_pitch = cos(imu_offsets.imu1_pitch_offset);
  imu_offsets.imu1_roll_offset = atan2(-az / cos_pitch, ay / cos_pitch);
  
  // For now, set IMU2 and IMU3 offsets to 0
  // In a multi-IMU system, these would be calculated from IMU2 and IMU3 data
  // with adjustments for the relative subtractions in firmware
  imu_offsets.imu2_roll_offset = 0.0;
  imu_offsets.imu3_roll_offset = 0.0;

  imu_offsets.valid = true;
}

void resetIMUCalibration() {
  calibration.accel_offset_x = 0.0;
  calibration.accel_offset_y = 0.0;
  calibration.accel_offset_z = 0.0;
  calibration.valid = false;

  Serial.println("IMU calibration offsets reset to zero");
}
#endif

void handleSoftwareReset() {
  Serial.println("*** SOFTWARE RESET REQUESTED ***");
  Serial.println("System will restart in 2 seconds...");
  Serial.println("Please wait for reconnection.");
  Serial.flush();

  delay(2000);

  // Board-specific reset
  #if defined(__IMXRT1062__)  // Teensy 4.x
    SCB_AIRCR = 0x05FA0004;  // Request system reset
  #elif defined(ARDUINO_ARCH_MBED_NANO) || defined(ARDUINO_ARCH_MBED)
    NVIC_SystemReset();  // ARM Cortex-M reset
  #else
    // For other boards, jump to reset vector
    void (*resetFunc)(void) = 0;
    resetFunc();
  #endif
}
"""


def get_calibration_firmware():
    """
    Get the calibration firmware content as a string.

    Returns:
        str: The complete calibration.ino firmware code
    """
    return CALIBRATION_INO_CONTENT


def write_calibration_firmware(target_path):
    """
    Write the embedded calibration firmware to a file.

    Args:
        target_path (str or Path): The destination file path for the firmware

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        from pathlib import Path
        target_path = Path(target_path)

        # Ensure parent directory exists
        target_path.parent.mkdir(parents=True, exist_ok=True)

        # Write the firmware content
        with open(target_path, 'w') as f:
            f.write(CALIBRATION_INO_CONTENT)

        return True
    except Exception as e:
        print(f"Error writing calibration firmware: {e}")
        return False


def get_firmware_directory(app_data_dir):
    """
    Get or create the firmware directory and write embedded firmware files.

    Args:
        app_data_dir (Path): The application data directory path

    Returns:
        Path: The path to the firmware directory containing calibration.ino
    """
    try:
        from pathlib import Path

        firmware_dir = Path(app_data_dir) / 'arduino_sketches' / 'calibration'
        firmware_dir.mkdir(parents=True, exist_ok=True)

        # Write the embedded firmware
        firmware_path = firmware_dir / 'calibration.ino'
        if write_calibration_firmware(firmware_path):
            return firmware_dir
        else:
            raise Exception("Failed to write firmware file")

    except Exception as e:
        print(f"Error creating firmware directory: {e}")
        return None


def create_firmware_file(output_path):
    """
    Create a calibration firmware file at the specified path.

    Args:
        output_path (str or Path): The destination file path

    Returns:
        bool: True if successful, False otherwise
    """
    return write_calibration_firmware(output_path)
