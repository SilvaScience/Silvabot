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



h = 4.135E-15 #eV/Hz
h_c = 1239.841984 #h * c in eV/nm
#lv.connect()
# %%
# input 
date = '2025-09-17' # '2025-07-24' # 
data_name =  'GaAs_QW_2501_21_14_29' # 'GaAs_QW_2501_16_08_00' #
bg_name =  'avg_data11_21_32' # 'avg_data17_11_58' # # load background  ;  CHANGE THIS IF TAU CHANGES THE 
path = r"D:\DATA\BIGFOOT"
title_id = os.path.join(date,data_name)


with h5py.File(os.path.join(path,date,bg_name + '.h5'), 'r') as f:
    bg_rawI_row = np.sum(f['averaged_rawI'][260:268,:],axis =0)
    bg_rawQ_row = np.sum(f['averaged_rawQ'][260:268,:],axis =0)
    image_I_bg =  f['averaged_rawI'][:]

# create 2d map for fft (horizontal = amplitude with bg suppression, vertical = tau axis)
folder = os.path.join(path,date,data_name)
file_list = sorted(os.listdir(folder))

#plt.pcolor(image_I_bg)
#plt.ylim(260,270)
plt.plot(image_I_bg[264])
plt.show()

step = 0.02 # 0.02 # lv.LV_Control.read_scan_params()[1]  #SINCE THIS RETURNS NUMBERS WITH ++DECIMALS, I'M NOT SURE IT'S THE EXACT TAU POSITIONS THAT WILL BE SENT TO THE STAGE... SEE HOW PRECISE WE CAN ASK BF STAGE TO BE
tau_values = np.arange(0, len(file_list)*step, step)   #should import tau_max_value instead of writing '2.0'... how?
print(tau_values.shape)
print(len(file_list))
# %% load data
amp_map = np.zeros((len(file_list), bg_rawI_row.shape[0]))   #should be len(tau_values... but sometimes len(file_list) is different :(
print(amp_map.shape)

for i, filename in enumerate(file_list):
    filepath = os.path.join(folder, filename)

    with h5py.File(filepath, 'r') as f:
        rawI_row = np.sum(f['rawI'][:, 260:268, :],axis =1)  # shape: (n_avg, x)
        rawQ_row = np.sum(f['rawQ'][:, 260:268, :],axis =1) 

    # external bg 
    #amp_row = np.sqrt((rawI_row-bg_rawI_row) ** 2 + (rawQ_row-bg_rawQ_row) ** 2)

    # self-averaged    
    rawI_row = rawI_row-np.average(rawI_row,axis=0)
    rawQ_row = rawQ_row-np.average(rawQ_row,axis=0)
    amp_row = np.sqrt(rawI_row ** 2 + rawQ_row ** 2)
    
    amp_row = abs(amp_row - np.average(amp_row,axis=0))
    #amp_row = amp_row[np.max(amp_row,axis=1)>100]
    mean_amp_row = np.mean(amp_row, axis=0) #np.average(amp_row,axis=0)
    print(np.shape(amp_row)[0])
    amp_map[i, :] = np.average(amp_row,axis=0) #amp_row #mean_amp_row

amp_map = np.fliplr(amp_map)
raw_amp_map = amp_map
# %% plot raw files
approx_x_axis = np.linspace(1429,1429+250,np.shape(amp_map)[1])
approx_x_axis = np.linspace(1506,1506+80,np.shape(amp_map)[1])
bg_correct = False
if bg_correct:
    plt.pcolor(approx_x_axis,tau_values,amp_map-np.mean(amp_map,axis =0))
    plt.title(f'Raw data -mean(raw data) \n {title_id}') 
else:
    plt.pcolor(approx_x_axis,tau_values,amp_map)
    plt.title(f'Raw data \n {title_id}')  
plt.xlim(1530,1580)
plt.xlabel('Energy (meV)')
plt.ylabel('Time (ps)')
plt.colorbar()

plt.show()
amp_map_bg_correct = amp_map-np.mean(amp_map,axis =0)
#amp_map = amp_map_bg_correct

plot_average = True
if plot_average:
    plt.plot(approx_x_axis,np.average(amp_map,axis=0))
    plt.xlabel('Energy (meV)')
    plt.ylabel('Intensity')
    plt.title(f'Averaged raw data \n {title_id}')
    plt.xlim(1530,1580)
    plt.plot()

# %% FT data as done for BF data 
amp_map = raw_amp_map
amp_map = amp_map_bg_correct

padded_amp_map = np.pad(amp_map,((0,np.shape(amp_map)[0]),(0,0)))
num_padded_step = np.shape(padded_amp_map)[0]



ps_to_meV = 4.1356677
cal_tau_freq_step = ps_to_meV/(step*num_padded_step)
freq_shift = 1240/0.796 
cal_tau_freq_axis = np.linspace(-freq_shift-cal_tau_freq_step*num_padded_step/2,-freq_shift+cal_tau_freq_step*num_padded_step/2,num_padded_step)


freq_freq = fft(padded_amp_map, axis=0)
plt.pcolor(approx_x_axis, cal_tau_freq_axis,np.abs(freq_freq))
plt.clim(0,130)
plt.colorbar()
#plt.xlim(1530,1580)
#plt.xlim(1545,1565)
#plt.xlim(1550,1610)
#plt.ylim(-1565,-1545)
plt.title(f'FT Data \n {title_id}')  
plt.xlabel('Emission Energy (meV)')
plt.ylabel('Absorption Energy (meV)')
formatter = ticker.FormatStrFormatter('%.0f')
plt.gca().xaxis.set_major_formatter(formatter)
plt.gca().yaxis.set_major_formatter(formatter)

# %% plot individual spectrum
file_idx = 3
filename = file_list[file_idx]
filepath = os.path.join(folder, filename)
#data_name = 'GaAs_QW_2501_19_39_48'
#title_id = os.path.join(date,data_name)
#filepath = os.path.join(path,date,data_name + '.h5')
with h5py.File(filepath, 'r') as f:
    rawI_row = np.sum(f['rawI'][:, 260:268, :],axis =1)  # shape: (n_avg, x)
    rawQ_row = np.sum(f['rawQ'][:, 260:268, :],axis =1) 
    amp_row = np.sqrt((rawI_row-bg_rawI_row) ** 2 + (rawQ_row-bg_rawQ_row) ** 2)
    
    rawI_row = rawI_row-np.average(rawI_row,axis=0)
    rawQ_row = rawQ_row-np.average(rawQ_row,axis=0)
    amp_row = np.sqrt(rawI_row ** 2 + rawQ_row ** 2)
    #amp_row = amp_row[np.max(amp_row,axis=1)>100]
    mean_amp_row = np.mean(amp_row, axis=0)

f, plts = plt.subplots(2, figsize =(4,4),gridspec_kw={'height_ratios': [1, 2]})
plts[0].plot(approx_x_axis,np.average(amp_row,axis=0))
pc = plts[1].pcolor(approx_x_axis,np.linspace(1,np.shape(amp_row)[0],np.shape(amp_row)[0]),amp_row)
plts[1].set_xlabel('Emission Energy (meV)')
plts[1].set_ylabel('Frame number')
plts[0].set_ylabel('Intensity')
plts[0].set_xticks([])
plts[0].set_title(f'Raw data at T={tau_values[file_idx]}ps \n {title_id}')

f.colorbar(pc, orientation='horizontal', pad =0.25, shrink=0.9)
for i in range(2): plts[i].set_xlim(1510,1590)  

f.subplots_adjust(wspace =0,hspace =0)
plt.show()
# % plot time evolution  
plot_evolution = True
if plot_evolution:
    plt.plot(np.average(amp_row,1))
    plt.xlabel('Frame number')
    plt.ylabel('Averaged intensity pixel row')
    plt.show()

# %% plot individual spectrum
file_idx = 3
data_name = 'GaAs_QW_2501_09_56_09'
title_id = os.path.join(date,data_name)
filepath = os.path.join(path,date,data_name + '.h5')
with h5py.File(filepath, 'r') as f:
    rawI_row = np.sum(f['rawI'][:, 260:268, :],axis =1)  # shape: (n_avg, x)
    rawQ_row = np.sum(f['rawQ'][:, 260:268, :],axis =1) 
    #rawI_row = rawI_row-np.transpose(np.transpose(np.ones(np.shape(rawI_row)))*np.average(rawQ_row,axis=1))
    #rawQ_row = rawQ_row-np.transpose(np.transpose(np.ones(np.shape(rawQ_row)))*np.average(rawQ_row,axis=1))
    rawI_row = rawI_row-np.average(rawI_row,axis=0)
    rawQ_row = rawQ_row-np.average(rawQ_row,axis=0)
    #amp_row = np.sqrt((rawI_row-bg_rawI_row) ** 2 + (rawQ_row-bg_rawQ_row) ** 2)
    #amp_row = np.sqrt((rawI_row-np.mean(rawI_row)) ** 2 + (rawQ_row-np.mean(rawQ_row)) ** 2)
    amp_row = np.sqrt(rawI_row ** 2 + rawQ_row ** 2)
    amp_row = abs(amp_row - np.average(amp_row,axis=0)) # np.transpose(np.tile(np.average(amp_row,axis=0), (512,1)))
    mean_amp_row = np.average(amp_row, axis=0)

f, plts = plt.subplots(2, figsize =(4,4),gridspec_kw={'height_ratios': [1, 2]})
plts[0].plot(approx_x_axis,np.average(amp_row,axis=0))
pc = plts[1].pcolor(approx_x_axis,np.linspace(1,np.shape(amp_row)[0],np.shape(amp_row)[0]),amp_row)
plts[1].set_xlabel('Emission Energy (meV)')
plts[1].set_ylabel('Frame number')
pc.set_clim(0,10)
plts[0].set_ylabel('Intensity')
plts[0].set_xticks([])
plts[0].set_title(f'Raw data at T={tau_values[file_idx]}ps \n {title_id}')

f.colorbar(pc, orientation='horizontal', pad =0.25, shrink=0.9)
for i in range(2): plts[i].set_xlim(1510,1590)  

f.subplots_adjust(wspace =0,hspace =0)
plt.show()
plot_evolution = False
if plot_evolution:
    plt.plot(np.average(amp_row,1))
    plt.xlabel('Frame number')
    plt.ylabel('Averaged intensity pixel row')
    plt.show()
# % plot time evolution  
# %% 
plt.title('Averaged time evolution')
plt.plot(np.average(rawI_row,1),label ='raw I')
plt.plot(np.average(rawQ_row,1),label ='raw Q')
plt.legend()
plt.xlabel('Frame number')
plt.ylabel('Averaged intensity pixel row')
ax2 = plt.gca().twinx()
avg_amp_row = np.average(amp_row,1)
ax2.plot(avg_amp_row-np.mean(avg_amp_row),label ='$(Q^2+I^2)^{(1/2)}$', c ='grey')
abs_amp_row = abs(avg_amp_row -np.mean(avg_amp_row))
ax2.plot(abs_amp_row,label ='$|(Q^2+I^2)^{(1/2)}|$', c ='black')
#ax2.plot(np.average(rawI_row/rawQ_row,1),label ='$I/Q$', c ='grey')
ax2.legend(loc='lower right')
plt.show()

