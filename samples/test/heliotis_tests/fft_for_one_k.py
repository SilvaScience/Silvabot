# -*- coding: utf-8 -*-
"""
Created on Fri Jul 18 18:04:25 2025

@author: bviscogliosi
"""
import numpy as np
import matplotlib.pyplot as plt
import h5py
from scipy.fft import fft, fftshift, fftfreq


# %%

filename = r"C:\DATA\BIGFOOT\2025-07-16\GaAs_QW_2501_17_11_15.h5"

with h5py.File(filename, 'r') as f:   # Access the dataset by name and load its content into a NumPy array
    tau_values = f['parameter'][11]
    twoD_data = f['spectra'][1:,263,:]
print(tau_values)
print(np.shape(twoD_data))


# %%

fft= fft(twoD_data, axis=0)  #gives complex data

fft_shifted = fftshift(fft, axes=0)  #shifts the zero component to the middle so does negative->0->positive (vertically)

freqs = fftfreq(np.shape(twoD_data)[0], d=(tau_values[1]-tau_values[0])*(10**(-12)))  #d = time between each tau step i think (in seconds)... 0.15ps for now
freqs_shifted = fftshift(freqs)  #shifts the freqs axis too

fft_magnitude = np.abs(fft_shifted)  #gives amplitude of complex data


# %%

plt.figure(figsize=(10, 6))
plt.imshow(fft_magnitude, aspect='auto', origin='lower', cmap='viridis')
plt.xlabel('Horizontal pixel index')
plt.ylabel('Frequency [Hz]')
plt.title('2D spectrum for pixels (263,:)')
plt.colorbar()
plt.tight_layout()
plt.show()

#NOT ON THE RIGHT SIDE I THINK... asked cgpt (see below :)

# %%

plt.figure(figsize=(10, 6))
extent = [0, twoD_data.shape[1], freqs_shifted[0], freqs_shifted[-1]]  # x: pixels, y: freq
plt.imshow(fft_magnitude.T, aspect='auto', extent=extent, origin='lower', cmap='magma')
plt.xlabel('Horizontal pixel index')
plt.ylabel('Frequency [Hz]')
plt.title('2D spectrum for pixels (263,:)')
plt.colorbar()
plt.tight_layout()
plt.show()