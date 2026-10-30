import numpy as np
import matplotlib.pyplot as plt
import h5py
import os
from scipy.fft import fft, fftshift, ifftshift, fftfreq, ifft, fft2, ifft2
#from src.measurements.MeasurementClasses import TwoDMeasurement
from jki_python_bridge_for_labview import labview as lv
from matplotlib.patches import Rectangle
import matplotlib.ticker as ticker
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
from scipy.signal import savgol_filter


def find_idx(array,value):
    return np.argmin(abs(array-value))

h = 4.135E-15 #eV/Hz
h_c = 1239.841984 #h * c in eV/nm
#lv.connect()
# %%
# input 
date = '2026-10-30' # '2025-07-24' # 
data_name =  'DCM' # 'GaAs_QW_2501_16_08_00' #
filename =  'raw_data10_24_09' # 'avg_data17_11_58' # # load background  ;  CHANGE THIS IF TAU CHANGES THE 
path = r"C:\DATA\ECPL"
path = r"D:\DATA\BIGFOOT"
title_id = os.path.join(date,data_name)


with h5py.File(os.path.join(path,date,"raw",filename + '.h5'), 'r') as f:
    #bg_rawI_row = np.flip(np.sum(f['averaged_rawI'][315:320,:],axis =0))
    #bg_rawQ_row = np.flip(np.sum(f['averaged_rawQ'][315:320,:],axis =0))
    rawI =  f['rawI'][:]
    rawQ =  f['rawQ'][:]
    
    
#amp_row_bg = np.sqrt(bg_rawI_row ** 2 + bg_rawQ_row ** 2)
#amp_row_bg = abs(amp_row_bg - np.average(amp_row_bg,axis=0))

# create 2d map for fft (horizontal = amplitude with bg suppression, vertical = tau axis)

#plt.title(date + bg_name)
#plt.pcolor(raw_amp[1])
#plt.show()

# %% sum data 
x_rec = 228
y_rec = 261
width = 10


I = np.average(rawI,axis=0)**2
avgI = np.average(I[y_rec:y_rec+width,x_rec:x_rec+width]) 
Q = np.average(rawQ,axis=0)**2
avgQ = np.average(Q[y_rec:y_rec+width,x_rec:x_rec+width])
amp_map =np.sqrt(I + Q)
avgamp = np.average(Q[y_rec:y_rec+width,x_rec:x_rec+width]+I[y_rec:y_rec+width,x_rec:x_rec+width])
avgamp1 = np.sqrt(avgQ +avgI) 
avgamp2 = np.sqrt(avgamp) 

# %% 
rect = Rectangle((x_rec,y_rec),width,width,facecolor = 'none', edgecolor = 'white')
avg = np.average(amp_map[y_rec:y_rec+width,x_rec:x_rec+width])
plt.pcolor(amp_map)
plt.xlim(220,250)
plt.ylim(250,280)
plt.gca().add_patch(rect)
plt.annotate(f'avg={avg:.2f}', (242,278), color = 'white')
plt.title(date + filename)
plt.colorbar()
plt.show()

# %% load data
path = r"C:\DATA\ECPL"
date = '2026_10_30' 
filename = 'ECPL_DCM_0ps_11_58_57.h5'
filepath = os.path.join(path,date, filename)

with h5py.File(filepath, 'r') as f:
    image =  f['spectra'][1]
    

# % plot data
spec = image
x_rec = 228
y_rec = 261
width = 8

rect = Rectangle((x_rec,y_rec),width,width,facecolor = 'none', edgecolor = 'white')
avg = np.average(spec[y_rec:y_rec+width,x_rec:x_rec+width])
avg_bg = np.average(spec[y_rec-width:y_rec,x_rec:x_rec+width])
plt.pcolor(spec)
plt.xlim(220,250)
plt.ylim(250,280)
plt.gca().add_patch(rect)
plt.annotate(f'avg={avg:.2f}', (242,278), color = 'white')
plt.colorbar()
plt.title(date + filename)
plt.show()