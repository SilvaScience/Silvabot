String deviceID = "ArduinoUnoRev3";  // Stored ID

void setup() {
  Serial.begin(9600);
  while (!Serial) { ; } // Needed for Leonardo/Micro; harmless for Uno
}

void loop() {
  // Check if Python sent something
  if (Serial.available()) {
    String cmd = Serial.readString();  // Read until newline

    cmd.trim();                                 // Remove whitespace

    if (cmd == "ID?") {
      Serial.println(deviceID);                 // Send ID back
    }
  }
}