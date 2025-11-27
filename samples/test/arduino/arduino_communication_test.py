import serial
import time

# Change the port to your Arduino's serial port
port = "COM5"

ser = serial.Serial(port, 115200, timeout=1)
time.sleep(2)  # wait for Arduino reset

# Send command
ser.write(b"ID?\n")

# Read response
response = ser.readline().decode().strip()
print("Arduino ID:", response)

ser.close()