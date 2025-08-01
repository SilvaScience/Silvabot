# -*- coding: utf-8 -*-
"""
Created on Tue Apr 22 23:50:11 2025

@author: David Tiede
"""
                   
import sys
#sys.path.insert(0, r'C:\Users\david\OneDrive - Universite de Montreal\software\Git\mdsam')
from mdsam.BF import Bigfoot as bf
from mdsam.BF_plots import BFPlots as bfplot 
import numpy as np
import matplotlib.pyplot as plt
from scipy.fft import fft2, fftshift, fftfreq, fft


# %% Load data 
data_folder = r'C:\DATA\BIGFOOT\2025-07-31\Run003'
h5_filename = bf.transform_to_HDF5(data_folder)
#h5_filename = r'c:\users\david\onedrive - universite de montreal\software\git\pharostable\data\BIGFOOT\2025-06-13\GaAs_QW_2501_2025-06-13_038_Bigfoot.h5'
data,header = bf.read_HDF5_file(h5_filename)

# %%plot data
plot_range = [1545,1565]
bfplot.plot_Reph_Re_Im_Abs(data,header,plot_range)

# allocate data 
time_amp = data['raw']['TimeSpec_amp']
time_phase = data['raw']['TimeSpec_phase']
tau_t = (time_amp*np.exp(1j*time_phase)).T  #tau vs t 2d map
plt.imshow(np.abs(tau_t), aspect='auto')
plt.ylabel('tau')
plt.xlabel('t')
plt.show()

tau_t_reordered = fftshift(tau_t, axes=0)
plt.imshow(np.abs(tau_t_reordered), aspect='auto')
plt.xlim(15,55)
plt.ylim(85, 30)
plt.show()

# frequency shift to center around 1e14 Hz
#f_shift_eV = 1.56
#tau_values = np.linspace(0, 2.0, tau_t.shape[0])
#t_values = np.linspace(-0.35, 1.15, tau_t.shape[1])
#tau_t_freq_shifted = tau_t*np.exp(-1j * 2 * np.pi * f_shift_eV * tau_values[:, np.newaxis])
#tau_t_freq_shifted = tau_t_freq_shifted*np.exp(-1j * 2 * np.pi * f_shift_eV * t_values[np.newaxis, :])
#plt.imshow(np.abs(tau_t_freq_shifted), aspect='auto')
#plt.ylabel('tau')
#plt.xlabel('t')
#plt.show()
 
# fft along t axis to get tau vs freq and compare with heliotis data

# 2d fft on tau_t or half of tau_t (test both)
cropped_tau_t = tau_t[:int(tau_t.shape[0]/2), :]
#plt.imshow(np.abs(cropped_tau_t), aspect='auto')
#plt.show()

freq_freq = fft(cropped_tau_t, axis=0)
#em_freqs = fftfreq(freq_freq.shape[1], d=(1.5e-12)/freq_freq.shape[1])  good if there is no frequency shift
#abs_freqs = fftfreq(freq_freq.shape[0], d=(2e-12)/freq_freq.shape[0])
#abs_freq_step_meV =  4.1356677 / ((tau_values[1]-tau_values[0]) * freq_freq.shape[0] * 2)  #i put a *2 because of the padding (see eric's mail). i should probably just remove this and give the whole uncropped data
#em_freq_step_meV =  4.1356677 / ((t_values[1]-t_values[0]) * freq_freq.shape[1])
#extent = [f_shift_eV*1e3 - (freq_freq.shape[1]*em_freq_step_meV/2), f_shift_eV*1e3 + (freq_freq.shape[1]*em_freq_step_meV/2), f_shift_eV*1e3 - (freq_freq.shape[0]*abs_freq_step_meV/2), f_shift_eV*1e3 + (freq_freq.shape[0]*abs_freq_step_meV/2)]

plt.imshow(np.flipud(np.abs(freq_freq)), aspect='auto')
plt.colorbar()
plt.clim(0,1)
plt.xlim(20, 50)
plt.ylim(35,10)
plt.show()