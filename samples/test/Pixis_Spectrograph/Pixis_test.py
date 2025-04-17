# -*- coding: utf-8 -*-
"""
Created on Mon Apr  7 14:42:48 2025

@author: David Tiede
"""

from pylablib.devices import PrincetonInstruments
import time
import numpy as np
import matplotlib as plt

# frame size is (252,1024)

print(PrincetonInstruments.list_cameras())
cam = PrincetonInstruments.PicamCamera()
print(cam.get_attribute_value("Pixel Format"))
#cam.open()
exp = cam.get_attribute_value("Exposure Time")
print(exp)
exp = cam.get_attribute_value("Sensor Temperature Reading")
print(exp)
#exp = cam.get_attribute_value("Center Wavelength Reading")
#print(exp)
int_time = 10
cam.set_attribute_value("Exposure Time", int_time)
t1 = time.time() 
#image = cam.grab(nframes=10, frame_timeout=5.0, missing_frame='skip', return_info=False, buff_size=None)
print('Int time grab:' + str((time.time()-t1)/10))
cam.start_acquisition()
for i in range(5):
    t1 = time.time() 
    time.sleep(int_time/1E3)
    image = None 
    count = 0
    while not type(image) == np.ndarray:
        time.sleep(0.01)
        image = cam.read_newest_image()
        count = count + 1 
    print('count:' + str(count))
    print('Int time:' + str(time.time()-t1))
    
    #print(image)
cam.stop_acquisition()
#plt.pyplot.pcolor(image)
#plt.pyplot.colorbar()
#cam.setup_acquisition(mode='snap')
cam.close()

