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
date = '2026-01-20' # '2025-07-24' # 
data_name =  'raw_data17_44_41' # 'GaAs_QW_2501_16_08_00' #
bg_name =  'avg_data17_44_22' # 'avg_data17_11_58' # # load background  ;  CHANGE THIS IF TAU CHANGES THE 
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
limits = np.r_[270:290]
with h5py.File(os.path.join(path,date,bg_name + '.h5'), 'r') as f:
    bg_rawI_row = np.flip(np.sum(f['averaged_rawI'][limits,:],axis =0)) # 264:268
    bg_rawQ_row = np.flip(np.sum(f['averaged_rawQ'][limits,:],axis =0))
    bg_rawI = np.flip(f['averaged_rawI'][:,:]) # 264:268
    bg_rawQ = np.flip(f['averaged_rawQ'][:,:])
    image_I_bg =  f['averaged_rawI'][:]
    


#data_name = 'GaAs_QW_2501_19_39_48'
#filepath = os.path.join(path,date,data_name + '.h5')

with h5py.File(filepath, 'r') as f:
    rawI_row = np.flip(np.sum(f['rawI'][:, limits, :],axis =1))  # shape: (n_avg, x)
    rawQ_row = np.flip(np.sum(f['rawQ'][:, limits, :],axis =1)) 
    
    raw_image = f['rawQ'][5,:,:]
    
    rawI = np.flip(f['rawI'][:, :, :])  # shape: (n_avg, x)
    rawQ = np.flip(f['rawQ'][:, :, :]) 
    #amp_row = np.sqrt((rawI_row-bg_rawI_row) ** 2 + (rawQ_row-bg_rawQ_row) ** 2)
    
    wl = f['rawI'].attrs['xaxis']
    plt.imshow(raw_image)
    
    external_background = False
    if external_background:
        rawI_row = rawI_row-bg_rawI_row # average over all frames. 
        rawQ_row = rawQ_row-bg_rawQ_row
        rawI = rawI-bg_rawI
        rawQ = rawQ-bg_rawQ
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

f, plts = plt.subplots(3, figsize =(4,8),gridspec_kw={'height_ratios': [1, 1.1,2]})
plts[0].plot(approx_x_axis,mean_amp_row)


#plts[0].plot(approx_x_axis,np.average(amp_row/np.cos(phase_row),axis=0))
#plts[0].set_ylim(0,800)
pc = plts[1].pcolor(approx_x_axis,time_axis,amp_row)
#pc = plts[1].pcolor(approx_x_axis,time_axis,rawI_row)
#pc = plts[1].pcolor(approx_x_axis,np.linspace(1,np.shape(amp_row)[0],np.shape(amp_row)[0]),np.cos(phase_row))
#pc.set_clim(14,18)
#pc.set_clim(14,600)
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
plot_evolution = True 
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
plt.pcolor(approx_x_axis,pixel,mean_amp)
plt.clim(6,10)
plt.title(f'{title_id}')
#plt.ylim(140,200)
plt.colorbar()
plt.show()
# %% Plot FFT 


amp_ft = np.fft.fft(amp_row,axis=0)
 
Fs = 1 / (time_axis[1] - time_axis[0])   # Sampling frequency
N = np.shape(amp_row)[0]   
 
freqs = np.fft.fftfreq(N, d=1/Fs)
plt.pcolor(approx_x_axis,freqs,np.abs(amp_ft))
plt.xlim(1542,1562)
plt.ylim(-0.04,0.04)
plt.clim(0,5000)
plt.colorbar()
plt.show()
freqs_raw = freqs
amp_ft_raw = amp_ft
# keep only half of FT spectrum 
amp_ft = amp_ft[len(freqs)//2-5:]
amp_ft2 = amp_ft
freqs= -freqs[len(freqs)//2-5:]
# filter FT spectrum
crit_min = find_idx(freqs,0.020) #0.006  #0.06 #0.18
crit_max = find_idx(freqs,0.022) #0.015 #0.075 #0.195
filtered_amp_ft = amp_ft
filtered_amp_ft[:crit_max]= 0 
filtered_amp_ft[crit_min:]= 0 
filtered_amp = np.fft.ifft(np.pad(filtered_amp_ft,((len(freqs)-5,0),(0,0)),mode='constant'),axis=0)

amp_ft = np.fft.fft(amp_row,axis=0)
amp_ft = amp_ft[len(freqs)-10:]

# plot ind FT 
plt.pcolor(approx_x_axis,freqs,np.abs(amp_ft))
plt.title(f'FT data at t=0ps Nperiod=100 \n {title_id}')
plt.ylabel('FT(Raw) \n 1/Time (1/ms)')
plt.xlabel('Energy (meV)')
plt.clim(00,8000)
plt.colorbar()
plt.xlim(1535,1560)
plt.ylim(-0.10,0.01)
plt.show()

# plot 
plot_all = False
if plot_all:
    pc = {}
    f, plts = plt.subplots(4, figsize =(4,6))
    pc[0] = plts[0].pcolor(approx_x_axis,time_axis,np.abs(amp_row))
    pc[1] = plts[1].pcolor(approx_x_axis,freqs,np.abs(amp_ft))
    pc[2] = plts[2].pcolor(approx_x_axis,freqs,np.abs(filtered_amp_ft))
    pc[3] = plts[3].pcolor(approx_x_axis,time_axis,np.abs(filtered_amp))
    plts[1].set_ylim(0,0.15)
    plts[2].set_ylim(0,0.15)
    for i in range(4): 
        plts[i].set_xlim(1530,1570)
        f.colorbar(pc[i], pad =0.01, shrink=0.9)
    for i in range(3): plts[i].set_xticks([])
    pc[1].set_clim(0,10000)
    pc[2].set_clim(0,10000)
    plts[3].set_xlabel('Energy (meV)')
    plts[0].set_ylabel('Raw \n Time (ms)')
    plts[1].set_ylabel('FT(Raw) \n 1/Time (1/ms)')
    plts[2].set_ylabel('filtered FT \n 1/Time (1/ms)')
    plts[3].set_ylabel('iFT(FT) \n Time (ms)')
    plts[0].set_title(f'{title_id}')
    f.subplots_adjust(wspace =0,hspace =0)
    #plt.colorbar()
    plt.show()

# %% Plot iFT(FT)
pc = {}
f, plts = plt.subplots(3, figsize =(4,6))
pc[0] = plts[0].pcolor(approx_x_axis,time_axis,np.real(filtered_amp))
pc[1] = plts[1].pcolor(approx_x_axis,time_axis,np.imag(filtered_amp))
#pc[2] = plts[2].pcolor(approx_x_axis,time_axis,np.abs(filtered_amp))
pc[2] = plts[2].pcolor(approx_x_axis,time_axis,np.sqrt(np.real(filtered_amp)**2+np.imag(filtered_amp)**2))
plts[2].set_xlabel('Energy (meV)')
plts[0].set_ylabel('Real (iFT(FT)) \n Time (ms)')
plts[1].set_ylabel('Imag (iFT(FT)) \n Time (ms)')
plts[2].set_ylabel('Abs(iFT(FT)) \n Time (ms)')
plts[0].set_title(f'{title_id}')
for i in range(3): 
    plts[i].set_xlim(1530,1570)
    f.colorbar(pc[i], pad =0.01, shrink=0.9)
for i in range(2): plts[i].set_xticks([])
f.subplots_adjust(wspace =0,hspace =0)
plt.show()

# %%
plt.pcolor(approx_x_axis,time_axis,np.real(filtered_amp))
#plt.ylim(0,0.3)
plt.xlim(1530,1570)
#plt.clim(0,100)
plt.xlabel('Energy (meV)')
plt.ylabel('1/Time (1/ms)')
plt.colorbar()
plt.show()

# %%
plt.plot(approx_x_axis,np.average(np.abs(filtered_amp),axis=0))
#plt.plot(approx_x_axis,np.average(np.sqrt(np.real(filtered_amp)**2+np.imag(filtered_amp)**2),axis=0))
#plt.ylim(0,0.3)
plt.xlim(1530,1570)
#plt.clim(0,100)
plt.xlabel('Energy (meV)')
plt.ylabel('Intensity')
plt.title(f'{title_id}')
plt.show()

# %% plot individual spectrum of chopped Krypton lamp
approx_x_axis = np.linspace(1450,1650,np.shape(amp_map)[1])
file_idx = 3
data_name = 'Krypton_lamp_6000Hz_17_30_23'
title_id = os.path.join(date,data_name)
filepath = os.path.join(path,date,data_name + '.h5')
time_axis = np.linspace(0,np.shape(amp_row)[0],np.shape(amp_row)[0])/750.267*1E3 # in ms 750.267 is fps for N_period=40, freq=29.780kHz 
time_axis = np.linspace(0,np.shape(amp_row)[0],np.shape(amp_row)[0])/302.346*1E3 # in ms 302.346 is fps for N_period=100, freq=29.780kHz
N_period = 100
freq = 5000
fps = freq/N_period
time_axis = np.linspace(0,np.shape(amp_row)[0],np.shape(amp_row)[0])/fps*1E3
#data_name = 'GaAs_QW_2501_19_39_48'
#title_id = os.path.join(date,data_name)
#filepath = os.path.join(path,date,data_name + '.h5')
with h5py.File(filepath, 'r') as f:
    rawI_row = np.flip(np.sum(f['rawI'][:, 10:150, :],axis =1))  # shape: (n_avg, x) # 260:268
    rawQ_row = np.flip(np.sum(f['rawQ'][:, 10:150, :],axis =1))  # 260:268
    #amp_row = np.sqrt((rawI_row-bg_rawI_row) ** 2 + (rawQ_row-bg_rawQ_row) ** 2)
    rawI_imag = f['rawI'][:,:,:]
    
    rawI_row = rawI_row-np.average(rawI_row,axis=0) # average over all frames. 
    rawQ_row = rawQ_row-np.average(rawQ_row,axis=0)
    amp_row = np.sqrt(rawI_row ** 2 + rawQ_row ** 2)
    phase_row = np.arctan2(rawQ_row,rawI_row)
    #amp_row = amp_row[np.max(amp_row,axis=1)>100]
    mean_amp_row = np.mean(amp_row, axis=0)

f, plts = plt.subplots(3, figsize =(4,8),gridspec_kw={'height_ratios': [1, 1.1,2]})
plts[0].plot(approx_x_axis,np.average(amp_row,axis=0))
#plts[0].plot(approx_x_axis,np.average(amp_row/np.cos(phase_row),axis=0))
plts[0].set_ylim(0,9000)
pc = plts[1].pcolor(approx_x_axis,time_axis,amp_row)
#pc = plts[1].pcolor(approx_x_axis,np.linspace(1,np.shape(amp_row)[0],np.shape(amp_row)[0]),np.cos(phase_row))
#pc.set_clim(14,18)
pc.set_clim(14,9000)
clean_phase = np.zeros(np.shape(phase_row))
for i in range(np.shape(phase_row)[1]): 
    window = 2
    clean_phase[:,i] = np.convolve(phase_row[:,i], np.ones(window)/window, mode='same')
    #clean_phase[:,i] = savgol_filter(phase_row[:,i],3,1)
pc = plts[2].pcolor(approx_x_axis,time_axis,np.cos(clean_phase))
pc.set_clim(-1,1)
plts[2].set_xlabel('Energy (meV)')
plts[1].set_ylabel('$(Q^2+I^2)^{(1/2)}$ \n Time (ms)')
plts[2].set_ylabel('$arctan2(Q,I)$ \n Time (ms)')
#plts[1].set_ylim(0,700)
#plts[2].set_ylim(0,700)
plts[0].set_ylabel('Intensity')
plts[0].set_xticks([])
plts[1].set_xticks([])
plts[0].set_title(f'Raw data Nperiod=100 \n {title_id}')

f.colorbar(pc, orientation='horizontal', pad =0.2, shrink=0.9)
#for i in range(3): plts[i].set_xlim(1530,1570)  

f.subplots_adjust(wspace =0,hspace =0)
plt.show()
# % plot time evolution  
plot_evolution = True 
if plot_evolution:
    f, plts = plt.subplots(4, figsize =(4,6))
    #plt.plot(np.average(amp_row[:,218:279],1))
    plts[0].plot(time_axis,np.average(rawI_row[:,10:150],1),label ='rawI')
    plts[1].plot(time_axis,np.average(rawQ_row[:,10:150],1),label ='rawQ')
    plts[2].plot(time_axis,np.average(amp_row[:,10:150],1),label ='$(Q^2+I^2)^{(1/2)}$')
    plts[3].plot(time_axis,np.average(clean_phase[:,10:150],1),label ='$arctan2(Q,I)$')
    #plt.plot(time_axis,np.average(amp_row[:,230:240]/phase_row[:,230:240],1)+30,label ='$(Q^2+I^2)^{(1/2)}$')
    plts[0].set_xlabel('Time (ms)')
    for i in range(3):plts[i].set_xticks([])
    for i in range(4): 
        plts[i].legend()
        plts[i].set_ylabel('Avg. Int.')
    #plt.xlabel('Frame number')
    #plt.ylabel('Averaged intensity pixel row')
    plts[0].set_title(f'Raw data Nperiod=100 \n {title_id}')
    
    f.subplots_adjust(wspace =0,hspace =0)
    plt.show()
    
# %% Plot FFT 


amp_ft = np.fft.fft(amp_row,axis=0)
 
Fs = 1 / (time_axis[1] - time_axis[0])   # Sampling frequency
N = np.shape(amp_row)[0]   
 
freqs = np.fft.fftfreq(N, d=1/Fs)

# keep only half of FT spectrum 
amp_ft = amp_ft[len(freqs)//2:]
amp_ft2 = amp_ft
freqs= -freqs[len(freqs)//2:]
# filter FT spectrum
crit_min = find_idx(freqs,0.0038) #0.006  #0.06 #0.18
crit_max = find_idx(freqs,0.0042) #0.015 #0.075 #0.195
filtered_amp_ft = amp_ft
filtered_amp_ft[:crit_max]= 0 
filtered_amp_ft[crit_min:]= 0 
filtered_amp = np.fft.ifft(np.pad(filtered_amp_ft,((len(freqs),0),(0,0)),mode='constant'),axis=0)

amp_ft = np.fft.fft(amp_row,axis=0)
amp_ft = amp_ft[len(freqs):]

# plot ind FT 
plt.pcolor(approx_x_axis,freqs,np.abs(amp_ft))
plt.title(f'FT data Nperiod=100 \n {title_id}')
plt.ylabel('FT(Raw) \n 1/Time (1/ms)')
plt.xlabel('Energy (meV)')
plt.clim(0,8000)
plt.colorbar()
#plt.xlim(1535,1560)
plt.show()

# plot 
plot_all = True
if plot_all:
    pc = {}
    f, plts = plt.subplots(4, figsize =(4,6))
    pc[0] = plts[0].pcolor(approx_x_axis,time_axis,np.abs(amp_row))
    pc[1] = plts[1].pcolor(approx_x_axis,freqs,np.abs(amp_ft))
    pc[2] = plts[2].pcolor(approx_x_axis,freqs,np.abs(filtered_amp_ft))
    pc[3] = plts[3].pcolor(approx_x_axis,time_axis,np.abs(filtered_amp))
    plts[1].set_ylim(0,0.015)
    plts[2].set_ylim(0,0.015)
    for i in range(4): 
        plts[i].set_xlim(1450,1650)
        f.colorbar(pc[i], pad =0.01, shrink=0.9)
    for i in range(3): plts[i].set_xticks([])
    pc[1].set_clim(0,10000)
    pc[2].set_clim(0,10000)
    plts[3].set_xlabel('Energy (meV)')
    plts[0].set_ylabel('Raw \n Time (ms)')
    plts[1].set_ylabel('FT(Raw) \n 1/Time (1/ms)')
    plts[2].set_ylabel('filtered FT \n 1/Time (1/ms)')
    plts[3].set_ylabel('iFT(FT) \n Time (ms)')
    plts[0].set_title(f'Raw data Nperiod=100 \n {title_id}')
    f.subplots_adjust(wspace =0,hspace =0)
    #plt.colorbar()
    plt.show()

# %% Plot iFT(FT)
pc = {}
f, plts = plt.subplots(4, figsize =(4,6))
plts[0].plot(approx_x_axis,np.average(np.abs(filtered_amp),axis =0))
pc[0] = plts[1].pcolor(approx_x_axis,time_axis,np.real(filtered_amp))
pc[1] = plts[2].pcolor(approx_x_axis,time_axis,np.imag(filtered_amp))
#pc[2] = plts[2].pcolor(approx_x_axis,time_axis,np.abs(filtered_amp))
pc[2] = plts[3].pcolor(approx_x_axis,time_axis,np.sqrt(np.real(filtered_amp)**2+np.imag(filtered_amp)**2))
plts[3].set_xlabel('Energy (meV)')
plts[1].set_ylabel('Real (iFT(FT)) \n Time (ms)')
plts[2].set_ylabel('Imag (iFT(FT)) \n Time (ms)')
plts[3].set_ylabel('Abs(iFT(FT)) \n Time (ms)')
plts[0].set_title(f'Raw data at tau={tau_values[file_idx]}ps \n {title_id}')
plts[0].set_xlim(1450,1650)
for i in range(3): 
    plts[i].set_xlim(1450,1650)
    #f.colorbar(pc[i], pad =0.01, shrink=0.9)
for i in range(2): plts[i].set_xticks([])
f.subplots_adjust(wspace =0,hspace =0)
plt.show()


