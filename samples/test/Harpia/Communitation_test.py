import time
import sys
from lightcon.harpia import Harpia


#serialNumber = "M24100"
#base_adress = "http://localhost:20050/v1/"

ip_address = "192.168.1.134"

#initialize connection to Harpia
harpia = Harpia(ip_address)
# check if connection is established
if not harpia.connected:
    sys.exit("Could not connect to Harpia")

# test shutter
print("Pump open")
harpia.open_pump_shutter()

"""
print("Third beam open")
harpia.open_third_beam_shutter()
time.sleep(2)
print("Third beam close")
harpia.close_third_beam_shutter()
"""



# test delay line
# Read actual delay line position
current = harpia.delay_line_actual_delay()
print("Current delay:", current, "ps")

# Move to 1 ps
target_delay = 1.0

print("Moving to", target_delay, "ps")
harpia.set_delay_line_target_delay(target_delay)

# Wait for the delay line to reach the target position
while True:
    current = harpia.delay_line_actual_delay()
    print("Current delay:", current, "ps")
    if abs(current - target_delay) < 0.001:  # tolerance of 1 fs = 0.001 ps
        break
    time.sleep(0.2)

print("Delay reached!")













