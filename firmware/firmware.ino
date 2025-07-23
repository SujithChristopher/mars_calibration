#include "HX711.h"

#define DOUT 2  // HX711 data pin
#define CLK  3  // HX711 clock pin

HX711 scale;

float calibration_factor = -8029.94; // Adjust this as per your setup

// IMU calibration offsets (to be updated after IMU calibration)
float accel_offset_x = 0.050100;
float accel_offset_y = -0.029800;
float accel_offset_z = 0.080200;

// Simulated IMU variables for Teensy (no physical IMU attached)
bool imu_simulation_enabled = true;
float sim_tilt_x = 0.0;
float sim_tilt_y = 0.0;
float sim_noise_level = 0.01;
unsigned long lastSimUpdate = 0;

void setup() {
  Serial.begin(115200);
  while (!Serial && millis() < 3000); // Wait for serial on Teensy
  
  // Initialize HX711
  scale.begin(DOUT, CLK);
  scale.set_scale(calibration_factor);
  scale.tare();  // Reset the scale to 0

  // Initialize random seed for simulation
  randomSeed(analogRead(A0) * millis());

  Serial.println("=== Load Cell & IMU System (Teensy 4.1) ===");
  Serial.println("HX711 Load Cell initialized");
  
  if (imu_simulation_enabled) {
    Serial.println("IMU: Simulation mode enabled (no physical sensor)");
    Serial.println("IMU offsets applied from calibration:");
    Serial.print("  X offset: "); Serial.println(accel_offset_x, 6);
    Serial.print("  Y offset: "); Serial.println(accel_offset_y, 6);
    Serial.print("  Z offset: "); Serial.println(accel_offset_z, 6);
  } else {
    Serial.println("IMU: Physical sensor mode (not implemented)");
  }
  
  Serial.println("Output format: WEIGHT,PITCH,ROLL,YAW");
  Serial.println();
  
  delay(2000);
}

void loop() {
  // Read load cell data
  float weight = scale.get_units(5); // average over 5 readings
  
  // Read and process IMU data (simulated or real)
  float pitch = 0.0, roll = 0.0, yaw = 0.0;
  
  if (imu_simulation_enabled) {
    // Update simulation parameters
    updateSimulation();
    
    // Get simulated accelerometer data
    float ax, ay, az;
    getSimulatedAcceleration(&ax, &ay, &az);
    
    // Apply calibration offsets
    float calibrated_ax = ax - accel_offset_x;
    float calibrated_ay = ay - accel_offset_y;
    float calibrated_az = az - accel_offset_z;
    
    // Calculate angles (in degrees)
    roll = calculateRoll(calibrated_ax, calibrated_ay, calibrated_az);
    pitch = calculatePitch(calibrated_ax, calibrated_ay, calibrated_az);
    yaw = calculateYaw(calibrated_ax, calibrated_ay, calibrated_az);
  }
  
  // Output data in CSV format: WEIGHT,PITCH,ROLL,YAW
  Serial.print(weight, 2);
  Serial.print(",");
  Serial.print(pitch, 2);
  Serial.print(",");
  Serial.print(roll, 2);
  Serial.print(",");
  Serial.print(yaw, 2);
  Serial.println();

  delay(100); // Reduced delay for more responsive output
}

void updateSimulation() {
  // Update simulated tilts slowly over time
  if (millis() - lastSimUpdate >= 3000) { // Update every 3 seconds
    sim_tilt_x += random(-10, 11) * 0.005;    // Small random changes
    sim_tilt_y += random(-10, 11) * 0.005;
    
    // Limit tilt ranges to realistic values
    sim_tilt_x = constrain(sim_tilt_x, -0.2, 0.2);
    sim_tilt_y = constrain(sim_tilt_y, -0.2, 0.2);
    
    lastSimUpdate = millis();
  }
}

void getSimulatedAcceleration(float* ax, float* ay, float* az) {
  // Generate noise
  float noise_x = (random(-1000, 1001) / 1000.0) * sim_noise_level;
  float noise_y = (random(-1000, 1001) / 1000.0) * sim_noise_level;
  float noise_z = (random(-1000, 1001) / 1000.0) * sim_noise_level;
  
  // Simulate accelerometer readings with tilt and small base offsets
  *ax = 0.02 + sim_tilt_x + noise_x;      // Small base offset + tilt + noise
  *ay = -0.01 + sim_tilt_y + noise_y;     // Small base offset + tilt + noise  
  *az = 1.0 + 0.03 + noise_z;             // 1g + small offset + noise
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
