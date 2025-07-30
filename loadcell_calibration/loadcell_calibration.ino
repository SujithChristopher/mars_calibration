// Load Cell Simulator for Arduino Nano 33 BLE
// Simulates HX711 load cell behavior without actual hardware
// Baud rate: 115200

// For Arduino Nano 33 BLE compatibility
#if defined(ARDUINO_ARCH_MBED_NANO) || defined(ARDUINO_ARCH_MBED)
  // Nano 33 BLE specific includes if needed
  #include <mbed.h>
#endif

// Simulation variables
float simulatedWeight = 0.0;
float calibrationFactor = 1.0;
float tareOffset = 0.0;
bool isTared = false;
bool isCalibrating = false;
float knownMass = 0.0;
unsigned long lastPrintTime = 0;
const unsigned long printInterval = 500; // Print every 500ms

// Simulate noise and drift
float baseNoise = 0.0;
unsigned long noiseTime = 0;

void setup() {
  Serial.begin(115200);
  delay(100);
  
  Serial.println();
  Serial.println("=== Load Cell Simulator ===");
  Serial.println("Starting...");
  delay(1000);
  
  // Simulate startup sequence
  Serial.println("Initializing load cell...");
  delay(500);
  Serial.println("Startup is complete");
  
  // Add some initial noise - use different analog pin for Nano 33 BLE
  #if defined(ARDUINO_ARCH_MBED_NANO) || defined(ARDUINO_ARCH_MBED)
    randomSeed(analogRead(A1)); // Use A1 for Nano 33 BLE
  #else
    randomSeed(analogRead(A0)); // Use A0 for other boards
  #endif
  
  Serial.println();
  Serial.println("Commands:");
  Serial.println("  't' - Tare the scale");
  Serial.println("  'r' - Start calibration");
  Serial.println("  Place weights on scale and enter mass for calibration");
  Serial.println();
}

void loop() {
  // Generate simulated load cell reading
  generateSimulatedReading();
  
  // Print simulated weight reading
  if (millis() - lastPrintTime > printInterval) {
    float displayValue = (simulatedWeight - tareOffset) * calibrationFactor;
    Serial.println(displayValue, 2);
    lastPrintTime = millis();
  }
  
  // Handle serial commands
  handleSerialCommands();
  
  // Small delay to prevent overwhelming the serial
  delay(10);
}

void generateSimulatedReading() {
  // Generate some realistic noise and drift
  if (millis() - noiseTime > 100) {
    baseNoise = random(-50, 50) / 100.0; // ±0.5 unit noise
    noiseTime = millis();
  }
  
  // Simulate weight changes (you can manually add weight here)
  // For demo purposes, we'll add a small drift
  float drift = sin(millis() / 10000.0) * 2.0; // Slow drift
  
  simulatedWeight = baseNoise + drift;
  
  // If we're in calibration and known mass is set, simulate having weight on scale
  if (isCalibrating && knownMass > 0) {
    simulatedWeight += knownMass / calibrationFactor; // Raw value that would produce known mass
  }
}

void handleSerialCommands() {
  if (Serial.available() > 0) {
    if (isCalibrating && knownMass == 0) {
      // We're waiting for known mass input during calibration
      float inputMass = Serial.parseFloat();
      if (inputMass > 0) {
        knownMass = inputMass;
        Serial.print("Known mass is: ");
        Serial.println(knownMass, 1);
        
        // Simulate measurement and calculate new calibration factor
        delay(1000); // Simulate measurement time
        
        float rawReading = simulatedWeight - tareOffset;
        if (rawReading != 0) {
          float newCalFactor = knownMass / rawReading;
          calibrationFactor = newCalFactor;
          
          Serial.print("New calibration value has been set to: ");
          Serial.print(newCalFactor, 6);
          Serial.println(", use this as calibration value (calFactor) in your project sketch.");
          Serial.print("Save this value to EEPROM adress 0");
          Serial.println("? y/n");
          
          isCalibrating = false;
          knownMass = 0;
        } else {
          Serial.println("Error: No weight detected. Please place known mass on scale.");
        }
      }
    } else {
      // Handle single character commands
      char command = Serial.read();
      
      switch (command) {
        case 't':
          performTare();
          break;
          
        case 'r':
          startCalibration();
          break;
          
        case 'y':
          if (!isCalibrating) {
            Serial.println("Calibration value saved to EEPROM.");
          }
          break;
          
        case 'n':
          if (!isCalibrating) {
            Serial.println("Calibration value not saved.");
          }
          break;
          
        default:
          // Ignore other characters
          break;
      }
    }
  }
}

void performTare() {
  Serial.println("Performing tare...");
  delay(500); // Simulate tare time
  
  tareOffset = simulatedWeight;
  isTared = true;
  
  Serial.println("Tare complete");
}

void startCalibration() {
  Serial.println("***");
  Serial.println("Start calibration:");
  Serial.println("Place the load cell an a level stable surface.");
  Serial.println("Remove any load applied to the load cell.");
  Serial.println("Send 't' from serial monitor to set the tare offset.");
  
  isCalibrating = true;
  knownMass = 0;
  
  // Wait for tare before proceeding
  waitForTare();
}

void waitForTare() {
  bool tareCompleted = false;
  
  while (!tareCompleted && isCalibrating) {
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

// Additional function to simulate placing weights (for testing)
void simulateWeightPlacement(float weight) {
  simulatedWeight += weight / calibrationFactor;
}

// Function to simulate removing weights
void simulateWeightRemoval() {
  simulatedWeight = baseNoise + sin(millis() / 10000.0) * 2.0; // Back to base reading
}