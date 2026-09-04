#include <Stepper.h>

// # steps for full 360-degree rotation, change to fit your motor
int SPR = 2048;

// set a speed for the stepper motor
int rpm = 10;

// initialize stepper library on pins 8 - 11
// pin order IN1, IN3, IN2, IN4
Stepper SRV1 (SPR, 8, 10, 9, 11);
Stepper SRV2 (SPR, 4, 5, 6, 7);
Stepper SRV2 (SPR, 0, 1, 2, 3);

void setup() {
  SRV1.setSpeed(rpm);
}

void loop() {
  // make a full revolution in one direction
  SRV1.step(SPR);
  delay(100);

  // make a full revolution in the opposite direction
  SRV1.step(-SPR/2);
  delay(100);
}