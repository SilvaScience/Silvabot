from src.drivers.avaspec import *
from src.drivers.AvantesController import AvantesController
import time

# Initialize AvaSpec library
AVS_Init(0)       # 0 = USB

# Find connected spectrometers
n = AVS_GetNrOfDevices()

print("Number of devices:", n)

if n == 0:
    raise RuntimeError("No AvaSpec spectrometer found")

# Get device list
devices = AVS_GetList(n)
print(devices)

ans = AVS_GetHandleFromSerial("7617523SP")
print(ans)
handle = AVS_Init()
print(handle)

#AVS_PrepareMeasure(handle,measconf)
AC = AvantesController()
ans = AC.open_communication()
print(ans)
sn = AC.serial_number
print(sn)
wl = AC.wavelengths
print(wl)
print(len(wl))
AC.set_default_config()

t1 = time.time()
for i in range(10):
    spec = AC.grab_spectrum()
    print(f'Time since start: {time.time()-t1}')
    print(spec)



# Print devices
#for device in devices:
#    print(device.m_SerialId, device.m_UserFriendlyName)

# Activate first spectrometer
handle = AVS_Activate(devices[0])

print("Connected!")
print("Handle:", handle)