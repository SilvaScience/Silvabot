from harvesters.core import Harvester
import time
import os


h = Harvester()
ctiFile = os.environ['DIAPHUS_GENTL64_FILE']
print(ctiFile)
h.add_file(ctiFile)


h.update()

NDevices = len(h.device_info_list)
print(h.device_info_list)
print("{} device(s) detected on the Network:\n".format(NDevices))

if NDevices == 1:
    selectionInt = 1
elif NDevices == 0:
    print("WARNING: no heliotis detected. Wait and retry")
    time.sleep(3)
    h.update()
    NDevices = len(h.device_info_list)
    print("After wait: {} device(s) detected on the Network:\n".format(NDevices))
    selectionInt = 1
else:
    selectionInt = 1 #int(selectionStr)
    if ((selectionInt <= 0) or (selectionInt > NDevices)):
        exit('No device selected - exit script')

# to be used if more than one camera is on the network
deviceID = h.device_info_list[selectionInt - 1].id_
print('selected device:', deviceID, '\n')
h.create(selectionInt - 1)