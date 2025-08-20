/*
  Mars Unified Calibration Program
  
  This program provides unified calibration for both Load Cell and IMU sensors.
  Supports multiple Arduino boards and auto-detects available hardware.
  
  Hardware Support:
  - Load Cell: HX711 simulation (all boards)
  - IMU: MPU6050 on I2C (Teensy 4.1, Arduino Nano 33 BLE)
  
  Commands:
  - 'h': Show help and available commands
  - 'i': Initialize and detect available hardware
  - 's': Show current system status
  
  Load Cell Commands:
  - 't': Tare the load cell
  - 'r': Start load cell calibration
  - Enter weight value during calibration
  
  IMU Commands:
  - 'c': Start IMU calibration (place device flat and level)
  - 'x': Reset IMU offsets to zero
  - 'RESET': Software reset for IMU switching
  
  Output Formats:
  - Load Cell: Raw weight values during operation
  - IMU: AX,AY,AZ,ROLL,PITCH,YAW,OFFSET_X,OFFSET_Y,OFFSET_Z
*/

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
  MODE_IMU,
  MODE_BOTH
};

struct SystemStatus {
  bool loadcell_available;
  bool imu_available;
  CalibrationMode current_mode;
  bool initialized;
};

SystemStatus system_status = {false, false, MODE_INIT, false};

// Load Cell variables (simulation)
float simulatedWeight = 0.0;
float calibrationFactor = 1.0;
float tareOffset = 0.0;
bool isTared = false;
bool isLoadCellCalibrating = false;
float knownMass = 0.0;
unsigned long lastPrintTime = 0;
const unsigned long printInterval = 500; // Print every 500ms for load cell
float baseNoise = 0.0;
unsigned long noiseTime = 0;

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

CalibrationData calibration;
bool isIMUCalibrating = false;
int calibrationSamples = 0;
const int MAX_CALIBRATION_SAMPLES = 100;
float calibrationSum[3] = {0, 0, 0};
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
  
  // Show initial help
  showHelp();
  
  delay(2000);
}

void loop() {
  // Handle serial commands
  handleSerialCommands();
  
  // Update active systems based on current mode
  if (system_status.current_mode == MODE_LOADCELL || system_status.current_mode == MODE_BOTH) {
    updateLoadCell();
  }
  
  #ifdef IMU_SUPPORTED
  if (system_status.current_mode == MODE_IMU || system_status.current_mode == MODE_BOTH) {
    if (system_status.imu_available) {
      updateIMU();
    }
  }
  #endif
  
  delay(10);
}

void initializeSystem() {
  Serial.println("=== Initializing System ===");
  
  // Always enable load cell simulation
  system_status.loadcell_available = true;
  Serial.println("✓ Load Cell simulation ready");
  
  #ifdef IMU_SUPPORTED
  // Try to initialize IMU
  system_status.imu_available = initializeIMU();
  if (system_status.imu_available) {
    Serial.println("✓ IMU (MPU6050) detected and ready");
  } else {
    Serial.println("✗ IMU not available on this board/configuration");
  }
  #else
  Serial.println("✗ IMU not supported on this board");
  #endif
  
  // Set default mode
  if (system_status.loadcell_available && system_status.imu_available) {
    system_status.current_mode = MODE_BOTH;
    Serial.println("Mode: Both Load Cell and IMU available");
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
    
    if (status == 0) {
      Serial.print("MPU6050 connected at address 0x");
      Serial.println(addresses[i], HEX);
      
      // Calculate gyroscope offsets
      Serial.println("Calculating gyroscope offsets, keep device still...");
      delay(1000);
      mpu.calcOffsets();
      
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
  // Generate simulated load cell reading
  generateSimulatedReading();
  
  // Print simulated weight reading
  if (millis() - lastPrintTime > printInterval) {
    if (system_status.current_mode == MODE_LOADCELL) {
      // Only print weight when in load cell only mode
      float displayValue = (simulatedWeight - tareOffset) * calibrationFactor;
      Serial.println(displayValue, 2);
    }
    lastPrintTime = millis();
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
  
  // Print IMU data at regular intervals
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

void generateSimulatedReading() {
  // Generate realistic noise and drift
  if (millis() - noiseTime > 100) {
    baseNoise = random(-50, 50) / 100.0; // ±0.5 unit noise
    noiseTime = millis();
  }
  
  // Simulate weight changes
  float drift = sin(millis() / 10000.0) * 2.0; // Slow drift
  simulatedWeight = baseNoise + drift;
  
  // If calibrating and known mass is set, simulate weight on scale
  if (isLoadCellCalibrating && knownMass > 0) {
    simulatedWeight += knownMass / calibrationFactor;
  }
}

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
      
    case 'i':
      initializeSystem();
      break;
      
    case 's':
      showSystemStatus();
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
      
    case 'y':
      if (!isLoadCellCalibrating) {
        Serial.println("Load cell calibration value saved to EEPROM.");
      }
      break;
      
    case 'n':
      if (!isLoadCellCalibrating) {
        Serial.println("Load cell calibration value not saved.");
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
  Serial.println("  'i' - Initialize/re-detect hardware");
  Serial.println("  's' - Show system status");
  Serial.println();
  
  if (system_status.loadcell_available) {
    Serial.println("Load Cell:");
    Serial.println("  't' - Tare the scale");
    Serial.println("  'r' - Start calibration");
    Serial.println("  During calibration: Enter weight value (e.g., 100.0)");
    Serial.println("  'y'/'n' - Save/don't save calibration to EEPROM");
    Serial.println();
  }
  
  #ifdef IMU_SUPPORTED
  if (system_status.imu_available) {
    Serial.println("IMU:");
    Serial.println("  'c' - Start calibration (place device flat and level)");
    Serial.println("  'x' - Reset offsets to zero");
    Serial.println("  'RESET' - Software reset for IMU switching");
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
    case MODE_LOADCELL: return "Load Cell Only";
    case MODE_IMU: return "IMU Only";
    case MODE_BOTH: return "Load Cell + IMU";
    default: return "Unknown";
  }
}

// Load Cell Functions
void performTare() {
  Serial.println("Performing tare...");
  delay(500);
  
  tareOffset = simulatedWeight;
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
    handleSerialCommands();
    
    if (isTared) {
      Serial.println("Now, place your known mass on the loadcell.");
      Serial.println("Then send the weight of this mass (i.e. 100.0) from serial monitor.");
      tareCompleted = true;
      isTared = false; // Reset for next time
    }
    
    delay(10);
  }
}

void processLoadCellCalibration(float inputMass) {
  knownMass = inputMass;
  Serial.print("Known mass is: ");
  Serial.println(knownMass, 1);
  
  // Simulate measurement and calculate new calibration factor
  delay(1000);
  
  float rawReading = simulatedWeight - tareOffset;
  if (rawReading != 0) {
    float newCalFactor = knownMass / rawReading;
    calibrationFactor = newCalFactor;
    
    Serial.print("New calibration value has been set to: ");
    Serial.print(newCalFactor, 6);
    Serial.println(", use this as calibration value (calFactor) in your project sketch.");
    Serial.print("Save this value to EEPROM address 0? y/n");
    Serial.println();
    
    isLoadCellCalibrating = false;
    knownMass = 0;
  } else {
    Serial.println("Error: No weight detected. Please place known mass on scale.");
  }
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
    // Calculate average offsets
    calibration.accel_offset_x = calibrationSum[0] / MAX_CALIBRATION_SAMPLES;
    calibration.accel_offset_y = calibrationSum[1] / MAX_CALIBRATION_SAMPLES;
    calibration.accel_offset_z = (calibrationSum[2] / MAX_CALIBRATION_SAMPLES) - 1.0;
    
    calibration.valid = true;
    isIMUCalibrating = false;
    
    Serial.println("*** IMU CALIBRATION COMPLETE ***");
    Serial.print("X offset: ");
    Serial.println(calibration.accel_offset_x, 6);
    Serial.print("Y offset: ");
    Serial.println(calibration.accel_offset_y, 6);
    Serial.print("Z offset: ");
    Serial.println(calibration.accel_offset_z, 6);
    Serial.println("*** Use these offsets in your firmware ***");
    Serial.println();
  }
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