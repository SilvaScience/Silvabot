import serial
import time

# Change the port to your Arduino's serial port
port = "COM8"

ser = serial.Serial(port, 115200, timeout=1)
time.sleep(2)  # wait for Arduino reset

# Send command
ser.write(b"ID?\n")

# Read response
response = ser.readline().decode().strip()
print("Arduino ID:", response)

#
shutter =1
set_angle = 400
command = 'SRV' + str(shutter) + '=' + str(set_angle)
ser.write(command.encode())
time.sleep(0.5)

response = ser.readline().decode().strip()
print("Arduino ID:", response)


ser.close()