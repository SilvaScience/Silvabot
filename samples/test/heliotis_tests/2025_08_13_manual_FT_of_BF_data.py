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
import matplotlib.ticker as ticker
from scipy.fft import fft2, fftshift, fftfreq, fft


# %% Load data 
data_folder = r'C:\DATA\BIGFOOT\2025-07-31\Run003'
h5_filename = bf.transform_to_HDF5(data_folder)
#h5_filename = r'c:\users\david\onedrive - universite de montreal\software\git\pharostable\data\BIGFOOT\2025-06-13\GaAs_QW_2501_2025-06-13_038_Bigfoot.h5'
data,header = bf.read_HDF5_file(h5_filename)

# %%plot data
plot_range = [1545,1565]
bfplot.plot_Reph_Re_Im_Abs(data,header,plot_range)

# there is already...
#   -> zero padding (after tau_max or after t_max? probably tau_max)
#   -> freq shift ? try with and without
#   -> FFT along t axis (to have freq)
#   -> if this doesn't allow to have extra 'fictive' data in negative taus, do fft and then ifft
#   -> result should be positive tau data + unmeasured ('fictive') negative taus, relatively symetric to positive data. Horizontal = frequency (i think this whole axis is 'real' (no fictive data) because of the absence of middle demarcation or symetry, but I'm not 100% sure)

# %%
# allocate data 
time_amp = data['raw']['TimeSpec_amp']
time_phase = data['raw']['TimeSpec_phase']
tau_freq = (time_amp*np.exp(1j*time_phase)).T  #tau vs t 2d map
t_axis = header['emission_energy']
tau_axis = header['stepped_axis_energy']
num_step = len(tau_axis)
tau_step = float(header['scan_params']['Step axis step (ps)'])
tau_start = float(header['scan_params']['Step axis start (ps)'])
tau_axis_time =np.linspace(tau_start,tau_start+tau_step*(num_step-1),num_step)

# plot raw data 
plt.pcolor(t_axis, tau_axis_time,np.abs(tau_freq))
plt.ylabel('Tau (ps)')
plt.xlabel('Energy (meV)')
plt.xlim(1530,1580)
plt.ylim(0,2)
plt.colorbar()
plt.title(f'Raw data \n {header['file_id']}')
#plt.clim(0,0.02)
plt.show()
# %% plot fft of tau

# calculate fft axis 
ps_to_meV = 4.1356677
cal_tau_freq_step = ps_to_meV/(tau_step*num_step)
freq_shift = 1240/0.796 
cal_tau_freq_axis = np.linspace(-freq_shift-cal_tau_freq_step*num_step/2,-freq_shift+cal_tau_freq_step*num_step/2,num_step)

freq_freq = fft(tau_freq, axis=0)

plt.pcolor(t_axis, tau_axis,np.abs(freq_freq))
plt.xlim(1545,1565)
plt.ylim(-1565,-1545)
plt.xlabel('Emission Energy (meV)')
plt.ylabel('Absorption Energy (meV)')
formatter = ticker.FormatStrFormatter('%.0f')
plt.gca().xaxis.set_major_formatter(formatter)
plt.gca().yaxis.set_major_formatter(formatter)
plt.title(f'fft-transformed data \n {header['file_id']}')
#plt.ylim(0,2)
plt.colorbar()
#plt.clim(0,2.5)
#plt.xlim(15, 55)
#plt.ylim(70,25)
plt.show()