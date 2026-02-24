#include <Stepper.h>
String id = "ArduinoUnoRev3"; //do not change that
// # steps for full 360-degree rotation, change to fit your motor
int SPR = 2048;

// set a speed for the stepper motor
int rpm = 10;

// initialize stepper library on pins 8 - 11
// pin order IN1, IN3, IN2, IN4
Stepper SRV1 (SPR, 8, 10, 9, 11); // 8, 10, 9, 11
Stepper SRV2 (SPR, 4, 6, 5, 7); // 4, 5, 6, 7
Stepper SRV3 (SPR, 12, 2, 13, 3);

void setup() {
  Serial.begin(115200);
  SRV1.setSpeed(rpm);
  SRV2.setSpeed(rpm);
  SRV3.setSpeed(rpm);
}

void processCommand(String command){

  int equalPos = command.indexOf('=');

  if (equalPos != -1) {
    String servoName = command.substring(0,equalPos);

    int servoPort = 0;
    if (servoName == "SRV1") {
       Serial.println("Servoport1 selected");
       int value = command.substring(equalPos+1,command.length()).toInt();
       SRV1.step(value);
    }
    else if (servoName == "SRV2") {
       Serial.println("Servoport2 selected");
       int value = command.substring(equalPos+1,command.length()).toInt();
       SRV2.step(value);
    }
    else if (servoName == "SRV3") {
       Serial.println("Servoport3 selected");
       int value = command.substring(equalPos+1,command.length()).toInt();
       SRV3.step(value);
    }
  }}
void loop() {
  // run repeatedly, check if python sent something:
  
  if (Serial.available()) {
  
  // Serial.println(Serial.available());
  String input = Serial.readString();
  // Serial.println(input);
  input.trim(); // To wash the string from whitespace, termination character..

  if (input == "ID?") {
    Serial.println(id);
  }
  else {
    int curs = 0;
    int delimPos = 0;
    while (delimPos != -1) {
      delimPos = input.indexOf(',', curs);
      String command = input.substring(curs,delimPos);
      processCommand(command);
      curs = delimPos+1;
    }
    //Serial.println("done");
  }
  }
}