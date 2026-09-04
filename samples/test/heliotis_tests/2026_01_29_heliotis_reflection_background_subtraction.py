import numpy as np
import matplotlib.pyplot as plt
import matplotlib
import h5py
import os
from scipy.fft import fft, fftshift, ifftshift, fftfreq, ifft, fft2, ifft2
#from src.measurements.MeasurementClasses import TwoDMeasurement
from jki_python_bridge_for_labview import labview as lv
from matplotlib.patches import Rectangle
import matplotlib.ticker as ticker
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
from scipy.signal import savgol_filter
import matplotlib.colors as colors


def find_idx(array,value):
    return np.argmin(abs(array-value))

h = 4.135E-15 #eV/Hz
h_c = 1239.841984 #h * c in eV/nm
#lv.connect()
# %%
# input 
date = '2026-01-29' # '2025-07-24' # 
data_name =  'raw_data16_45_50' # 'GaAs_QW_2501_16_08_00' #
bg_name =  'avg_data11_52_26' # 'avg_data17_11_58' # # load background  ;  CHANGE THIS IF TAU CHANGES THE 
path = r"D:\DATA\BIGFOOT"
title_id = os.path.join(date,data_name)


# %% plot individual spectrum
def load_n_correct_bg(data_name):
    title_id = os.path.join(date,data_name)
    filepath = os.path.join(path,date,data_name + '.h5')
        
    # load background 
    
    limits = np.r_[190:240]
    with h5py.File(os.path.join(path,date,bg_name + '.h5'), 'r') as f:
        bg_rawI = f['averaged_rawI'][:,:] # 264:268
        bg_rawQ = f['averaged_rawQ'][:,:]
        
    
    with h5py.File(filepath, 'r') as f:
        
        rawI_t = f['rawI'][:, :, :]  # shape: (n_avg, x)
        rawQ_t = f['rawQ'][:, :, :] 
        
        wl = f['rawI'].attrs['xaxis']
        
        rawI = rawI_t-bg_rawI
        rawQ = rawQ_t-bg_rawQ
        amp = np.sqrt(rawI ** 2 + rawQ ** 2)
        mean_amp = np.mean(amp, axis=0)
        
    energy_axis = 1240/wl*1E3
    
    return energy_axis,mean_amp

# %% stich several maps
filenames=['raw_data14_35_30','raw_data14_35_41','raw_data14_35_57','raw_data14_36_16']
filenames=['raw_data20_13_18']
maps = {}
energy_axis = {}
wl_axis = {}
for f in filenames:
    energy_axis[f],maps[f] = load_n_correct_bg(f)
    wl_axis[f] = 1240/energy_axis[f]*1E3
    
# %% Plot amplitude map
pixel = np.r_[1:543]
for f in filenames:
    Z =maps[f]-7
    log_norm = colors.LogNorm(vmin=2, vmax=np.nanmax(Z))
    plt.pcolor(wl_axis[f],pixel,Z) #,norm=log_norm 
    plt.clim(1,40)
plt.title(f'{date}\n{filenames}'.replace('raw_data',''))
plt.xlabel('Wavelength (nm)')
plt.ylabel('Pixel')
plt.xlim(-13,12)
plt.ylim(120,450)
plt.colorbar()
plt.show()

# %% Plot average

pixel = np.r_[200:300]
pixel = np.r_[340:360]
bg_pixel = np.r_[50:70]
max_val =np.zeros(len(filenames))
for i,f in enumerate(filenames):
    avg_spectrum = np.mean(maps[f][pixel,:],axis=0) - np.mean(maps[f][bg_pixel,:],axis=0)
    plt.plot(wl_axis[f],avg_spectrum)
    max_val[i] = np.max(avg_spectrum)
plt.title(f'{date}\n{filenames}'.replace('raw_data',''))
plt.annotate(f'Avg:[{pixel[0]}:{pixel[-1]}]-[{bg_pixel[0]}:{bg_pixel[-1]}]', (np.min(wl_axis[filenames[0]])+5,np.max(max_val)-2))
plt.xlabel('Wavelength (nm)')
plt.ylabel('Pixel')
plt.ylim(-1,np.max(max_val)*1.1)
#plt.xlim(1595,1609)
#plt.ylim(100,490)
#plt.colorbar()
plt.show()




