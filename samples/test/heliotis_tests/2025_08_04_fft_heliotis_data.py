import numpy as np
import matplotlib.pyplot as plt
import h5py
import os
from scipy.fft import fft, fftshift, ifftshift, fftfreq, ifft, fft2, ifft2
#from src.measurements.MeasurementClasses import TwoDMeasurement
from jki_python_bridge_for_labview import labview as lv
from matplotlib.patches import Rectangle



h = 4.135E-15 #eV/Hz
h_c = 1239.841984 #h * c in eV/nm
#lv.connect()
# %%

# load background  ;  CHANGE THIS IF TAU CHANGES THE BG
folder_bg = r"C:\DATA\BIGFOOT\2025-08-04"
filename_bg = 'avg_data16_12_12'
with h5py.File(folder_bg + "\\" + filename_bg + '.h5', 'r') as f:
    bg_rawI_row = f['averaged_rawI'][263,:]
    bg_rawQ_row = f['averaged_rawQ'][263,:]

# create 2d map for fft (horizontal = amplitude with bg suppression, vertical = tau axis)
folder = r"C:\DATA\BIGFOOT\2025-08-04\GaAs_QW_2501_16_10_35"
file_list = sorted(os.listdir(folder))

step = 0.02 # lv.LV_Control.read_scan_params()[1]  #SINCE THIS RETURNS NUMBERS WITH ++DECIMALS, I'M NOT SURE IT'S THE EXACT TAU POSITIONS THAT WILL BE SENT TO THE STAGE... SEE HOW PRECISE WE CAN ASK BF STAGE TO BE
tau_values = np.arange(0, 3.0 + step, step)   #should import tau_max_value instead of writing '2.0'... how?
print(tau_values.shape)
print(tau_values)
print(len(file_list))
amp_map = np.zeros((len(file_list), bg_rawI_row.shape[0]))   #should be len(tau_values... but sometimes len(file_list) is different :(
print(amp_map.shape)

for i, filename in enumerate(file_list):
    filepath = os.path.join(folder, filename)

    with h5py.File(filepath, 'r') as f:
        rawI_row = f['rawI'][:, 263, :]  # shape: (n_avg, x)
        rawQ_row = f['rawQ'][:, 263, :]

        amp_row = np.sqrt((rawI_row-bg_rawI_row) ** 2 + (rawQ_row-bg_rawQ_row) ** 2)
        mean_amp_row = np.mean(amp_row, axis=0)
        amp_map[i, :] = mean_amp_row

amp_map = np.fliplr(amp_map)
plt.imshow(np.abs(amp_map), aspect='auto', extent=[1429, 1429+250, tau_values[-1], tau_values[0]])
plt.title('amp_map')
#plt.xlim(1530,1580)
plt.colorbar()
plt.show()

plt.plot(tau_values[:len(file_list)], np.average(amp_map,axis=1))
plt.show()


# CODE INSPIRED BY BF DATA PROCESSING

tau_t = ifft(amp_map, axis=1)
plt.imshow(np.abs(fftshift(tau_t, axes=1)), aspect='auto')
plt.title('tau_t with  (centered 0)')
plt.colorbar()
plt.show()

f_shift_eV = 1.5292
f_shift_hz = f_shift_eV / h  #go close to features around 1.555eV
t = tau_values*(10**(-12))
tau_t_f_shifted = np.zeros_like(tau_t, dtype=complex)
for column in range(tau_t.shape[1]):
    tau_t_f_shifted[:,column] = tau_t[:,column] * np.exp(-1j * 2 * np.pi * f_shift_hz * t[:len(file_list)])
plt.imshow(np.abs(tau_t_f_shifted), aspect='auto')
plt.title('tau_t_f_shifted (not centered 0)')
plt.show()

tau_t_padded = np.pad(tau_t, ((0, tau_t.shape[0]), (0, 0)), mode='constant')
plt.imshow(np.abs(tau_t_padded), aspect='auto')
plt.title('tau_t_padded (not centered 0)')
plt.show()

tau_freq_like_BF = fft(tau_t_padded, axis=1)
plt.imshow(np.abs(tau_freq_like_BF), aspect='auto')
plt.title('tau_freq_like_BF (not centered 0)')
plt.show()

tau_freq_like_BF = fft(ifft(tau_freq_like_BF, axis=0),axis=0)
plt.imshow(np.abs(tau_freq_like_BF), aspect='auto')
plt.title('tau_freq_like_BF after fft(ifft()) (not centered 0)')
plt.show()

plt.imshow(np.abs(tau_freq_like_BF[int(tau_freq_like_BF.shape[0]/2):,:]), aspect='auto')
plt.title('fictive half')
plt.colorbar()
plt.show()

## now, can do the same code as 2025_07_31_manual_FT_of_BF_data.py
tau_freq_reordered = fftshift(tau_freq_like_BF, axes=0)
plt.imshow(np.abs(tau_freq_reordered), aspect='auto')
plt.title('tau_freq_reordered')
plt.show()

cropped_tau_freq = tau_freq_like_BF[int(tau_freq_like_BF.shape[0]/2):, :]

freq_freq = fft(cropped_tau_freq, axis=0)
N_tot = freq_freq.shape[0]
freq_step_meV = 4.1356677 / ((tau_values[1]-tau_values[0]) * N_tot)
extent = [1429, 1429+250, f_shift_eV*1e3 - (N_tot*freq_step_meV/2), f_shift_eV*1e3 + (N_tot*freq_step_meV/2)]
plt.imshow(np.flipud(np.abs(fftshift(freq_freq,axes=0))), aspect='auto',extent=extent)
plt.colorbar()
plt.title('2d freq_freq with fictive half')
#plt.clim(6e-15,)
plt.xlim(1540, 1590)
#plt.ylim(1540, 1560)
#plt.ylim(35,0)
plt.show()

freq_freq = fft(tau_freq_reordered, axis=0)
N_tot = freq_freq.shape[0]
freq_step_meV = 4.1356677 / ((tau_values[1]-tau_values[0]) * N_tot)
extent = [1429, 1429+250, f_shift_eV*1e3 - (N_tot*freq_step_meV/2), f_shift_eV*1e3 + (N_tot*freq_step_meV/2)]
plt.imshow(np.flipud(np.abs(fftshift(freq_freq,axes=0))), aspect='auto', extent=extent)
plt.colorbar()
plt.title('2d freq_freq with tau_freq_reordered (like BF)')
#plt.clim(0,80)
#plt.xlim(15, 55)
#plt.ylim(70,25)
plt.show()