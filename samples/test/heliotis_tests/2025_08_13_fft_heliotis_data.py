import numpy as np
import matplotlib.pyplot as plt
import h5py
import os
from scipy.fft import fft, fftshift, ifftshift, fftfreq, ifft, fft2, ifft2
#from src.measurements.MeasurementClasses import TwoDMeasurement
from jki_python_bridge_for_labview import labview as lv
from matplotlib.patches import Rectangle



h = 4.135E-15 #eV/Hz
h_c = 1239.841984 #h * c in eV/nm
#lv.connect()
# %%
# input 
date = '2025-08-14' # '2025-07-24' # 
data_name =  'GaAs_QW_2501_11_50_55' # 'GaAs_QW_2501_16_08_00' #
bg_name =  'avg_data11_16_10' # 'avg_data17_11_58' # # load background  ;  CHANGE THIS IF TAU CHANGES THE 
path = r"D:\DATA\BIGFOOT"
title_id = os.path.join(date,data_name)


with h5py.File(os.path.join(path,date,bg_name + '.h5'), 'r') as f:
    bg_rawI_row = f['averaged_rawI'][263,:]
    bg_rawQ_row = f['averaged_rawQ'][263,:]

# create 2d map for fft (horizontal = amplitude with bg suppression, vertical = tau axis)
folder = os.path.join(path,date,data_name)
file_list = sorted(os.listdir(folder))


step = 0.02 # 0.02 # lv.LV_Control.read_scan_params()[1]  #SINCE THIS RETURNS NUMBERS WITH ++DECIMALS, I'M NOT SURE IT'S THE EXACT TAU POSITIONS THAT WILL BE SENT TO THE STAGE... SEE HOW PRECISE WE CAN ASK BF STAGE TO BE
tau_values = np.arange(0, 2+step, step)   #should import tau_max_value instead of writing '2.0'... how?
print(tau_values.shape)
print(len(file_list))
# %% load data
amp_map = np.zeros((len(file_list), bg_rawI_row.shape[0]))   #should be len(tau_values... but sometimes len(file_list) is different :(
print(amp_map.shape)

for i, filename in enumerate(file_list):
    filepath = os.path.join(folder, filename)

    with h5py.File(filepath, 'r') as f:
        rawI_row = f['rawI'][:, 263, :]  # shape: (n_avg, x)
        rawQ_row = f['rawQ'][:, 263, :]

        amp_row = np.sqrt((rawI_row-bg_rawI_row) ** 2 + (rawQ_row-bg_rawQ_row) ** 2)
        mean_amp_row = np.mean(amp_row, axis=0)
        amp_map[i, :] = mean_amp_row

amp_map = np.fliplr(amp_map)
# %% plot raw files
approx_x_axis = np.linspace(1429,1429+250,np.shape(amp_map)[1])
plt.pcolor(approx_x_axis,tau_values,amp_map)
#plt.pcolor(approx_x_axis,tau_values,amp_map-np.mean(amp_map,axis =0))
#plt.title(f'Raw data -mean(raw data) \n {title_id}') 
plt.title(f'Raw data \n {title_id}')  
plt.xlim(1530,1580)
plt.xlabel('Energy (meV)')
plt.ylabel('Time (ps)')
plt.colorbar()
plt.show()
amp_map_bg_correct = amp_map-np.mean(amp_map,axis =0)
amp_map = amp_map_bg_correct


# %% FT data as done for BF data 
padded_amp_map = np.pad(amp_map,((0,np.shape(amp_map)[0]),(0,0)))
num_padded_step = np.shape(padded_amp_map)[0]

ps_to_meV = 4.1356677
cal_tau_freq_step = ps_to_meV/(step*num_padded_step)
freq_shift = 1240/0.796 
cal_tau_freq_axis = np.linspace(-freq_shift-cal_tau_freq_step*num_padded_step/2,-freq_shift+cal_tau_freq_step*num_padded_step/2,num_padded_step)


freq_freq = fft(padded_amp_map, axis=0)
plt.pcolor(approx_x_axis, cal_tau_freq_axis,np.abs(freq_freq))
plt.xlim(1530,1580)
#plt.xlim(1545,1565)
#plt.ylim(-1565,-1545)
plt.title(f'FT Data \n {title_id}')  
plt.xlabel('Emission Energy (meV)')
plt.ylabel('Absorption Energy (meV)')


