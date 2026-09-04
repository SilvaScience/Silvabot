#include <Servo.h>
String id = "ArduinoUnoRev3_55639303135351D0B172"; //do not change that
Servo servo;
int servoPorts[3] = {8,12,13};
bool shutterstatus[3] {false, false, false}; 
int feedbackPin = 2;
char delimiter = ',';
bool status;
int idx;

void setup() {
  // put your setup code here, to run once:
  pinMode(feedbackPin, INPUT);
  pinMode(servoPorts, OUTPUT);
  Serial.begin(115200);
  Serial.print("Initialize ");
}

String val;
char msg[128];
int angle;
int currentAngle;
int diff;
int direction;
long dutyScale = 1000;
long unitsFC = 360;
long dcMin = 29;
long dcMax = 971;
long q2min = unitsFC / 4;
long q3max = q2min * 3;

int readFeedback(int pin) {
  long tHigh, tLow, tCycle, turns;
  while (1) {
    tHigh = pulseIn(pin, HIGH);
    tLow = pulseIn(pin, LOW);
    tCycle = tHigh + tLow;
    if (tLow == 0) 
      continue;
    if ((tCycle > 1000) && (tCycle < 1200))
      break;
  }
  long dc = (dutyScale * tHigh) / tCycle;
  long theta = (unitsFC - 1) - ((dc - dcMin) * unitsFC) / (dcMax - dcMin + 1);
  if (theta < 0) {
    Serial.println("Error");
  }
  return theta;
}

void processCommand(String command){

  int equalPos = command.indexOf('=');

  if (equalPos != -1) {
    String servoName = command.substring(0,equalPos);

    int servoPort = 0;
    if (servoName == "SRV1") {
       servoPort = servoPorts[0];
       Serial.println("Servoport1 selected");
    }
    else if (servoName == "SRV2") {
       servoPort = servoPorts[1];
       idx = 1;
       // FeedBackServo(FEEDBACK_PINs[1]);
       Serial.println("Servoport2 selected");
    }
    else if (servoName == "SRV3") {
       servoPort = servoPorts[2];
       idx = 2;
       // Serial.println("Servoport3 selected");
    }

    if (servoPort != 0) {
        if (servoPort == servoPorts[0] ) {  //filter wheel with feedback 
          servo.attach(servoPort);
          direction = 1;
          while (direction != 0) {          
          int angle = command.substring(equalPos+1,command.length()).toInt();
          angle = angle % 360;
          currentAngle = readFeedback(feedbackPin);
          diff = (currentAngle - angle + 180) % 360 - 180;
          diff = diff < -180 ? diff + 360 : diff;

          // direction
          if (abs(diff) < 1) {
            direction = 0;
            } 
          else {
              if (diff > 0) {
                direction = 1;
              } else if (diff < 0) {
                direction = -1;
              }
            }

          // rotation speed
          int speed = 10;
          if (abs(diff) < 2) {
            direction = 0;
          } else if (abs(diff) < 20) {
            speed = 35;
          } else {
            speed = 100;
          }

          // rotate
          if (direction == 1) {
            servo.writeMicroseconds(1500 - speed);
            delay(100);
          } 
          else if (direction == -1) {
            servo.writeMicroseconds(1500 + speed);
            delay(100);
          } 
          else {
            servo.writeMicroseconds(1500);
          }
	      }
        servo.detach();}
	      else {
          servo.attach(servoPort);
          int value = command.substring(equalPos+1,command.length()).toInt();
          //Serial.print(value);
          //Serial.print(shutterstatus[idx]);
          if (value == 1)
          {
          servo.write(1600);
          } else {
          servo.write(1400);
          }
          delay(200);
          servo.detach(); 
        }   
    } 
  } 
}


void loop() {
  // put your main code here, to run repeatedly:
  int currentAngle = readFeedback(feedbackPin);
  diff = (currentAngle - angle + 180) % 360 - 180;
  diff = diff < -180 ? diff + 360 : diff;
  
  //while (Serial.available() == 0) {
  //  Serial.print("Now angle: ");
  //  Serial.println(feedback.Angle());
  //  delay(1000);
  //}
  if (Serial.available() > 0) {
  
  Serial.println(Serial.available());
  String input = Serial.readString();
  Serial.println(input);
  input.trim(); // To wash the string from whitespace, termination character..

  if (input == "ID?") {
    Serial.println(id);
  }
  else if (input == "pos?") {
    currentAngle = readFeedback(feedbackPin);
    sprintf(msg,"Current angle: %d", currentAngle);
    Serial.println(msg);
    servo.attach(servoPorts[1]);
    val = servo.read(); 
    servo.detach();
    Serial.println(val);
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






    
