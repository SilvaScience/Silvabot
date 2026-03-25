import matplotlib.pyplot as plt
import zhinst.core
import time
import numpy as np
from scipy.fft import fft2, fftshift
import csv
import urllib.request
from jki_python_bridge_for_labview import labview as lv

################
#Running scan and noting times of tau-stage movement for later synchro
lv.connect()
scan_busy = lv.LV_Control.check_scan()[1]
print('scan_busy:',scan_busy)
t1 = time.time()
print('Initial time:', t1)
tau_list = [0.1]
lv.LV_Control.change_scan('1Q-R', 0.5, 0.5, 0.1)       #can make scan so narrow vertically that it takes only one tau, and loop for many taus to make 2d scan
for tau in tau_list:
    lv.LV_Control.move_stage_pos(0,float(tau))
    print('time before tau =', tau, ':', time.time())
    lv.LV_Control.run_scan()
    print('time after tau =', tau, ':', time.time(),', stage movement:', lv.LV_Control.check_stage_move())
    i=0
    while i < 300:
        print(i, time.time())
        print(lv.LV_Control.acquire_phase())
        stage_moveA, stage_moveB = lv.LV_Control.check_scan()
        if stage_moveA != 0:
            print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!A', i)
        if stage_moveB != 1:
            print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!B', i)
        time.sleep(0.1)
        i+=1

###############
#Acquire the latest data
#   !!LabOne can only send 16384 data points per poll in the Scope... with the lowest resolution option, max. scan length = 17s!
#   **Probably ok, because we will probably send the data from Plotter (can go up to 12h!)
# IMPORTANT: THIS TECHNIQUE SENDS THE DATA OF THE LAST TIME PERIOD SELECTED IN THE PLOTTER (OR IN THE SCOPE IF USING SCOPE). BUT IF YOU ZOOM ON THE TIME
#            SCALE, IT WILL ONLY SEND THE TIME THAT YOU CAN SEE IN THE PLOTTER (OR SCOPE). DON'T ZOOM / UNZOOM THE TIME AXIS WHEN LOOKING AT LABONE DURING A SCAN!
#            ALSO, BEFORE RUNNING THE CODE, YOU ALWAYS HAVE TO GO IN LABONE AND VIEW THE PLOTTED DATA. THEN, YOU CAN RUN THIS CODE AND, WHILE IT'S RUNNNING, DON'T
#            OPEN ANYTHING ELSE ON THIS COMPUTER OR CHANGE TAB ; SOME ACTIONS AFFECT THE DATA POLL.
time.sleep(11)
print('time since t1:', time.time()-t1)
url = "http://127.0.0.1:8006/netlink?id=c0p1t8p1cfm0p0&ziSessionId=0"
webpage = urllib.request.urlopen(url)
datareader = csv.reader(webpage.read().decode().splitlines())
data = []
for row in datareader:
    data.append(row)
#print(data[:40])
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
plt.title('Plotter')
x,y = data[4]  #add [0].split(';') if plot the 'scope' tab
plt.xlabel(x)
plt.ylabel(y)
plt.grid()
plt.show()


################
#Split the data for each tau
critical_times = [-35, -30, -25, -20, -15, -10] #change later. here, for 5 taus
for i in range(len(critical_times)-1):
    time_start = critical_times[i]+1  #cut 1sec before and after stage movement
    time_end = critical_times[i+1]-1

    i_start = np.searchsorted(time, time_start, side='left')
    i_end = np.searchsorted(time, time_end, side='right')

    data_slice = scope[i_start:i_end]

    if i == 0:
        target_len = len(data_slice)
        TwoD_data_t = np.zeros((len(critical_times)-1, target_len))  #initialize 2d time-domain data with t-axis length of first tau

    if len(data_slice) > target_len:
        data_slice = data_slice[:target_len]

    elif len(data_slice) < target_len:
        padding = np.zeros(target_len - len(data_slice))
        data_slice = np.concatenate((data_slice, padding))

    TwoD_data_t[-i-1] = data_slice

plt.imshow(TwoD_data_t, aspect='auto', cmap='viridis')  # or 'plasma', 'inferno', 'gray', etc.
plt.colorbar()  # adds a color scale bar
plt.title("2D time-domain data")
plt.xlabel("t")
plt.ylabel("tau index")
plt.show()


#################
#Apply 2D FFT
fft_result = fft2(TwoD_data_t)
fft_magnitude = np.abs(fft_result)
fft_shifted = fftshift(fft_result) #shifts the zero-frequency component to the center (inverts quadrants 1-3 and 2-4)
magnitude_spectrum = np.abs(fft_shifted)  #done 2 times... ok?

#plt.imshow(magnitude_spectrum, aspect='auto', cmap='viridis')
plt.imshow(np.log(1 + magnitude_spectrum), aspect='auto', cmap='viridis')  #log scale for better visibility
plt.colorbar()
plt.title("2D frequency-domain data")
plt.xlabel("Emission Energy")
plt.ylabel("Absorption Energy")
plt.show()