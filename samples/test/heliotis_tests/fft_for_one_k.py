# -*- coding: utf-8 -*-
"""
Created on Fri Jul 18 18:04:25 2025

@author: bviscogliosi
"""
import numpy as np
import matplotlib.pyplot as plt
import h5py
import os
from scipy.fft import fft, fftshift, fftfreq
from src.measurements.MeasurementClasses import TwoDMeasurement

# %%

#filename = r"C:\DATA\BIGFOOT\2025-07-16\GaAs_QW_2501_17_11_15.h5"

#with h5py.File(filename, 'r') as f:   # Access the dataset by name and load its content into a NumPy array
#    tau_values = f['parameter'][11]
#    twoD_data = f['spectra'][1:,263,:]
#print(tau_values)
#print(np.shape(twoD_data))





########################## NEW METHOD:

# load background  ;  CHANGE THIS IF TAU CHANGES THE BG !!!
folder_bg = r"C:\DATA\BIGFOOT\2025-07-24"
filename_bg = 'avg_data14_27_35'
with h5py.File(folder_bg + "\\" + filename_bg + '.h5', 'r') as f:
    bg_rawI_row = f['averaged_rawI'][263,:]
    bg_rawQ_row = f['averaged_rawQ'][263,:]

# create 2d map for fft (horizontal = amplitude with bg suppression, vertical = tau axis)
folder = r"C:\DATA\BIGFOOT\2025-07-24\GaAs_QW_2501_14_24_54"
file_list = sorted(os.listdir(folder))
print(file_list)

tau_values = TwoDMeasurement.get_tau_array(2.0)   #should import tau_max_value instead of writing '2.0'... how?
print(tau_values.shape)
print(len(file_list))
amp_map = np.zeros((len(file_list), bg_rawI_row.shape[0]))    #should be len(tau_values)

for i, filename in enumerate(file_list):
    filepath = os.path.join(folder, filename)

    with h5py.File(filepath, 'r') as f:
        rawI_row = f['rawI'][:, 263, :]  # shape: (n_avg, x)
        rawQ_row = f['rawQ'][:, 263, :]

        amp_row = np.sqrt((rawI_row- bg_rawI_row) ** 2 + (rawQ_row - bg_rawQ_row) ** 2)
        mean_amp_row = np.mean(amp_row, axis=0)
        amp_map[i, :] = mean_amp_row

amp_map = np.flipud(amp_map) # flip vertically for tau=0 at the bottom


# %%
plt.imshow(amp_map, aspect='auto', extent=[0,amp_map.shape[1], 0, tau_values[-1]])  #extent = axis values from (left, right, bottom, top)
plt.xlabel('pixel_x (-> Emission energy)')
plt.ylabel('tau (ps)')
plt.title(f'2D Map for fft generated with pixel_y = 263 \n {folder}')
plt.colorbar(label='Amplitude')
plt.show()

print(amp_map.shape)

# %%

fft= fft(amp_map, axis=0)  #gives complex data

fft_shifted = fftshift(fft, axes=0)  #shifts the zero component to the middle so does negative->0->positive (vertically)

freqs = fftfreq(amp_map.shape[0], d=(tau_values[1]-tau_values[0])*(10**(-12)))  #d = time between each tau step i think (in seconds)... 0.15ps for now
freqs_shifted = fftshift(freqs) #, axes=0)  #shifts the freqs axis too

fft_magnitude = np.abs(fft_shifted)  #gives amplitude of complex data


# %%

plt.figure(figsize=(10, 6))
extent = [0, amp_map.shape[1], freqs_shifted[0], freqs_shifted[-1]]  # x: pixels, y:  freq
plt.imshow(fft_magnitude, aspect='auto', origin='lower', extent=extent, cmap='viridis')
plt.xlabel('Horizontal pixel index')
plt.ylabel('Frequency [Hz]')
plt.title(f'2D Spectrum generated with pixel_y = 263 \n {folder}')
plt.colorbar()
#plt.clim(175,300)
plt.tight_layout()
plt.show()
