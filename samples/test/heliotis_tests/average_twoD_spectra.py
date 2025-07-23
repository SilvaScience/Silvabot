# -*- coding: utf-8 -*-
"""
Created on Mon Jul 21 15:58:48 2025

@author: bviscogliosi
"""

import numpy as np
import matplotlib.pyplot as plt
import h5py
from scipy.fft import fft, fftshift, fftfreq

# %%  TO CHOOSE AN INTEGER FRAMERATE
framerate_range = np.linspace(500,700,101)
print(29796/framerate_range)

#framerate = 29796/printed_int



# %%  
filename = r"C:\DATA\BIGFOOT\2025-07-21\29796Hz_GaAs_QW_2501_17_31_17.h5"

with h5py.File(filename, 'r') as f:   # Access the dataset by name and load its content into a NumPy array
    twoD_spectra = f['spectra'][1:,:,:]
print(np.shape(twoD_spectra))
twoD_averaged = np.mean(twoD_spectra, axis = 0)
plt.imshow(twoD_averaged)