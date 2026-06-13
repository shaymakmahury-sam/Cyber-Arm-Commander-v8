#  This is the C++(CPP) Script for the Robotic Arm Commander

#  How to Upload & Link It

Open your Arduino IDE, paste the code above, and upload it to your board (Uno, Mega, Nano, etc.).

Double-check your wiring: Wire your 4 servos to Digital PWM Pins 3, 5, 6, and 9.

Crucial: Make sure your Python app is closed before uploading code from the Arduino IDE (they cannot share the COM port at the exact same millisecond).

Once uploaded, open your Python app, select the correct COM port, click Establish Neural Link, and watch your hardware sync with your 3D digital twin!

#include <Servo.h>

// --- CONFIGURATION ---
#define BAUD_RATE 128000
#define NUM_SERVOS 4

// Define your physical Arduino PWM pins here
const int servoPins[NUM_SERVOS] = {3, 5, 6, 9}; 

Servo myServos[NUM_SERVOS];

// Array to store target and current positions for smooth interpolation
int targetAngles[NUM_SERVOS] = {90, 90, 90, 90};
int currentAngles[NUM_SERVOS] = {90, 90, 90, 90};

// Speed control: Higher = faster, Lower = smoother/slower movement
const int moveSpeed = 3; 

void setup() {
  Serial.begin(BAUD_RATE);
  
  // Initialize servos and set them to default home position (90 degrees)
  for (int i = 0; i < NUM_SERVOS; i++) {
    myServos[i].attach(servoPins[i]);
    myServos[i].write(currentAngles[i]);
  }
}

void loop() {
  // 1. Check for incoming serial commands from Python
  readSerialCommands();

  // 2. Smoothly update servo positions (prevents jerky movements)
  updateServoPositions();
  
  delay(15); // Small delay to control the update pacing
}

void readSerialCommands() {
  while (Serial.available() > 0) {
    // Read string until newline character '\n'
    String data = Serial.readStringUntil('\n');
    data.trim(); // Remove any accidental whitespace
    
    // Validate command structure (Must start with 'S', contain ':')
    if (data.startsWith("S") && data.indexOf(':') != -1) {
      int colonIndex = data.indexOf(':');
      
      // Parse the Servo Index and the Target Angle
      int servoIdx = data.substring(1, colonIndex).toInt();
      int angle = data.substring(colonIndex + 1).toInt();
      
      // Safety limits: Ensure index is valid and angle is within 0-180
      if (servoIdx >= 0 && servoIdx < NUM_SERVOS) {
        targetAngles[servoIdx] = constraintAngle(angle);
      }
    }
  }
}

void updateServoPositions() {
  for (int i = 0; i < NUM_SERVOS; i++) {
    if (currentAngles[i] < targetAngles[i]) {
      currentAngles[i] += moveSpeed;
      if (currentAngles[i] > targetAngles[i]) currentAngles[i] = targetAngles[i];
    } 
    else if (currentAngles[i] > targetAngles[i]) {
      currentAngles[i] -= moveSpeed;
      if (currentAngles[i] < targetAngles[i]) currentAngles[i] = targetAngles[i];
    }
    
    // Write updated increment to the physical hardware pin
    myServos[i].write(currentAngles[i]);
  }
}

int constraintAngle(int angle) {
  if (angle < 0) return 0;
  if (angle > 180) return 180;
  return angle;
}
