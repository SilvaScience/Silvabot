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


def find_idx(array,value):
    return np.argmin(abs(array-value))

h = 4.135E-15 #eV/Hz
h_c = 1239.841984 #h * c in eV/nm
#lv.connect()
# %%
# input 
date = '2026-01-26' # '2025-07-24' # 
data_name =  'raw_data17_18_56' # 'GaAs_QW_2501_16_08_00' #
bg_name =  'avg_data13_24_08' # 'avg_data17_11_58' # # load background  ;  CHANGE THIS IF TAU CHANGES THE 
path = r"D:\DATA\BIGFOOT"
title_id = os.path.join(date,data_name)


# %% plot individual spectrum
N_period = 100
freq = 1000
fps = freq/N_period
plot_external = True
if plot_external:
    title_id = os.path.join(date,data_name)
    filepath = os.path.join(path,date,data_name + '.h5')
    
# load background 
limits = np.r_[190:240]
with h5py.File(os.path.join(path,date,bg_name + '.h5'), 'r') as f:
    bg_rawI_row = np.flip(np.sum(f['averaged_rawI'][limits,:],axis =0)) # 264:268
    bg_rawQ_row = np.flip(np.sum(f['averaged_rawQ'][limits,:],axis =0))
    bg_rawI = f['averaged_rawI'][:,:] # 264:268
    bg_rawQ = f['averaged_rawQ'][:,:]
    image_I_bg =  f['averaged_rawI'][:]
    


#data_name = 'GaAs_QW_2501_19_39_48'
#filepath = os.path.join(path,date,data_name + '.h5')

with h5py.File(filepath, 'r') as f:
    rawI_row = np.flip(np.sum(f['rawI'][:, limits, :],axis =1))  # shape: (n_avg, x)
    rawQ_row = np.flip(np.sum(f['rawQ'][:, limits, :],axis =1)) 
    
    raw_image = f['rawQ'][5,:,:]
    
    rawI_t = f['rawI'][:, :, :]  # shape: (n_avg, x)
    rawQ_t = f['rawQ'][:, :, :] 
    #amp_row = np.sqrt((rawI_row-bg_rawI_row) ** 2 + (rawQ_row-bg_rawQ_row) ** 2)
    
    wl = f['rawI'].attrs['xaxis']
    #plt.imshow(raw_image)
    
    external_background = True
    if external_background:
        rawI_row = rawI_row-bg_rawI_row # average over all frames. 
        rawQ_row = rawQ_row-bg_rawQ_row
        rawI = rawI_t-bg_rawI
        rawQ = rawQ_t-bg_rawQ
    else:
        rawI_row = rawI_row-np.average(rawI_row,axis=0) # average over all frames. 
        rawQ_row = rawQ_row-np.average(rawQ_row,axis=0)
        rawI = rawI-np.average(rawI,axis=0)
        rawQ = rawQ-np.average(rawQ,axis=0)
    amp_row = np.sqrt(rawI_row ** 2 + rawQ_row ** 2)
    amp = np.sqrt(rawI ** 2 + rawQ ** 2)
    mean_amp = np.mean(amp, axis=0)
    phase_row = np.arctan2(rawQ_row,rawI_row)
    #amp_row = amp_row[np.max(amp_row,axis=1)>100]
    mean_amp_row = np.mean(amp_row, axis=0)
    
time_axis = np.linspace(0,np.shape(amp_row)[0],np.shape(amp_row)[0])/fps*1E3
approx_x_axis = np.flip(1240/wl*1E3)


plot_row_average = False
if plot_row_average:
    f, plts = plt.subplots(3, figsize =(4,8),gridspec_kw={'height_ratios': [1, 1.1,2]})
    plts[0].plot(approx_x_axis,mean_amp_row)
    
    pc = plts[1].pcolor(approx_x_axis,time_axis,amp_row)
    
    clean_phase = np.zeros(np.shape(phase_row))
    for i in range(np.shape(phase_row)[1]): 
        window = 2
        clean_phase[:,i] = np.convolve(phase_row[:,i], np.ones(window)/window, mode='same')
        #clean_phase[:,i] = savgol_filter(phase_row[:,i],3,1)
    pc = plts[2].pcolor(approx_x_axis,time_axis,np.cos(clean_phase))
    #pc.set_clim(-1,1)
    plts[2].set_xlabel('Energy (meV)')
    plts[1].set_ylabel('$(Q^2+I^2)^{(1/2)}$ \n Time (ms)')
    plts[2].set_ylabel('$arctan2(Q,I)$ \n Time (ms)')
    #plts[1].set_ylim(0,700)
    #plts[2].set_ylim(0,700)
    plts[0].set_ylabel('Intensity')
    plts[0].set_xticks([])
    plts[1].set_xticks([])
    plts[0].set_title(f'{title_id}')
    if plot_external: plts[0].set_title(f'Single scan Ref=1kHz Demod=1kHz \n {title_id}')
    
    f.colorbar(pc, orientation='horizontal', pad =0.2, shrink=0.9)
    #for i in range(3): plts[i].set_xlim(1540,1570)
    f.subplots_adjust(wspace =0,hspace =0)
    plt.show()
  


# % plot time evolution  
plot_evolution = False 
if plot_evolution:
    f, plts = plt.subplots(4, figsize =(4,6))
    #plt.plot(np.average(amp_row[:,218:279],1))
    plts[0].plot(time_axis,np.average(rawI_row[:,limits],1),label ='rawI')
    plts[1].plot(time_axis,np.average(rawQ_row[:,limits],1),label ='rawQ')
    plts[2].plot(time_axis,np.average(amp_row[:,limits],1),label ='$(Q^2+I^2)^{(1/2)}$')
    plts[3].plot(time_axis,np.average(clean_phase[:,limits],1),label ='$arctan2(Q,I)$')
    #plt.plot(time_axis,np.average(amp_row[:,230:240]/phase_row[:,230:240],1)+30,label ='$(Q^2+I^2)^{(1/2)}$')
    plts[0].set_xlabel('Time (ms)')
    for i in range(4): 
        plts[i].legend()
        plts[i].set_ylabel('Avg. Int.')
    #plt.xlabel('Frame number')
    #plt.ylabel('Averaged intensity pixel row')
    plts[0].set_title(f'{title_id}')
    
    f.subplots_adjust(wspace =0,hspace =0)
    plt.show()
    
  
# %% Plot amplitude map
pixel = np.r_[1:543]
plt.pcolor(approx_x_axis,pixel,np.flipud(mean_amp))
plt.clim(7.2,8)
plt.title(f'{title_id}')
plt.xlabel('Energy (meV)')
plt.ylabel('Pixel')
plt.xlim(1595,1609)
plt.ylim(100,490)
plt.colorbar()
plt.show()

# %% 
#plt.figure(figsize=(6,10))
plt.pcolor(pixel,approx_x_axis+12,np.transpose(np.flipud(mean_amp)))
plt.clim(6.8,7.4)
plt.title(f'{title_id}')
plt.ylabel('Energy (meV)')
plt.xlabel('Pixel')
plt.ylim(1607,1614)
plt.xlim(100,490)
plt.colorbar()
plt.show()




