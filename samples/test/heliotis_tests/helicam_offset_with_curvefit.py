# -*- coding: utf-8 -*-
"""
Created on Fri Jul  4 10:49:07 2025

@author: bviscogliosi
"""

import h5py
import numpy as np
import matplotlib.pyplot as plt     
from scipy.optimize import curve_fit
import time 
from joblib import Parallel, delayed, cpu_count


# Open the file in read mode
folder = r"C:\DATA\BIGFOOT\2025-07-04"
filename = folder + "\\" + "raw_data_11_01_22.h5"

with h5py.File(filename, 'r') as f:
    # Access the dataset by name and load its content into a NumPy array
    rawI = f['rawI'][:]
    rawQ = f['rawQ'][:]
    
raw_data = rawI / rawQ

print('Nbr of CPUs :',cpu_count())
# %% plot raw data

plt.pcolor(rawI[3])
plt.plot()
plt.show()

# %% plot curve fit on average of all pixels per frame
def sine_function(x, A, omega, phase, offset):
    return A * np.sin(omega * x + phase) + offset

avg_I = np.average(np.average(rawI,axis = 1),axis =1)
avg_Q = np.average(np.average(rawQ,axis = 1),axis =1)
IdivQ = avg_I/avg_Q

plt.plot(IdivQ, label='average of each frame')

# Initial guess: [amplitude, angular freq, phase, offset]
initial_guess = [0.01, 0.2, -.2, 0.985]

# Perform the curve fit
frame_nbr = np.r_[0:rawI.shape[0]].astype(float)
popt, pcov = curve_fit(sine_function, frame_nbr, IdivQ, p0=initial_guess)
A_general, omega_general, phase_general, offset_general = popt
plt.plot(frame_nbr,sine_function(frame_nbr, A_general, omega_general, phase_general, offset_general), label='curve fit')
print(popt)
plt.legend()
plt.show()


# %% curve fit on each pixel
def sine_function_fixed_omega_phase(x, A, offset):
    return A * np.sin(omega_general * x + phase_general) + offset

A_opt = np.zeros_like(rawI[0,:,:],dtype=float)
offset_opt = np.zeros_like(rawI[0,:,:],dtype=float)
initial_guess = [0.01, 0.985]

t1 = time.time()
duration = 0.
for i in range(rawI.shape[1]): 
    for j in range(rawI.shape[2]):
        popt, pcov = curve_fit(sine_function_fixed_omega_phase, frame_nbr, raw_data[:,i,j], p0=initial_guess, maxfev=2000)
        A_opt[i,j], offset_opt[i,j] = popt

print('Duration :',time.time()-t1)  #Result : 25,6sec

# %% CGPT method to make calculations faster using all the processors instead of one
def sine_function_fixed_omega_phase(x, A, offset):
    return A * np.sin(omega_general * x + phase_general) + offset

A_opt = np.zeros_like(rawI[0,:,:],dtype=float)
offset_opt = np.zeros_like(rawI[0,:,:],dtype=float)
initial_guess = [0.01, 0.985]

def fit_pixel(i, j):
        popt, _ = curve_fit(
            sine_function_fixed_omega_phase,
            frame_nbr,
            raw_data[:,i,j],
            p0=initial_guess,
            maxfev=2000
        )
        return i, j, popt[0], popt[1]

# Get shape
Ny, Nx = rawI.shape[1], rawI.shape[2]

# Launch parallel fitting
t2 = time.time()
results = Parallel(n_jobs=-1, prefer="processes")(
    delayed(fit_pixel)(i, j) for i in range(Ny) for j in range(Nx)
)

# Store results
for i, j, A_val, offset_val in results:
    A_opt[i, j] = A_val
    offset_opt[i, j] = offset_val

print('Duration :',time.time()-t2)  #Result : 6,2sec

# %% plot background offset and amplitude 2d map
plt.imshow(A_opt)
plt.title('Amplitude')
plt.colorbar()
#plt.clim(0,0.08)
plt.show()
#plt.imshow(omega_opt)
#plt.title('Omega')
#plt.colorbar()
#plt.clim(0.1,0.2)
#plt.show()
#plt.imshow(phase_opt)
#plt.title('Phase')
#plt.colorbar()
#plt.clim(-0.2,0.2)
#plt.show()
plt.imshow(offset_opt)
plt.title('Offset')
plt.colorbar()
#plt.clim(0.98,0.99)
plt.show()

plt.plot(sine_function_fixed_omega_phase(frame_nbr, A_opt[111,111], offset_opt[111,111]))
plt.plot(rawI[:,111,111]/rawQ[:,111,111])
plt.show()