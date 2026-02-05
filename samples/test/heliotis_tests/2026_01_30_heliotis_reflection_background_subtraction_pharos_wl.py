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
date = '2026-01-30' # '2025-07-24' # 
data_name =  'raw_data11_37_00' # 'GaAs_QW_2501_16_08_00' #
bg_name =  'avg_data16_17_15' # 'avg_data17_11_58' # # load background  ;  CHANGE THIS IF TAU CHANGES THE 
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
    
    return energy_axis,mean_amp,rawI,rawQ,amp

# %% stich several maps
filenames=['raw_data14_35_30','raw_data14_35_41','raw_data14_35_57','raw_data14_36_16']
filenames=['raw_data16_29_30']
maps = {}
rawI = {}
rawQ = {}
amp = {}
energy_axis = {}
wl_axis = {}
for f in filenames:
    energy_axis[f],maps[f],rawI[f],rawQ[f],amp[f] = load_n_correct_bg(f)
    wl_axis[f] = 1240/energy_axis[f]*1E3
    
# %% Plot amplitude map
pixel = np.r_[1:543]
for f in filenames:
    Z =maps[f]-7
    log_norm = colors.LogNorm(vmin=2, vmax=np.nanmax(Z))
    plt.pcolor(wl_axis[f],pixel,Z) #,norm=log_norm 
    plt.clim(3,7)
plt.title(f'{date}\n{filenames[0]}'.replace('raw_data',''))
plt.xlabel('Wavelength (nm)')
plt.ylabel('Pixel')
#plt.xlim(-13,12)
#plt.ylim(190,210)
plt.colorbar()
plt.show()

# %% Plot vs energy
limits_pixel = np.r_[40:60]
limits_pixel = np.r_[310:340]

file = filenames[0]
pixel = np.r_[1:543]
plt.pcolor(pixel,energy_axis[file],np.transpose(maps[file]))
plt.clim(7,13.47)
plt.title(f'{date}\n{filenames[0]}'.replace('raw_data',''))
plt.ylabel('Energy (meV)')
plt.xlabel('Pixel')
#plt.xlim(120,480)
#plt.ylim(100,490)
plt.colorbar()

# add rectangle
#plt.figure()
rect = Rectangle((limits_pixel[0],energy_axis[file][limits_energy[0]]), limits_pixel[-1] - limits_pixel[0], energy_axis[file][limits_energy[0]] - energy_axis[file][limits_energy[-1]],
                 fill=False, edgecolor='red', linewidth=2)
plt.gca().add_patch(rect)

plt.show()

# % plot time evolution
N_period = 100
freq = 347
fps = freq/N_period
file = filenames[0]
I= rawI[file]
Q= rawQ[file]
a = amp[file]
time_axis = np.linspace(0,np.shape(I)[0],np.shape(I)[0])/fps*1E3  
plot_evolution = True 
limits_energy = np.r_[find_idx(energy_axis[file], 1640):find_idx(energy_axis[file], 1630)]
if plot_evolution:
    f, plts = plt.subplots(3, figsize =(4,6))
    #plt.plot(np.average(amp_row[:,218:279],1))
    plts[0].plot(time_axis,np.average(np.average(I[:,limits_pixel,:],1)[:,limits_energy],1),label ='rawI')
    plts[1].plot(time_axis,np.average(np.average(Q[:,limits_pixel,:],1)[:,limits_energy],1),label ='rawQ')
    plts[2].plot(time_axis,np.average(np.average(a[:,limits_pixel,:],1)[:,limits_energy],1),label ='$(Q^2+I^2)^{(1/2)}$')
    #plts[3].plot(time_axis,np.average(clean_phase[:,limits],1),label ='$arctan2(Q,I)$')
    #plt.plot(time_axis,np.average(amp_row[:,230:240]/phase_row[:,230:240],1)+30,label ='$(Q^2+I^2)^{(1/2)}$')
    plts[0].set_xlabel('Time (ms)')
    for i in range(3): 
        plts[i].legend()
        plts[i].set_ylabel('Avg. Int.')
    #plt.xlabel('Frame number')
    #plt.ylabel('Averaged intensity pixel row')
    plts[0].set_title(f'{date} {filenames[0]}'.replace('raw_data',''))
    
    f.subplots_adjust(wspace =0,hspace =0)
    plt.show()
    print(f'amp average ={np.average(np.average(np.average(a[:,limits_pixel,:],1)[:,limits_energy],1))}')

# %% Plot average

pixel = np.r_[204:208]
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




