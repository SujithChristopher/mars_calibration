/*
  IMU Calibration Program for Arduino Nano 33 BLE
  
  This program reads accelerometer data from the LSM9DS1 sensor
  and calculates yaw, pitch, and roll angles. It also provides
  calibration functionality to find and set zero offsets.
  
  Commands:
  - 'c': Start calibration (place device flat and still)
  - 'r': Reset offsets to zero
  - 's': Save current offsets to EEPROM
  - 'l': Load offsets from EEPROM
*/

#include <Arduino_LSM9DS1.h>
#include <EEPROM.h>

// Calibration data structure
struct CalibrationData {
  float accel_offset_x;
  float accel_offset_y;
  float accel_offset_z;
  bool valid;
};

// EEPROM address for calibration data
const int EEPROM_ADDRESS = 0;

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
  while (!Serial);
  
  delay(1000);
  
  Serial.println("=== IMU Calibration Program ===");
  Serial.println("Arduino Nano 33 BLE - LSM9DS1 Sensor");
  Serial.println();
  
  // Initialize the IMU
  if (!IMU.begin()) {
    Serial.println("Failed to initialize IMU!");
    while (1);
  }
  
  Serial.println("IMU initialized successfully!");
  Serial.print("Accelerometer sample rate = ");
  Serial.print(IMU.accelerationSampleRate());
  Serial.println(" Hz");
  Serial.println();
  
  // Load calibration from EEPROM
  loadCalibration();
  
  Serial.println("Commands:");
  Serial.println("  'c' - Start calibration (place device flat and level)");
  Serial.println("  'r' - Reset offsets to zero");
  Serial.println("  's' - Save current offsets to EEPROM");
  Serial.println("  'l' - Load offsets from EEPROM");
  Serial.println();
  Serial.println("Output format: AX,AY,AZ,ROLL,PITCH,YAW,OFFSET_X,OFFSET_Y,OFFSET_Z");
  Serial.println();
  
  // Wait a bit before starting
  delay(2000);
}

void loop() {
  // Handle serial commands
  handleSerialCommands();
  
  // Read accelerometer data
  float ax, ay, az;
  if (IMU.accelerationAvailable()) {
    IMU.readAcceleration(ax, ay, az);
    
    // Apply low-pass filter for smoothing
    filteredAccel[0] = filterAlpha * filteredAccel[0] + (1 - filterAlpha) * ax;
    filteredAccel[1] = filterAlpha * filteredAccel[1] + (1 - filterAlpha) * ay;
    filteredAccel[2] = filterAlpha * filteredAccel[2] + (1 - filterAlpha) * az;
    
    // Apply calibration offsets
    float calibrated_ax = filteredAccel[0] - calibration.accel_offset_x;
    float calibrated_ay = filteredAccel[1] - calibration.accel_offset_y;
    float calibrated_az = filteredAccel[2] - calibration.accel_offset_z;
    
    // Calculate angles (in degrees)
    float roll = calculateRoll(calibrated_ax, calibrated_ay, calibrated_az);
    float pitch = calculatePitch(calibrated_ax, calibrated_ay, calibrated_az);
    float yaw = calculateYaw(calibrated_ax, calibrated_ay, calibrated_az);
    
    // Handle calibration process
    if (isCalibrating) {
      processCalibration(ax, ay, az);
    }
    
    // Print data at regular intervals
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
    }
  }
  
  delay(10); // Small delay to prevent overwhelming the serial
}

float calculateRoll(float ax, float ay, float az) {
  // Roll calculation using accelerometer
  return atan2(ay, sqrt(ax * ax + az * az)) * 180.0 / PI;
}

float calculatePitch(float ax, float ay, float az) {
  // Pitch calculation using accelerometer
  return atan2(-ax, sqrt(ay * ay + az * az)) * 180.0 / PI;
}

float calculateYaw(float ax, float ay, float az) {
  // Note: True yaw cannot be determined from accelerometer alone
  // This provides a rough estimate based on tilt
  // For accurate yaw, magnetometer or gyroscope integration is needed
  float magnitude = sqrt(ax * ax + ay * ay + az * az);
  if (magnitude > 0.5) { // Avoid division by zero
    return atan2(ax, ay) * 180.0 / PI;
  }
  return 0.0;
}

void handleSerialCommands() {
  if (Serial.available() > 0) {
    char command = Serial.read();
    
    switch (command) {
      case 'c':
        startCalibration();
        break;
        
      case 'r':
        resetCalibration();
        break;
        
      case 's':
        saveCalibration();
        break;
        
      case 'l':
        loadCalibration();
        break;
        
      default:
        // Ignore other characters
        break;
    }
  }
}

void startCalibration() {
  Serial.println("*** STARTING IMU CALIBRATION ***");
  Serial.println("Place the device on a flat, level surface and keep it still.");
  Serial.println("Calibration will take about 10 seconds...");
  
  isCalibrating = true;
  calibrationSamples = 0;
  calibrationSum[0] = 0;
  calibrationSum[1] = 0;
  calibrationSum[2] = 0;
  
  delay(2000); // Give user time to position device
  Serial.println("Calibration started... Keep device still!");
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
    
    // For Z-axis, we expect 1g (9.81 m/s²) when device is flat
    // The LSM9DS1 outputs acceleration in g units, so we expect ~1.0
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
    Serial.println("Send 's' to save these offsets to EEPROM");
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

void saveCalibration() {
  if (!calibration.valid) {
    Serial.println("No valid calibration data to save. Run calibration first.");
    return;
  }
  
  EEPROM.put(EEPROM_ADDRESS, calibration);
  Serial.println("Calibration data saved to EEPROM");
}

void loadCalibration() {
  CalibrationData loaded;
  EEPROM.get(EEPROM_ADDRESS, loaded);
  
  // Check if loaded data is valid
  if (loaded.valid && 
      abs(loaded.accel_offset_x) < 2.0 && 
      abs(loaded.accel_offset_y) < 2.0 && 
      abs(loaded.accel_offset_z) < 2.0) {
    
    calibration = loaded;
    Serial.println("Calibration data loaded from EEPROM:");
    Serial.print("X offset: ");
    Serial.println(calibration.accel_offset_x, 6);
    Serial.print("Y offset: ");
    Serial.println(calibration.accel_offset_y, 6);
    Serial.print("Z offset: ");
    Serial.println(calibration.accel_offset_z, 6);
  } else {
    Serial.println("No valid calibration data found in EEPROM");
    calibration.accel_offset_x = 0.0;
    calibration.accel_offset_y = 0.0;
    calibration.accel_offset_z = 0.0;
    calibration.valid = false;
  }
}