/*
  IMU Simulation Program for Teensy 4.1
  
  This program simulates LSM9DS1 accelerometer data and provides
  calibration functionality to find zero offsets.
  
  Commands:
  - 'c': Start calibration (simulates device placed flat and still)
  - 'r': Reset offsets to zero
*/

// Simulation parameters
float sim_noise_level = 0.02;        // Noise amplitude
float sim_base_offset_x = 0.05;      // Simulated X offset
float sim_base_offset_y = -0.03;     // Simulated Y offset
float sim_base_offset_z = 0.08;      // Simulated Z offset (relative to 1g)
unsigned long sim_seed;

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

// Simulation state
float sim_tilt_x = 0.0;  // Simulated tilt angles
float sim_tilt_y = 0.0;
float sim_tilt_z = 0.0;
unsigned long lastTiltUpdate = 0;

void setup() {
  Serial.begin(115200);
  while (!Serial && millis() < 3000); // Wait up to 3 seconds for serial
  
  delay(1000);
  
  Serial.println("=== IMU Simulation Program ===");
  Serial.println("Teensy 4.1 - Simulated LSM9DS1 Sensor");
  Serial.println();
  
  // Initialize random seed
  sim_seed = analogRead(A0) * millis();
  randomSeed(sim_seed);
  
  Serial.println("Simulated IMU initialized successfully!");
  Serial.println("Sample rate = 104 Hz (simulated)");
  Serial.println();
  
  // Initialize calibration data
  calibration.accel_offset_x = 0.0;
  calibration.accel_offset_y = 0.0;
  calibration.accel_offset_z = 0.0;
  calibration.valid = false;
  
  Serial.println("Commands:");
  Serial.println("  'c' - Start calibration (simulates device flat and level)");
  Serial.println("  'r' - Reset offsets to zero");
  Serial.println();
  Serial.println("Output format: AX,AY,AZ,ROLL,PITCH,YAW,OFFSET_X,OFFSET_Y,OFFSET_Z");
  Serial.println();
  Serial.println("Simulation: Device will slowly drift and tilt to demonstrate IMU behavior");
  Serial.println();
  
  // Wait a bit before starting
  delay(2000);
}

void loop() {
  // Handle serial commands
  handleSerialCommands();
  
  // Update simulation
  updateSimulation();
  
  // Read simulated accelerometer data
  float ax, ay, az;
  readSimulatedAcceleration(&ax, &ay, &az);
  
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
  
  delay(10); // Small delay to prevent overwhelming the serial
}

void updateSimulation() {
  // Update simulated tilts slowly over time
  if (millis() - lastTiltUpdate >= 2000) { // Update every 2 seconds
    sim_tilt_x += random(-5, 6) * 0.01;    // Small random changes
    sim_tilt_y += random(-5, 6) * 0.01;
    sim_tilt_z += random(-3, 4) * 0.01;
    
    // Limit tilt ranges
    sim_tilt_x = constrain(sim_tilt_x, -0.3, 0.3);
    sim_tilt_y = constrain(sim_tilt_y, -0.3, 0.3);
    sim_tilt_z = constrain(sim_tilt_z, -0.2, 0.2);
    
    lastTiltUpdate = millis();
  }
}

void readSimulatedAcceleration(float* ax, float* ay, float* az) {
  // Generate noise
  float noise_x = (random(-1000, 1001) / 1000.0) * sim_noise_level;
  float noise_y = (random(-1000, 1001) / 1000.0) * sim_noise_level;
  float noise_z = (random(-1000, 1001) / 1000.0) * sim_noise_level;
  
  // Simulate accelerometer readings with tilt and offsets
  *ax = sim_base_offset_x + sim_tilt_x + noise_x;
  *ay = sim_base_offset_y + sim_tilt_y + noise_y;
  *az = 1.0 + sim_base_offset_z + sim_tilt_z + noise_z;  // 1g + offset + tilt
  
  // During calibration, simulate device being held still
  if (isCalibrating) {
    *ax = sim_base_offset_x + noise_x * 0.2;  // Reduced noise when still
    *ay = sim_base_offset_y + noise_y * 0.2;
    *az = 1.0 + sim_base_offset_z + noise_z * 0.2;
  }
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
        
      default:
        // Ignore other characters
        break;
    }
  }
}

void startCalibration() {
  Serial.println("*** STARTING IMU CALIBRATION (SIMULATED) ***");
  Serial.println("Simulating device placed on a flat, level surface...");
  Serial.println("Calibration will take about 10 seconds...");
  
  isCalibrating = true;
  calibrationSamples = 0;
  calibrationSum[0] = 0;
  calibrationSum[1] = 0;
  calibrationSum[2] = 0;
  
  delay(2000); // Simulate user positioning time
  Serial.println("Calibration started... Simulating stable readings!");
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