# -*- coding: utf-8 -*-
"""
Created on Mon Jul 21 15:58:48 2025

@author: bviscogliosi
"""

import numpy as np
import matplotlib.pyplot as plt
import h5py
from scipy.fft import fft, fftshift, fftfreq
from matplotlib.patches import Rectangle
import os 

# %%  
# load background 
folder = r"C:\DATA\BIGFOOT\2025-07-23"
filename_bg = 'avg_data18_15_25'
with h5py.File(folder + "\\" + filename_bg + '.h5', 'r') as f:
    bg_rawI = f['averaged_rawI'][:]
    bg_rawQ = f['averaged_rawQ'][:]

# load data 
folder = r"C:\DATA\BIGFOOT\2025-07-23"
filename_data = 'raw_data18_20_02'
with h5py.File(folder + "\\" + filename_data + '.h5', 'r') as f:
    data_rawI = f['rawI'][:]
    data_rawQ = f['rawQ'][:]
amp = np.sqrt((data_rawI-bg_rawI)**2 +(data_rawQ-bg_rawQ)**2) 
amp = np.mean(amp, axis=0)


# %%
plt.imshow(bg_rawI)
plt.colorbar()
plt.show()
plt.imshow(np.mean(data_rawI,axis=0))
plt.title('raw I')
plt.xlim(150,300)
plt.ylim(250,280)
plt.colorbar()
plt.show()

#%%
title = f"Amplitude (with bg suppression) \n Generated with: {filename_data} \n{filename_bg} \n Ref power: 0.2mW 100frames"
#amp_wo_bg =np.transpose(amp_wo_bg)
#amp = np.transpose(amp)
#np.shape(amp)

plt.imshow(amp)
x_range = (185, 275) # x range as displayed in Silvabot (in the 512 pixels) (focus on brightest spots to find optimal frequency and phase)
y_range = (261, 264) # y range as displayed in Silvabot (in the 542 pixels)
plt.gca().add_patch(Rectangle((x_range[0],y_range[0]), x_range[1]-x_range[0], y_range[1]-y_range[0],edgecolor='red',facecolor='none'))
plt.xlim(160,300)
plt.ylim(250,275)
plt.colorbar()
plt.title(title)
plt.show()

# %%
amp_int= np.mean(amp[y_range[0]:y_range[1],x_range[0]:x_range[1]],axis=0)
x_axis = np.linspace(1577,1550,len(amp_int))
plt.plot(x_axis,amp_int)
plt.xlabel("approx. Energy (meV)")
plt.ylabel("Amplitude")
plt.title(title)
plt.show()