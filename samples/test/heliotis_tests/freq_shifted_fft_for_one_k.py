import numpy as np
import matplotlib.pyplot as plt
import h5py
import os
from scipy.fft import fft, fftshift, fftfreq
from src.measurements.MeasurementClasses import TwoDMeasurement
from jki_python_bridge_for_labview import labview as lv
from matplotlib.patches import Rectangle



h = 4.135E-15 #eV/Hz
h_c = 1239.841984 #h * c in eV/nm
lv.connect()
# %%

# load background  ;  CHANGE THIS IF TAU CHANGES THE BG
folder_bg = r"C:\DATA\BIGFOOT\2025-07-29"
filename_bg = 'avg_data17_18_15'
with h5py.File(folder_bg + "\\" + filename_bg + '.h5', 'r') as f:
    bg_rawI_row = f['averaged_rawI'][263,:]
    bg_rawQ_row = f['averaged_rawQ'][263,:]

# create 2d map for fft (horizontal = amplitude with bg suppression, vertical = tau axis)
folder = r"C:\DATA\BIGFOOT\2025-07-29\GaAs_QW_2501_17_20_51"
file_list = sorted(os.listdir(folder))

step = lv.LV_Control.read_scan_params()[1]  #SINCE THIS RETURNS NUMBERS WITH ++DECIMALS, I'M NOT SURE IT'S THE EXACT TAU POSITIONS THAT WILL BE SENT TO THE STAGE... SEE HOW PRECISE WE CAN ASK BF STAGE TO BE
tau_values = np.arange(0.0, 2.0 + step, step)   #should import tau_max_value instead of writing '2.0'... how?
print(tau_values.shape)
print(tau_values)
print(len(file_list))
amp_map = np.zeros((len(file_list), bg_rawI_row.shape[0]))    #should be len(tau_values)

for i, filename in enumerate(file_list):
    filepath = os.path.join(folder, filename)

    with h5py.File(filepath, 'r') as f:
        rawI_row = f['rawI'][:, 263, :]  # shape: (n_avg, x)
        rawQ_row = f['rawQ'][:, 263, :]

        amp_row = np.sqrt((rawI_row- bg_rawI_row) ** 2 + (rawQ_row - bg_rawQ_row) ** 2)
        mean_amp_row = np.mean(amp_row, axis=0)
        amp_map[i, :] = mean_amp_row

t = tau_values*(10**(-12))
f_shift_eV = 1.56
f_shift_hz = f_shift_eV / h  #go close to features around 1.555eV
amp_map_f_shifted = np.zeros_like(amp_map, dtype=complex)
for column in range(amp_map.shape[1]):
    amp_map_f_shifted[:,column] = amp_map[:,column] * np.exp(-1j * 2 * np.pi * f_shift_hz * t[:len(file_list)])

padded_amp_map = np.pad(amp_map_f_shifted, ((0, amp_map_f_shifted.shape[0]), (0, 0)), mode='constant')
good_amp_map = np.flipud(padded_amp_map) # flip vertically for tau=0 at the bottom (Should we put this before "for column in...." ?)


# %%

plt.imshow(amp_map, aspect='auto', extent=[1480, 1630, 0, tau_values[-1]])  #extent = axis values from (left, right, bottom, top)
plt.xlabel('Emission energy (meV)')
plt.ylabel('tau (ps)')
plt.title(f'2D Map generated with pixel_y = 263 \n {folder}')
plt.colorbar(label='Amplitude')
plt.show()
print(amp_map.shape)


plt.imshow(np.abs(good_amp_map), aspect='auto', extent=[1480, 1630, 0, tau_values[-1]*2])
plt.xlabel('Emission energy (meV)')
plt.ylabel('tau (ps)')
plt.title(f'shifted & padded 2D Map (for fft) generated with pixel_y = 263 \n {folder}')
plt.colorbar(label='Amplitude')
plt.show()
print(good_amp_map.shape)


# %%

fft= fft(good_amp_map, axis=0)  #gives complex data
#freqs = fftfreq(t.shape[0], d=t[1]-t[0])
fft_shifted = fftshift(fft, axes=0)  #shifts the zero component to the middle so does negative->0->positive (vertically)
#freqs_shifted = fftshift(freqs)

tau_step_ps = tau_values[1] - tau_values[0]
N_tot = good_amp_map.shape[0]
freq_step_meV = 4.1356677 / (tau_step_ps * N_tot)
print(tau_step_ps, freq_step_meV)
#freq_axis_meV = f_shift_eV * 1e3 + np.arange(-N_tot//2, N_tot//2) * freq_step_meV


# %%

plt.figure(figsize=(10, 6))
extent = [1480, 1630, f_shift_eV*1e3 - (N_tot*freq_step_meV/2), f_shift_eV*1e3 + (N_tot*freq_step_meV/2)]
plt.imshow(np.abs(fft_shifted), aspect='auto', origin='lower', extent=extent, cmap='viridis')
plt.title(f"Spectrum after shifting fft central freq. to ~375THz (1.555eV) and zero padding\n {folder}")
plt.xlabel("Emission energy (meV)")
plt.ylabel("Absorption energy (meV) [f_shift=central energy]")
plt.colorbar()
#plt.clim(0,40)
plt.tight_layout()
plt.show()


plt.figure(figsize=(10, 6))
print(lv.LV_Control.read_scan_params())
extent = [1480, 1630, h_c*1e3/lv.LV_Control.read_scan_params()[0], h_c*1e3/lv.LV_Control.read_scan_params()[0] + (N_tot*freq_step_meV)]
plt.imshow(np.abs(fft_shifted), aspect='auto', origin='lower', extent=extent, cmap='viridis')
plt.title(f"Spectrum after shifting fft central freq. to ~375THz (1.555eV) and zero padding \n {folder}")
plt.xlabel("Emission energy (meV)")
plt.ylabel("Absorption energy (meV) [BF read_scan_params]")
plt.colorbar()
plt.clim(30,150)
plt.gca().add_patch(Rectangle((1545, 1545), 20, 20, edgecolor='red', facecolor='none', linewidth=0.6))
plt.tight_layout()
plt.show()
