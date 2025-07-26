/*
  3-IMU Sequential Calibration Program for Teensy 4.1
  
  This program calibrates 3 sequential MPU6050 IMU sensors connected to I2C pins 18/19.
  Used for sequential calibration of 3 different IMUs:
  - IMU 1: Pitch + Roll offsets (angle_offset1, angle_offset2)
  - IMU 2: Pitch + Roll offsets (angle_offset3, angle_offset4)  
  - IMU 3: Roll only offset (angle_offset5)
  
  Hardware:
  - Teensy 4.1
  - MPU6050 sensors connected to I2C: Pin 18 (SDA), Pin 19 (SCL)
  
  Commands:
  - 'c': Start calibration (place device flat and still)
  - 'r': Reset offsets to zero
  - 'RESET': Software reset command
*/

#include "Wire.h"
#include <MPU6050_light.h>
#include <math.h>

const float RAD2DEG = 180.0f / PI;

// I2C Configuration for Teensy 4.1
#define SDA_PIN 18
#define SCL_PIN 19

// Alternative: Try default I2C pins if custom pins don't work
// Default Teensy 4.1 I2C: SDA=18, SCL=19 (Wire) or SDA=17, SCL=16 (Wire1)

MPU6050 mpu(Wire);
bool imuConnected = false;

// Calibration data structure
struct CalibrationData {
  float accel_offset_x;
  float accel_offset_y;
  float accel_offset_z;
  bool valid;
};

// Calibration variables
CalibrationData calibration;
bool isCalibrating = false;
int calibrationSamples = 0;
const int MAX_CALIBRATION_SAMPLES = 100;
float calibrationSum[3] = {0, 0, 0};

// Timing variables
unsigned long lastPrintTime = 0;
const unsigned long printInterval = 100; // Print every 100ms

// Filter variables for smoothing
float filteredAccel[3] = {0, 0, 0};
const float filterAlpha = 0.8; // Low-pass filter coefficient

void setup() {
  Serial.begin(115200);
  while (!Serial && millis() < 3000); // Wait up to 3 seconds for serial
  
  delay(1000);
  
  Serial.println("=== 3-IMU Sequential Calibration Program ===");
  Serial.println("Teensy 4.1 - MPU6050 IMU on I2C Pins 18/19");
  Serial.println();
  
  // Initialize IMU using working template
  imuSetup();
  
  Serial.println();
  Serial.println("3-IMU Sequential Calibration Workflow:");
  Serial.println("  1. Connect IMU 1, calibrate pitch+roll -> angle_offset1, angle_offset2");
  Serial.println("  2. Connect IMU 2, calibrate pitch+roll -> angle_offset3, angle_offset4");
  Serial.println("  3. Connect IMU 3, calibrate roll only -> angle_offset5");
  Serial.println();
  
  // Initialize calibration data
  calibration.accel_offset_x = 0.0;
  calibration.accel_offset_y = 0.0;
  calibration.accel_offset_z = 0.0;
  calibration.valid = false;
  
  Serial.println("Commands:");
  Serial.println("  'c' - Start calibration (place device flat and level)");
  Serial.println("  'r' - Reset offsets to zero");
  Serial.println("  'RESET' - Software reset Teensy for IMU switching");
  Serial.println();
  Serial.println("Output format: AX,AY,AZ,ROLL,PITCH,YAW,OFFSET_X,OFFSET_Y,OFFSET_Z");
  Serial.println();
  
  // Wait a bit before starting
  delay(2000);
}

void imuSetup() {
  Serial.println("=== Trying I2C Configuration 1: Custom Pins 18/19 ===");
  
  // Try custom pins first
  Wire.setSDA(SDA_PIN);
  Wire.setSCL(SCL_PIN);
  Wire.begin();
  Wire.setClock(100000); // Start with slower 100kHz speed for better reliability
  
  Serial.println("I2C initialized on pins 18(SDA) and 19(SCL)");
  Serial.println("Scanning I2C bus for devices...");
  
  // Scan I2C bus to find devices
  scanI2C();
  
  // Try to connect with custom pins
  if (tryMPU6050Connection()) {
    return; // Success!
  }
  
  Serial.println("=== Trying I2C Configuration 2: Default Pins ===");
  
  // Try default I2C pins
  Wire.end(); // End current I2C
  Wire.begin(); // Use default pins
  Wire.setClock(100000);
  
  Serial.println("I2C initialized with default pins");
  Serial.println("Scanning I2C bus for devices...");
  
  // Scan again with default pins
  scanI2C();
  
  // Try to connect with default pins
  if (tryMPU6050Connection()) {
    return; // Success!
  }
  
  Serial.println("*** ERROR: Could not connect to MPU6050 with any configuration! ***");
  Serial.println("Check wiring and power:");
  Serial.println("  VCC -> 3.3V (NOT 5V!)");
  Serial.println("  GND -> GND");
  Serial.println("  SDA -> Pin 18 (or try Pin 17)");
  Serial.println("  SCL -> Pin 19 (or try Pin 16)");
  Serial.println("  Pull-up resistors: 4.7kΩ on SDA and SCL lines");
  imuConnected = false;
}

bool tryMPU6050Connection() {
  Serial.println("Trying to connect to MPU6050...");
  
  // Try different addresses
  uint8_t addresses[] = {0x68, 0x69}; // MPU6050 can be at 0x68 or 0x69
  
  for (int i = 0; i < 2; i++) {
    Serial.print("Trying address 0x");
    Serial.print(addresses[i], HEX);
    Serial.println("...");
    
    mpu.setAddress(addresses[i]);
    byte status = mpu.begin();
    
    if (status == 0) {
      Serial.print("MPU6050 connected successfully at address 0x");
      Serial.print(addresses[i], HEX);
      Serial.println("!");
      imuConnected = true;
      
      // Calculate offsets (calibration for gyroscope)
      Serial.println("Calculating gyroscope offsets, do not move MPU6050");
      delay(1000);
      mpu.calcOffsets(); // This will calibrate gyroscope and accelerometer offsets
      Serial.println("MPU6050 ready for use!");
      return true;
    } else {
      Serial.print("Failed at 0x");
      Serial.print(addresses[i], HEX);
      Serial.print(" (status: ");
      Serial.print(status);
      Serial.println(")");
    }
  }
  
  return false;
}

void scanI2C() {
  int deviceCount = 0;
  Serial.println("Scanning I2C addresses from 0x01 to 0x7F...");
  
  for (uint8_t address = 1; address < 127; address++) {
    Wire.beginTransmission(address);
    uint8_t error = Wire.endTransmission();
    
    if (error == 0) {
      Serial.print("I2C device found at address 0x");
      if (address < 16) Serial.print("0");
      Serial.print(address, HEX);
      
      // Identify common devices
      if (address == 0x68 || address == 0x69) {
        Serial.print(" (likely MPU6050/MPU9250)");
      } else if (address == 0x1E) {
        Serial.print(" (likely HMC5883L magnetometer)");
      } else if (address == 0x77) {
        Serial.print(" (likely BMP180/BMP280)");
      }
      Serial.println();
      deviceCount++;
    }
  }
  
  if (deviceCount == 0) {
    Serial.println("No I2C devices found!");
    Serial.println("Check wiring and power connections.");
  } else {
    Serial.print("Found ");
    Serial.print(deviceCount);
    Serial.println(" I2C device(s).");
  }
  Serial.println();
}

void loop() {
  // Handle serial commands
  handleSerialCommands();
  
  // Only proceed if IMU is connected
  if (!imuConnected) {
    delay(1000);
    return;
  }
  
  updateImu();
}

void updateImu() {
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
  
  // Calculate angles (in degrees) using MPU6050_light library functions
  float roll = mpu.getAngleX();  // Roll angle from library
  float pitch = mpu.getAngleY(); // Pitch angle from library  
  float yaw = mpu.getAngleZ();   // Yaw angle from library
  
  // Handle calibration process (use raw unfiltered data for calibration)
  if (isCalibrating) {
    processCalibration(ax, ay, az);
  }
  
  // Print data at regular intervals - ALWAYS print data
  if (millis() - lastPrintTime >= printInterval) {
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
    
    lastPrintTime = millis();
    
    // Debug info during calibration
    if (isCalibrating) {
      Serial.print("CAL: Sample ");
      Serial.print(calibrationSamples);
      Serial.print("/");
      Serial.print(MAX_CALIBRATION_SAMPLES);
      Serial.print(" Raw: ");
      Serial.print(ax, 4);
      Serial.print(",");
      Serial.print(ay, 4);
      Serial.print(",");
      Serial.print(az, 4);
      Serial.println();
    }
  }
  
  delay(10); // Small delay to prevent overwhelming the serial
}


void handleSerialCommands() {
  if (Serial.available() > 0) {
    String input = Serial.readString();
    input.trim();
    
    if (input == "c") {
      startCalibration();
    }
    else if (input == "r") {
      resetCalibration();
    }
    else if (input == "RESET") {
      handleSoftwareReset();
    }
    else {
      // Check for single character commands for backwards compatibility
      if (input.length() == 1) {
        char command = input.charAt(0);
        switch (command) {
          case 'c':
            startCalibration();
            break;
          case 'r':
            resetCalibration();
            break;
        }
      }
    }
  }
}

void startCalibration() {
  Serial.println("*** STARTING REAL IMU CALIBRATION ***");
  Serial.println("Place the device on a flat, level surface and keep it still.");
  Serial.println("Calibration will take about 10 seconds...");
  Serial.println("Calibration started... Keep device perfectly still!");
  
  isCalibrating = true;
  calibrationSamples = 0;
  calibrationSum[0] = 0;
  calibrationSum[1] = 0;
  calibrationSum[2] = 0;
  
  // No delay here - let the main loop continue processing
}

void processCalibration(float ax, float ay, float az) {
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
    
    // For Z-axis, we expect 1g when device is flat
    calibration.accel_offset_z = (calibrationSum[2] / MAX_CALIBRATION_SAMPLES) - 1.0;
    
    calibration.valid = true;
    isCalibrating = false;
    
    Serial.println("*** CALIBRATION COMPLETE ***");
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

void resetCalibration() {
  calibration.accel_offset_x = 0.0;
  calibration.accel_offset_y = 0.0;
  calibration.accel_offset_z = 0.0;
  calibration.valid = false;
  
  Serial.println("Calibration offsets reset to zero");
}

void handleSoftwareReset() {
  Serial.println("*** SOFTWARE RESET REQUESTED ***");
  Serial.println("Teensy will restart in 2 seconds...");
  Serial.println("Please wait for reconnection.");
  Serial.flush();
  
  delay(2000);
  
  // For Teensy 4.1, use the built-in reset function
  #if defined(__IMXRT1062__)  // Teensy 4.x
    SCB_AIRCR = 0x05FA0004;  // Request system reset
  #else
    // For other Teensy models, jump to reset vector
    void (*resetFunc)(void) = 0;
    resetFunc();
  #endif
}