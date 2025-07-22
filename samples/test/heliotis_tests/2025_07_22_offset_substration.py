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
folder = r"C:\DATA\BIGFOOT\2025-07-22\background_wo_light"
filenames = os.listdir(folder)
bg_shape = (len(filenames),542,512)  # *np.shape(rawI))
print(bg_shape)
bg_rawI = np.zeros(bg_shape)
bg_rawQ = np.zeros(bg_shape)
for i, filename in enumerate(filenames):
    with h5py.File(folder + "\\" + filename, 'r') as f:
        bg_rawI[i] = f['averaged_rawI'][:]
        bg_rawQ[i] = f['averaged_rawQ'][:]
bg_rawI_wo_light = np.mean(bg_rawI, axis=0)
bg_rawQ_wo_light = np.mean(bg_rawQ, axis=0)

folder = r"C:\DATA\BIGFOOT\2025-07-22\background"
filenames = os.listdir(folder)
bg_shape = (len(filenames),542,512)  # *np.shape(rawI))
print(bg_shape)
bg_rawI = np.zeros(bg_shape)
bg_rawQ = np.zeros(bg_shape)
for i, filename in enumerate(filenames):
    with h5py.File(folder + "\\" + filename, 'r') as f:
        bg_rawI[i] = f['averaged_rawI'][:]
        bg_rawQ[i] = f['averaged_rawQ'][:]
bg_rawI = np.mean(bg_rawI, axis=0)
bg_rawQ = np.mean(bg_rawQ, axis=0)


print(bg_shape)
folder = r"C:\DATA\BIGFOOT\2025-07-22\non_avg_data"
filenames = os.listdir(folder)
bg_shape = (len(filenames),542,512)  # *np.shape(rawI))
data_rawI = np.zeros(bg_shape)
data_rawQ = np.zeros(bg_shape)
for i, filename in enumerate(filenames):
    with h5py.File(folder + "\\" + filename, 'r') as f:
        print(np.shape(f['rawI'][:]))
        data_rawI = f['rawI'][:]
        data_rawQ = f['rawQ'][:]
amp = np.sqrt((data_rawI-bg_rawI)**2 +(data_rawQ-bg_rawQ)**2)
amp_w_bg = np.sqrt((data_rawI)**2 +(data_rawQ)**2)
amp = np.mean(amp, axis=0)
amp_w_bg = np.mean(amp_w_bg, axis=0)
print(np.sum(bg_rawI))

# %% 
#plt.imshow(bg_rawI) #-bg_rawI_wo_light
plt.imshow(np.mean(data_rawI,axis=0))
plt.xlim(150,300)
plt.ylim(250,280)
plt.colorbar()
#%%
#amp = np.sqrt((data_rawI-bg_rawI)**2 +(data_rawQ-bg_rawQ)**2)
#amp_w_bg = np.sqrt((data_rawI)**2 +(data_rawQ)**2)
#amp_w_bg =np.transpose(amp_w_bg)
#amp = np.transpose(amp)
x_range = (190, 260) # x range as displayed in Silvabot (in the 512 pixels) (focus on brightest spots to find optimal frequency and phase)
y_range = (261, 263) # y range as displayed in Silvabot (in the 542 pixels)
np.shape(amp)

plt.imshow(amp)
plt.gca().add_patch(Rectangle((x_range[0],y_range[0]), x_range[1]-x_range[0], y_range[1]-y_range[0],edgecolor='red',facecolor='none'))
plt.xlim(150,300)
plt.ylim(250,280)
#plt.clim(0,2)
#plt.Rectangle((200,262), 70, 8)
plt.colorbar()
plt.title("test")
plt.show()

#%%
plt.imshow(amp[y_range[0]:y_range[1],x_range[0]:x_range[1]])
plt.colorbar()
plt.show()
# %%
amp_int= np.mean(amp[y_range[0]:y_range[1],x_range[0]:x_range[1]],axis=0)
x_axis = np.linspace(1577,1550,len(amp_int))
plt.plot(x_axis,amp_int)
plt.xlabel("approx. Energy (meV)")