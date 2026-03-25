# -*- coding: utf-8 -*-
"""
Created on Mon Jul  7 11:03:51 2025

@author: bviscogliosi

CREATED BY CGPT
"""

import numpy as np
import matplotlib.pyplot as plt
import h5py
import time
from scipy.optimize import curve_fit
from joblib import Parallel, delayed



# --- Charger les données ---
folder = r"C:\DATA\BIGFOOT\2025-07-04"
filename = folder + "\\" + "raw_data_11_01_22.h5"

with h5py.File(filename, 'r') as f:
    rawI = f['rawI'][:]
    rawQ = f['rawQ'][:]

# --- Fit sur l'intensité moyenne pour obtenir omega_general et phase_general ---
def sine_function(x, A, omega, phase, offset):
    return A * np.sin(omega * x + phase) + offset

avg_I = np.mean(rawI, axis=(1, 2))
avg_Q = np.mean(rawQ, axis=(1, 2))
IdivQ = avg_I / avg_Q
frame_nbr = np.arange(rawI.shape[0])

initial_guess = [0.01, 0.2, -0.2, 0.985]
popt, _ = curve_fit(sine_function, frame_nbr, IdivQ, p0=initial_guess)
A_general, omega_general, phase_general, offset_general = popt

# --- Préparer la base sinusoïdale fixe ---
s = np.sin(omega_general * frame_nbr + phase_general)  # shape (frames,)
X = np.vstack([s, np.ones_like(s)]).T  # shape (frames, 2)

# --- Calculer I/Q une seule fois ---
with np.errstate(divide='ignore', invalid='ignore'):
    ydata = np.where(rawQ != 0, rawI / rawQ, np.nan)  # shape (frames, Ny, Nx)

Ny, Nx = rawI.shape[1], rawI.shape[2]
A_opt = np.full((Ny, Nx), np.nan)
offset_opt = np.full((Ny, Nx), np.nan)

# --- Fonction de fit analytique pour un pixel ---
def fit_pixel_linear(i, j):
    y = ydata[:, i, j]
    if np.any(np.isnan(y)):
        return i, j, np.nan, np.nan
    try:
        coeffs, *_ = np.linalg.lstsq(X, y, rcond=None)
        return i, j, coeffs[0], coeffs[1]  # A, offset
    except:
        return i, j, np.nan, np.nan

# --- Paralléliser ---
t0 = time.time()
results = Parallel(n_jobs=-1, prefer="processes")(
    delayed(fit_pixel_linear)(i, j)
    for i in range(Ny)
    for j in range(Nx)
)
for i, j, A, offset in results:
    A_opt[i, j] = A
    offset_opt[i, j] = offset
print("Duration:", time.time() - t0)

# --- Affichage ---
plt.imshow(A_opt, cmap='viridis')
plt.title("Amplitude 1")
plt.colorbar()
plt.show()

plt.imshow(offset_opt, cmap='viridis')
plt.title("Offset 1")
plt.colorbar()
plt.show()








# --- Charger les données ---
folder = r"C:\DATA\BIGFOOT\2025-07-04"
filename = folder + "\\" + "raw_data_11_01_23.h5"

with h5py.File(filename, 'r') as f:
    rawI = f['rawI'][:]
    rawQ = f['rawQ'][:]

# --- Fit sur l'intensité moyenne pour obtenir omega_general et phase_general ---
def sine_function(x, A, omega, phase, offset):
    return A * np.sin(omega * x + phase) + offset

avg_I = np.mean(rawI, axis=(1, 2))
avg_Q = np.mean(rawQ, axis=(1, 2))
IdivQ = avg_I / avg_Q
frame_nbr = np.arange(rawI.shape[0])

initial_guess = [0.01, 0.2, -0.2, 0.985]
popt, _ = curve_fit(sine_function, frame_nbr, IdivQ, p0=initial_guess)
A_general, omega_general, phase_general, offset_general = popt

# --- Préparer la base sinusoïdale fixe ---
s = np.sin(omega_general * frame_nbr + phase_general)  # shape (frames,)
X = np.vstack([s, np.ones_like(s)]).T  # shape (frames, 2)

# --- Calculer I/Q une seule fois ---
with np.errstate(divide='ignore', invalid='ignore'):
    ydata = np.where(rawQ != 0, rawI / rawQ, np.nan)  # shape (frames, Ny, Nx)

Ny, Nx = rawI.shape[1], rawI.shape[2]
A_opt_ = np.full((Ny, Nx), np.nan)
offset_opt_ = np.full((Ny, Nx), np.nan)

# --- Fonction de fit analytique pour un pixel ---
def fit_pixel_linear(i, j):
    y = ydata[:, i, j]
    if np.any(np.isnan(y)):
        return i, j, np.nan, np.nan
    try:
        coeffs, *_ = np.linalg.lstsq(X, y, rcond=None)
        return i, j, coeffs[0], coeffs[1]  # A, offset
    except:
        return i, j, np.nan, np.nan

# --- Paralléliser ---
t0 = time.time()
results = Parallel(n_jobs=-1, prefer="processes")(
    delayed(fit_pixel_linear)(i, j)
    for i in range(Ny)
    for j in range(Nx)
)
for i, j, A, offset in results:
    A_opt_[i, j] = A
    offset_opt_[i, j] = offset
print("Duration:", time.time() - t0)

# --- Affichage ---
plt.imshow(A_opt_, cmap='viridis')
plt.title("Amplitude 2")
plt.colorbar()
plt.show()

plt.imshow(offset_opt_, cmap='viridis')
plt.title("Offset 2")
plt.colorbar()
plt.show()


############# Plus le temps avance, plus le offsetmap est gros car offset_opt_ > offset_opt, idem amplitude
plt.imshow(A_opt_ + A_opt, cmap = 'viridis')
plt.title("Amplitude difference")
plt.colorbar()
#plt.clim(-0.00002,0.00002)
plt.show()
plt.imshow(offset_opt_ - offset_opt, cmap = 'viridis')
plt.title("Offset difference")
plt.colorbar()
#plt.clim(-0.00002,0.00002)
plt.show()

print('Average Amplitude increase :', np.mean(A_opt_-A_opt))
print('Average Offset increase :', np.mean(offset_opt_-offset_opt))



# %%
image = (rawI/rawQ)[33,:,:]
plt.imshow(image)