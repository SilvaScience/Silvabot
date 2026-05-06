String id = "ArduinoUnoRev3"; //do not change that

const int dir = 2;
const int imp = 3;
const int spr = 204;

void setup() {
Serial.begin(115200);
pinMode(dir, OUTPUT);
pinMode(imp, OUTPUT);
}

void processCommand(String command){

  int equalPos = command.indexOf('=');

  if (equalPos != -1) {
    String MotorName = command.substring(0,equalPos);

    int servoPort = 0;
    if (MotorName == "MTR1") {
       Serial.println("Motor1 selected");
       int value = command.substring(equalPos+1,command.length()).toInt();

       if (value < 0 ) {
          digitalWrite(dir, HIGH);}
       else {
          digitalWrite(dir, LOW);}

        for (int step = 0; step < abs(value); step++) {
            digitalWrite(imp, HIGH);
            delayMicroseconds(5000);
            digitalWrite(imp, LOW);
            delayMicroseconds(5000);
            }
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
