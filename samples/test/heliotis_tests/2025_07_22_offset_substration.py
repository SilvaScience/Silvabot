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
bg_rawI_light = np.mean(bg_rawI, axis=0)
bg_rawQ_light = np.mean(bg_rawQ, axis=0)

folder = r"C:\DATA\BIGFOOT\2025-07-22\non_avg_data"
filenames = os.listdir(folder)
bg_shape = (len(filenames),542,512)  # *np.shape(rawI))
data_rawI = np.zeros(bg_shape)
data_rawQ = np.zeros(bg_shape)
for i, filename in enumerate(filenames):
    with h5py.File(folder + "\\" + filename, 'r') as f:
        data_rawI = f['rawI'][:]    #no [i] !?
        data_rawQ = f['rawQ'][:]
        print(np.shape(data_rawI))
amp = np.sqrt((data_rawI-bg_rawI_light)**2 +(data_rawQ-bg_rawQ_light)**2)    #there was maybe an error here in the code ; always deleting 'bg_rawI' which was empty in option 1 (bg_wo_light) but full in option 2 (bg). i renamed the background of option2 'bg_rawI_light' instead of 'bg_rawI'
amp_wo_bg = np.sqrt((data_rawI)**2 +(data_rawQ)**2)                          #hmmm no it was not an error but just a questionable choice of variable name
amp = np.mean(amp, axis=0)
amp_wo_bg = np.mean(amp_wo_bg, axis=0)

print('SUM :')
print(np.sum(bg_rawI_wo_light))
print(np.sum(bg_rawI_light))

# %%
plt.imshow(bg_rawI_wo_light)
plt.colorbar()
plt.show()
plt.imshow(bg_rawI_light)
plt.colorbar()
plt.show()
plt.imshow(bg_rawI_wo_light - bg_rawI_light)
plt.title('background difference')
plt.colorbar()
plt.show()
plt.imshow(np.mean(data_rawI,axis=0))
plt.title('raw I')
plt.xlim(150,300)
plt.ylim(250,280)
plt.colorbar()
plt.show()

#%%
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
plt.title("Amplitude (with bg suppression)")
plt.show()

# %%
amp_int= np.mean(amp[y_range[0]:y_range[1],x_range[0]:x_range[1]],axis=0)
x_axis = np.linspace(1577,1550,len(amp_int))
plt.plot(x_axis,amp_int)
plt.xlabel("approx. Energy (meV)")
plt.ylabel("Amplitude")
plt.show()