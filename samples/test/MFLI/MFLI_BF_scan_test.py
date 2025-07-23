import matplotlib.pyplot as plt
import zhinst.core
import time
import numpy as np
import csv
import urllib.request
from jki_python_bridge_for_labview import labview as lv

################
#Running scan and noting times of tau-stage movement for later synchro
lv.connect()
scan_busy = lv.LV_Control.check_scan()[1]
print('scan_busy:',scan_busy)
print('Initial time:', time.time())
tau_list = [0.1,0.3,0.5,0.7]
lv.LV_Control.change_scan('1Q-R', 0.8, 0.2, 0.1)  #performs 1d (t-axis) scan (change 0.2 for the actual tau resolution (depends on 'Signal bandwidth' in the software)
for tau in tau_list:
    lv.LV_Control.move_stage_pos(0,float(tau))
    print('time before tau =', tau, ':', time.time())
    lv.LV_Control.run_scan()
    print('time after tau =', tau, ':', time.time())


###############
#Acquire the latest data
#   !!LabOne can only send 16384 data points per poll in the Scope... with the lowest resolution option, max. scan length = 17s!
#   **Probably ok, because we will probably send the data from Plotter (can go up to 12h!)
url = "http://127.0.0.1:8006/netlink?id=c0p1t8p1cfm0p0&ziSessionId=1"
webpage = urllib.request.urlopen(url)
datareader = csv.reader(webpage.read().decode().splitlines())
data = []
for row in datareader:
    data.append(row)
print(data[:40])
#'data' is a list of lists. The first 5 lists contain info; let's extract the other lists (each one containing a coordinate)
numeric_data = data[5:]

time = []
scope = []

for line in numeric_data:  #each 'line' of numeric_data is a coordinate (of type 'list'), e.g. ['-3.39e-05; 3.29305']
    t, v = line[0].split(';')  #takes the first (and only) element of the list and splits it in two, e.g. ['-3.39e-05', '3.29305']
    time.append(float(t.strip()))  #strip removes spaces before/after the string
    scope.append(float(v.strip()))

time = np.array(time)
scope = np.array(scope)

plt.plot(time, scope)
x,y = data[4]
plt.xlabel(x)
plt.ylabel(y)
plt.grid()
plt.show()


################
#Split the data for each tau

