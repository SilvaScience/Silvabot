import numpy as np
import matplotlib.pyplot as plt
import h5py
import os
from scipy.fft import fft, fftshift, ifftshift, fftfreq, ifft, irfft
#from src.measurements.MeasurementClasses import TwoDMeasurement
from jki_python_bridge_for_labview import labview as lv
from matplotlib.patches import Rectangle



h = 4.135E-15 #eV/Hz
h_c = 1239.841984 #h * c in eV/nm
lv.connect()
# %%

# load background  ;  CHANGE THIS IF TAU CHANGES THE BG
folder_bg = r"C:\DATA\BIGFOOT\2025-08-01"
filename_bg = 'avg_data11_49_23'
with h5py.File(folder_bg + "\\" + filename_bg + '.h5', 'r') as f:
    bg_rawI_row = f['averaged_rawI'][263,:]
    bg_rawQ_row = f['averaged_rawQ'][263,:]

# create 2d map for fft (horizontal = amplitude with bg suppression, vertical = tau axis)
folder = r"C:\DATA\BIGFOOT\2025-08-01\GaAs_QW_2501_11_54_49"
file_list = sorted(os.listdir(folder))
step = 0.04 # lv.LV_Control.read_scan_params()[1]  #SINCE THIS RETURNS NUMBERS WITH ++DECIMALS, I'M NOT SURE IT'S THE EXACT TAU POSITIONS THAT WILL BE SENT TO THE STAGE... SEE HOW PRECISE WE CAN ASK BF STAGE TO BE
tau_values = np.arange(0, 2.0 + step, step)   #should import tau_max_value instead of writing '2.0'... how?
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

plt.imshow(np.abs(amp_map), aspect='auto', extent=[1480, 1630, tau_values[-1], tau_values[0]])
plt.title('amp_map')
plt.colorbar()
plt.show()

plt.plot(tau_values[:len(file_list)], np.average(amp_map,axis=1))
plt.show()

t = tau_values*(10**(-12))
f_shift_eV = 1.5492
f_shift_hz = f_shift_eV / h  #go close to features around 1.555eV
amp_map_f_shifted = np.zeros_like(amp_map, dtype=complex)
for column in range(amp_map.shape[1]):
    amp_map_f_shifted[:,column] = amp_map[:,column] * np.exp(-1j * 2 * np.pi * f_shift_hz * t[:len(file_list)])

padded_amp_map = np.pad(amp_map_f_shifted, ((0, amp_map_f_shifted.shape[0]), (0, 0)), mode='constant')

plt.imshow(np.abs(padded_amp_map), aspect='auto', extent=[1480, 1630, 2*tau_values[-1] -tau_values[0], tau_values[0]])
plt.title(f'shifted & padded 2D Map (for fft) generated with pixel_y = 263 \n {folder}')
plt.xlabel('Emission energy (meV)')
plt.ylabel('tau (ps)')
plt.show()

#good_amp_map = np.flipud(padded_amp_map) # flip vertically for tau=0 at the bottom (Should we put this before "for column in...." ?)


# %% SECTION MADE BY CHAT GPT !!!!!!

fft_ = fft(padded_amp_map, axis=0)
fft_shifted = fftshift(fft_, axes=0)
freqs = fftshift(fftfreq(padded_amp_map.shape[0], d=t[1]-t[0]))   #shift the fft and fftfreq to have data from negative -> 0 -> positive
extent = [1480, 1630, freqs[-1], freqs[0]]
plt.imshow(np.abs(fft_shifted), aspect='auto', extent=extent)
plt.title('fft shifted')
plt.colorbar()
#plt.clim(0,160)
plt.show()

# Optional: apply a mask to remove DC / low freq
#mask = freqs > 0  # Keep only positive frequencies (= True or False)
#filtered_fft = fft_shifted * mask[:, None]  # Apply mask column-wise
#plt.imshow(np.abs(filtered_fft), aspect='auto', extent = extent)
#plt.title('filtered fft')
#plt.show()

# Back to time domain
fft_unshifted = ifftshift(fft_shifted, axes=0)
plt.imshow(np.abs(fft_unshifted), aspect='auto')
plt.title('filtered fft unshifted (for ifft)')
plt.ylabel('negative (ascending) <- positive (ascending)')
plt.show()
time_signal = ifft(fft_unshifted, axis=0)
plt.imshow(np.abs(time_signal), aspect='auto')    #appearance changes a lot with chosen freq shift value since the fft is always cut in the middle
plt.title('time signal')
plt.show()

# Crop negative time (if needed)
time_signal = time_signal[:int(time_signal.shape[0]/2), :]  # Remove negative times (after shift)
plt.imshow(np.abs(time_signal), aspect='auto')
plt.title('cropped time signal')
plt.show()

# Go back to frequency domain
final_fft = fft(time_signal, axis=0)
final_fft_shifted = fftshift(final_fft, axes=0)
freqs = fftshift(fftfreq(final_fft_shifted.shape[0], d=t[1]-t[0]))
print(final_fft_shifted.shape)
plt.imshow(np.abs(final_fft_shifted), aspect='auto', extent=[1480, 1630, freqs[-1], freqs[0]])
plt.title('final fft shifted')
plt.colorbar()
#plt.clim(0,200 )
plt.show()
