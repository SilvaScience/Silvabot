import numpy as np
import matplotlib.pyplot as plt
import matplotlib
import h5py
import os
from scipy.fft import fft, fftshift, ifftshift, fftfreq, ifft, fft2, ifft2
#from src.measurements.MeasurementClasses import TwoDMeasurement
from jki_python_bridge_for_labview import labview as lv
from matplotlib.patches import Rectangle
import matplotlib.ticker as ticker
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
from scipy.signal import savgol_filter


def find_idx(array,value):
    return np.argmin(abs(array-value))

h = 4.135E-15 #eV/Hz
h_c = 1239.841984 #h * c in eV/nm
#lv.connect()
# %%
# input 
date = '2025-10-01' # '2025-07-24' # 
data_name =  'GaAs_QW_2501_14_48_44' # 'GaAs_QW_2501_16_08_00' #
bg_name =  'avg_data15_25_36' # 'avg_data17_11_58' # # load background  ;  CHANGE THIS IF TAU CHANGES THE 
path = r"D:\DATA\BIGFOOT"
title_id = os.path.join(date,data_name)


with h5py.File(os.path.join(path,date,bg_name + '.h5'), 'r') as f:
    bg_rawI_row = np.flip(np.sum(f['averaged_rawI'][264:268,:],axis =0))
    bg_rawQ_row = np.flip(np.sum(f['averaged_rawQ'][264:268,:],axis =0))
    image_I_bg =  f['averaged_rawI'][:]
    
#bg_rawI_row = bg_rawI_row-np.average(bg_rawI_row,axis=0)
#bg_rawQ_row = bg_rawQ_row-np.average(bg_rawQ_row,axis=0)
amp_row_bg = np.sqrt(bg_rawI_row ** 2 + bg_rawQ_row ** 2)
amp_row_bg = abs(amp_row_bg - np.average(amp_row_bg,axis=0))

# create 2d map for fft (horizontal = amplitude with bg suppression, vertical = tau axis)
folder = os.path.join(path,date,data_name)
file_list = sorted(os.listdir(folder))

#plt.pcolor(image_I_bg)
#plt.ylim(260,270)
#plt.plot(image_I_bg[264])
plt.plot(amp_row_bg)
plt.show()

step = 0.1 # 0.02 # lv.LV_Control.read_scan_params()[1]  #SINCE THIS RETURNS NUMBERS WITH ++DECIMALS, I'M NOT SURE IT'S THE EXACT TAU POSITIONS THAT WILL BE SENT TO THE STAGE... SEE HOW PRECISE WE CAN ASK BF STAGE TO BE
tau_values = np.arange(0, len(file_list)*step, step)   #should import tau_max_value instead of writing '2.0'... how?
print(tau_values.shape)
print(len(file_list))

# %% load data
amp_map = np.zeros((len(file_list), bg_rawI_row.shape[0]))   #should be len(tau_values... but sometimes len(file_list) is different :(
averaged_amp = np.zeros((len(file_list), bg_rawI_row.shape[0]))   #should be len(tau_values... but sometimes len(file_list) is different :(
averaged_phase = np.zeros((len(file_list), bg_rawI_row.shape[0]))   #should be len(tau_values... but sometimes len(file_list) is different :(

print(amp_map.shape)
amp_map_3D = np.zeros((np.shape(amp_map)[0],500,np.shape(amp_map)[1]))

for i, filename in enumerate(file_list):
    filepath = os.path.join(folder, filename)

    with h5py.File(filepath, 'r') as f:
        rawI_row = np.sum(f['rawI'][:, 264:268, :],axis =1)  # shape: (n_avg, x)
        rawQ_row = np.sum(f['rawQ'][:, 264:268, :],axis =1) 
        wl = f['rawI'].attrs['xaxis']

    # external bg 
    #amp_row = np.sqrt((rawI_row-bg_rawI_row) ** 2 + (rawQ_row-bg_rawQ_row) ** 2)

    # self-averaged    
    #averaged_amp[i] =  np.sqrt((np.average(rawI_row,axis=0)-bg_I) ** 2 + (np.average(rawQ_row,axis=0)-bg_Q) ** 2)
    #print(np.sqrt((np.average(rawI_row,axis=0)-bg_I) ** 2 + (np.average(rawQ_row,axis=0)-bg_Q) ** 2))
    #averaged_phase[i] = np.arctan2(np.average(rawI_row,axis=0),np.average(rawQ_row,axis=0))
    rawI_row = rawI_row-np.average(rawI_row,axis=0)
    rawQ_row = rawQ_row-np.average(rawQ_row,axis=0)
    amp_row = np.sqrt(rawI_row ** 2 + rawQ_row ** 2)
    
    #amp_row = abs(amp_row - np.average(amp_row,axis=0))
    #amp_row = amp_row[np.max(amp_row,axis=1)>100]
    mean_amp_row = np.mean(amp_row, axis=0) #np.average(amp_row,axis=0)
    print(f'Progress loading: {i+1}/{len(file_list)}')
    print(np.shape(amp_row)[0])
    #amp_map_3D[i] = amp_row
    amp_map[i, :] = np.average(amp_row,axis=0) #amp_row #mean_amp_row

amp_map = np.fliplr(amp_map)
raw_amp_map = amp_map
# %% plot raw files
approx_x_axis = np.flip(1240/wl*1E3)
bg_correct = False
if bg_correct:
    plt.pcolor(approx_x_axis,tau_values,amp_map/np.mean(amp_map,axis =0))
    plt.title(f'Raw data -mean(raw data) \n {title_id}') 
else:
    plt.pcolor(approx_x_axis,tau_values,amp_map)
    plt.title(f'Raw data \n {title_id}')  
plt.xlim(1545,1565)
plt.clim(12,15)
#plt.clim(0.98,1.02)
plt.xlabel('Energy (meV)')
plt.ylabel('Time (ps)')
formatter = ticker.FormatStrFormatter('%.0f')
plt.gca().xaxis.set_major_formatter(formatter)
plt.gca().yaxis.set_major_formatter(formatter)
  
plt.colorbar()

plt.show()
#amp_map_bg_correct = amp_map-np.mean(amp_map,axis =0) # correct by tau mean
amp_map_bg_correct = amp_map-amp_map[40] # correct by last tau value
#amp_map = amp_map_bg_correct

plot_average = False
if plot_average:
    plt.plot(approx_x_axis,np.average(averaged_amp,axis=0))
    plt.xlabel('Energy (meV)')
    plt.ylabel('Intensity')
    plt.title(f'Averaged raw data \n {title_id}')
    plt.xlim(1530,1580)
    plt.plot()
    
plot_average_evolution = False
if plot_average_evolution:
    average =np.average(amp_map[:,find_idx(approx_x_axis,1545):find_idx(approx_x_axis,1565)],axis=1)
    plt.plot(tau_values,average/np.mean(average))
    plt.xlabel('tau (ps)')
    plt.ylabel('Intensity')
    plt.title(f'Averaged raw data \n {title_id}')
    plt.ylim(0.95,1)
    #plt.xlim(1530,1580)
    plt.plot()
# %% FT filter amp data
N_period = 100
freq = 29780
fps = freq/N_period
time_axis = np.linspace(0,np.shape(amp_row)[0],np.shape(amp_row)[0])/fps*1E3
Fs = 1 / (time_axis[1] - time_axis[0])   # Sampling frequency
N = np.shape(amp_row)[0]   

# prepare freq axis and filtering  
freqs = np.fft.fftfreq(N, d=1/Fs)
freqs_crop= -freqs[len(freqs)//2:]
# filter FT spectrum
crit_min = find_idx(freqs_crop,0.001) #0.006  #0.06 #0.18
crit_max = find_idx(freqs_crop,0.035) #0.015 #0.075 #0.195

filtered_amp_map =np.zeros(np.shape(amp_map_3D))
filtered_amp_real = np.zeros(np.shape(amp_map))
filtered_amp_imag = np.zeros(np.shape(amp_map))
filtered_amp_abs = np.zeros(np.shape(amp_map))
for i,amp_row in enumerate(amp_map_3D):
    amp_ft = np.fft.fft(amp_row,axis=0)
    # keep only half of FT spectrum 
    amp_ft = amp_ft[len(freqs)//2:]
    amp_ft2 = amp_ft
    filtered_amp_ft = amp_ft
    filtered_amp_ft[:crit_max]= 0 
    filtered_amp_ft[crit_min:]= 0 
    filtered_amp_map[i] = np.fft.ifft(np.pad(filtered_amp_ft,((len(freqs_crop),0),(0,0)),mode='constant'),axis=0)
    filtered_amp_real[i] = np.average((np.real(filtered_amp_map[i])),axis =0)
    filtered_amp_imag[i] = np.average((np.imag(filtered_amp_map[i])),axis =0)
    filtered_amp_abs[i] = np.average((np.abs(filtered_amp_map[i])),axis =0)

# plot FT filtered data 
pc = {}
f, plts = plt.subplots(3, figsize =(4,6))
pc[0] = plts[0].pcolor(approx_x_axis,tau_values,filtered_amp_real)
pc[1] = plts[1].pcolor(approx_x_axis,tau_values,filtered_amp_imag)
pc[2] = plts[2].pcolor(approx_x_axis,tau_values,filtered_amp_abs)
#pc[1].set_clim(-0.0001,0.0001)
plts[2].set_xlabel('Energy (meV)')
plts[0].set_ylabel('Real (iFT(FT)) \n Time (ms)')
plts[1].set_ylabel('Imag (iFT(FT)) \n Time (ms)')
plts[2].set_ylabel('Abs(iFT(FT)) \n Time (ms)')
plts[0].set_title(f'Filtered raw data \n {title_id}')
for i in range(3): 
    plts[i].set_xlim(1530,1570)
    f.colorbar(pc[i], pad =0.01, shrink=0.9)
for i in range(2): plts[i].set_xticks([])
f.subplots_adjust(wspace =0,hspace =0)
plt.show()

# %%
f = plt.figure()
plt.gca().set_prop_cycle(plt.cycler('color', plt.cm.Blues(np.linspace(0.4, 1, len(tau_values))))) 
for i in range(len(tau_values)):
    #plt.plot(approx_x_axis,filtered_amp_abs[i]+5*i)
    plt.plot(approx_x_axis,averaged_amp[i]+25*i-np.mean(averaged_amp,axis =0)) # -np.mean(averaged_amp,axis =0)
plt.xlim(1530,1570)
#plt.ylim(2200,2900)
plt.title(f'Abs(iFT(FT)) for different tau \n {title_id}')
plt.xlabel('Energy (meV)')
plt.show()

# %% FT data as done for BF data 

amp_map = filtered_amp_abs
amp_map = averaged_amp -np.mean(averaged_amp,axis =0)
amp_map = raw_amp_map
amp_map = amp_map_bg_correct

padded_amp_map = np.pad(amp_map,((0,np.shape(amp_map)[0]),(0,0)))
num_padded_steps = np.shape(padded_amp_map)[0]

# Revisit frequency axis 
ps_to_meV = 4.1356677 # E = h*f, h=4.135E-15eV*s 
freq_shift = 1240/0.796 # 0.796 

freq_axis = np.fft.fftfreq(num_padded_steps,(tau_values[1]-tau_values[0]))
shifted_freq_axis = np.fft.fftshift(freq_axis)*ps_to_meV - freq_shift
cal_tau_freq_axis = shifted_freq_axis
step_freq_axis = shifted_freq_axis[1] -shifted_freq_axis[0]
print(f'Energy resolution is {step_freq_axis}meV')
# %


freq_freq = fft(padded_amp_map, axis=0)
plot_ind = True 
if plot_ind:
    
    # pcolot plot 
    #plt.pcolor(approx_x_axis, cal_tau_freq_axis,np.abs(freq_freq))
    #plt.clim(0,4)
    #plt.colorbar()

    
    #contour plot (needs to be optimized)
    maxval = 4    
    minval = 0.1   
    levels = np.linspace(minval, maxval, 60)
    norm = matplotlib.colors.Normalize(vmin=minval, vmax=maxval)
    plt.contourf(approx_x_axis, cal_tau_freq_axis,np.abs(freq_freq),levels=levels, norm = norm)
    plt.colorbar()
    
    # diagonal 
    plt.plot([1565,1545],[-1565,-1545], c = 'grey')
    
    plt.xlim(1545,1565)
    plt.ylim(-1565,-1545)
    plt.title(f'FT Data \n {title_id}')  
    plt.xlabel('Emission Energy (meV)')
    plt.ylabel('Absorption Energy (meV)')
    formatter = ticker.FormatStrFormatter('%.0f')
    plt.gca().xaxis.set_major_formatter(formatter)
    plt.gca().yaxis.set_major_formatter(formatter)
  
plot_comb = False 
if plot_comb:
    pc = {}
    f, plts = plt.subplots(3, figsize =(4,6))
    pc[0] = plts[0].pcolor(approx_x_axis,cal_tau_freq_axis,np.real(freq_freq))
    pc[1] = plts[1].pcolor(approx_x_axis,cal_tau_freq_axis,np.imag(freq_freq))
    pc[2] = plts[2].pcolor(approx_x_axis,cal_tau_freq_axis,np.abs(freq_freq))
    plts[2].set_xlabel('Energy (meV)')
    plts[0].set_ylabel('Real (iFT(FT)) \n Time (ms)')
    plts[1].set_ylabel('Imag (iFT(FT)) \n Time (ms)')
    plts[2].set_ylabel('Abs(iFT(FT)) \n Time (ms)')
    plts[0].set_title(f'FT Data  \n {title_id}')
    #pc[2].set_clim(0,20)
    for i in range(3): 
        plts[i].set_xlim(1542,1562)
        plts[i].set_ylim(-1590,-1540)
        #pc[i].set_clim()
        f.colorbar(pc[i], pad =0.01, shrink=0.9)
    for i in range(2): plts[i].set_xticks([])
    f.subplots_adjust(wspace =0,hspace =0)
    plt.show()


# %% plot individual spectrum
N_period = 100
freq = 25000
fps = freq/N_period
plot_external = True
if plot_external:
    data_name = 'GaAs_QW_2501_14_13_52'
    title_id = os.path.join(date,data_name)
    filepath = os.path.join(path,date,data_name + '.h5')
else:
    file_idx = 21               
    filename = file_list[file_idx]
    filepath = os.path.join(folder, filename)
    title_id = os.path.join(date,data_name)
time_axis = np.linspace(0,np.shape(amp_row)[0],np.shape(amp_row)[0])/750.267*1E3 # in ms 750.267 is fps for N_period=40, freq=29.780kHz 
time_axis = np.linspace(0,np.shape(amp_row)[0],np.shape(amp_row)[0])/302.346*1E3 # in ms 302.346 is fps for N_period=100, freq=29.780kHz
time_axis = np.linspace(0,np.shape(amp_row)[0],np.shape(amp_row)[0])/fps*1E3
#data_name = 'GaAs_QW_2501_19_39_48'
#filepath = os.path.join(path,date,data_name + '.h5')
with h5py.File(filepath, 'r') as f:
    rawI_row = np.flip(np.sum(f['rawI'][:, 264:268, :],axis =1))  # shape: (n_avg, x)
    rawQ_row = np.flip(np.sum(f['rawQ'][:, 264:268, :],axis =1)) 
    #amp_row = np.sqrt((rawI_row-bg_rawI_row) ** 2 + (rawQ_row-bg_rawQ_row) ** 2)
    raw_image = f['rawQ'][5,:,:]
    #plt.imshow(raw_image)
    
    rawI_row = rawI_row-np.average(rawI_row,axis=0) # average over all frames. 
    rawQ_row = rawQ_row-np.average(rawQ_row,axis=0)
    amp_row = np.sqrt(rawI_row ** 2 + rawQ_row ** 2)
    phase_row = np.arctan2(rawQ_row,rawI_row)
    #amp_row = amp_row[np.max(amp_row,axis=1)>100]
    mean_amp_row = np.mean(amp_row, axis=0)

f, plts = plt.subplots(3, figsize =(4,8),gridspec_kw={'height_ratios': [1, 1.1,2]})
plts[0].plot(approx_x_axis,np.average(amp_row,axis=0))
#plts[0].plot(approx_x_axis,np.average(amp_row/np.cos(phase_row),axis=0))
#plts[0].set_ylim(0,800)
pc = plts[1].pcolor(approx_x_axis,time_axis,amp_row)
#pc = plts[1].pcolor(approx_x_axis,np.linspace(1,np.shape(amp_row)[0],np.shape(amp_row)[0]),np.cos(phase_row))
#pc.set_clim(14,18)
pc.set_clim(14,600)
clean_phase = np.zeros(np.shape(phase_row))
for i in range(np.shape(phase_row)[1]): 
    window = 2
    clean_phase[:,i] = np.convolve(phase_row[:,i], np.ones(window)/window, mode='same')
    #clean_phase[:,i] = savgol_filter(phase_row[:,i],3,1)
pc = plts[2].pcolor(approx_x_axis,time_axis,np.cos(clean_phase))
pc.set_clim(-1,1)
plts[2].set_xlabel('Energy (meV)')
plts[1].set_ylabel('$(Q^2+I^2)^{(1/2)}$ \n Time (ms)')
plts[2].set_ylabel('$arctan2(Q,I)$ \n Time (ms)')
#plts[1].set_ylim(0,700)
#plts[2].set_ylim(0,700)
plts[0].set_ylabel('Intensity')
plts[0].set_xticks([])
plts[1].set_xticks([])
plts[0].set_title(f'Individual T_step {tau_values[file_idx]}ps \n {title_id}')

f.colorbar(pc, orientation='horizontal', pad =0.2, shrink=0.9)
for i in range(3): plts[i].set_xlim(1540,1570)  

f.subplots_adjust(wspace =0,hspace =0)
plt.show()
# % plot time evolution  
plot_evolution = False 
if plot_evolution:
    f, plts = plt.subplots(4, figsize =(4,6))
    #plt.plot(np.average(amp_row[:,218:279],1))
    plts[0].plot(time_axis,np.average(rawI_row[:,235:237],1),label ='rawI')
    plts[1].plot(time_axis,np.average(rawQ_row[:,235:237],1),label ='rawQ')
    plts[2].plot(time_axis,np.average(amp_row[:,235:237],1),label ='$(Q^2+I^2)^{(1/2)}$')
    plts[3].plot(time_axis,np.average(clean_phase[:,235:237],1),label ='$arctan2(Q,I)$')
    #plt.plot(time_axis,np.average(amp_row[:,230:240]/phase_row[:,230:240],1)+30,label ='$(Q^2+I^2)^{(1/2)}$')
    plts[0].set_xlabel('Time (ms)')
    for i in range(4): 
        plts[i].legend()
        plts[i].set_ylabel('Avg. Int.')
    #plt.xlabel('Frame number')
    #plt.ylabel('Averaged intensity pixel row')
    plts[0].set_title(f'Individual T_step {tau_values[file_idx]}ps \n {title_id}')
    
    f.subplots_adjust(wspace =0,hspace =0)
    plt.show()
    
# %% Plot FFT 


amp_ft = np.fft.fft(amp_row,axis=0)
 
Fs = 1 / (time_axis[1] - time_axis[0])   # Sampling frequency
N = np.shape(amp_row)[0]   
 
freqs = np.fft.fftfreq(N, d=1/Fs)
plt.pcolor(approx_x_axis,freqs,np.abs(amp_ft))
plt.xlim(1542,1562)
plt.ylim(-0.04,0.04)
plt.clim(0,5000)
plt.colorbar()
plt.show()
freqs_raw = freqs
amp_ft_raw = amp_ft
# keep only half of FT spectrum 
amp_ft = amp_ft[len(freqs)//2-5:]
amp_ft2 = amp_ft
freqs= -freqs[len(freqs)//2-5:]
# filter FT spectrum
crit_min = find_idx(freqs,0.020) #0.006  #0.06 #0.18
crit_max = find_idx(freqs,0.022) #0.015 #0.075 #0.195
filtered_amp_ft = amp_ft
filtered_amp_ft[:crit_max]= 0 
filtered_amp_ft[crit_min:]= 0 
filtered_amp = np.fft.ifft(np.pad(filtered_amp_ft,((len(freqs)-5,0),(0,0)),mode='constant'),axis=0)

amp_ft = np.fft.fft(amp_row,axis=0)
amp_ft = amp_ft[len(freqs)-10:]

# plot ind FT 
plt.pcolor(approx_x_axis,freqs,np.abs(amp_ft))
plt.title(f'FT data at t=0ps Nperiod=100 \n {title_id}')
plt.ylabel('FT(Raw) \n 1/Time (1/ms)')
plt.xlabel('Energy (meV)')
plt.clim(00,8000)
plt.colorbar()
plt.xlim(1535,1560)
plt.ylim(-0.10,0.01)
plt.show()

# plot 
plot_all = False
if plot_all:
    pc = {}
    f, plts = plt.subplots(4, figsize =(4,6))
    pc[0] = plts[0].pcolor(approx_x_axis,time_axis,np.abs(amp_row))
    pc[1] = plts[1].pcolor(approx_x_axis,freqs,np.abs(amp_ft))
    pc[2] = plts[2].pcolor(approx_x_axis,freqs,np.abs(filtered_amp_ft))
    pc[3] = plts[3].pcolor(approx_x_axis,time_axis,np.abs(filtered_amp))
    plts[1].set_ylim(0,0.15)
    plts[2].set_ylim(0,0.15)
    for i in range(4): 
        plts[i].set_xlim(1530,1570)
        f.colorbar(pc[i], pad =0.01, shrink=0.9)
    for i in range(3): plts[i].set_xticks([])
    pc[1].set_clim(0,10000)
    pc[2].set_clim(0,10000)
    plts[3].set_xlabel('Energy (meV)')
    plts[0].set_ylabel('Raw \n Time (ms)')
    plts[1].set_ylabel('FT(Raw) \n 1/Time (1/ms)')
    plts[2].set_ylabel('filtered FT \n 1/Time (1/ms)')
    plts[3].set_ylabel('iFT(FT) \n Time (ms)')
    plts[0].set_title(f'Raw data at tau={tau_values[file_idx]}ps \n {title_id}')
    f.subplots_adjust(wspace =0,hspace =0)
    #plt.colorbar()
    plt.show()

# %% Plot iFT(FT)
pc = {}
f, plts = plt.subplots(3, figsize =(4,6))
pc[0] = plts[0].pcolor(approx_x_axis,time_axis,np.real(filtered_amp))
pc[1] = plts[1].pcolor(approx_x_axis,time_axis,np.imag(filtered_amp))
#pc[2] = plts[2].pcolor(approx_x_axis,time_axis,np.abs(filtered_amp))
pc[2] = plts[2].pcolor(approx_x_axis,time_axis,np.sqrt(np.real(filtered_amp)**2+np.imag(filtered_amp)**2))
plts[2].set_xlabel('Energy (meV)')
plts[0].set_ylabel('Real (iFT(FT)) \n Time (ms)')
plts[1].set_ylabel('Imag (iFT(FT)) \n Time (ms)')
plts[2].set_ylabel('Abs(iFT(FT)) \n Time (ms)')
plts[0].set_title(f'Raw data at tau={tau_values[file_idx]}ps \n {title_id}')
for i in range(3): 
    plts[i].set_xlim(1530,1570)
    f.colorbar(pc[i], pad =0.01, shrink=0.9)
for i in range(2): plts[i].set_xticks([])
f.subplots_adjust(wspace =0,hspace =0)
plt.show()

# %%
plt.pcolor(approx_x_axis,time_axis,np.real(filtered_amp))
#plt.ylim(0,0.3)
plt.xlim(1530,1570)
#plt.clim(0,100)
plt.xlabel('Energy (meV)')
plt.ylabel('1/Time (1/ms)')
plt.colorbar()
plt.show()

# %%
plt.plot(approx_x_axis,np.average(np.abs(filtered_amp),axis=0))
#plt.plot(approx_x_axis,np.average(np.sqrt(np.real(filtered_amp)**2+np.imag(filtered_amp)**2),axis=0))
#plt.ylim(0,0.3)
plt.xlim(1530,1570)
#plt.clim(0,100)
plt.xlabel('Energy (meV)')
plt.ylabel('Intensity')
plt.title(f'Raw data at tau={tau_values[file_idx]}ps \n {title_id}')
plt.show()

# %% plot individual spectrum of chopped Krypton lamp
approx_x_axis = np.linspace(1450,1650,np.shape(amp_map)[1])
file_idx = 3
data_name = 'Krypton_lamp_6000Hz_17_30_23'
title_id = os.path.join(date,data_name)
filepath = os.path.join(path,date,data_name + '.h5')
time_axis = np.linspace(0,np.shape(amp_row)[0],np.shape(amp_row)[0])/750.267*1E3 # in ms 750.267 is fps for N_period=40, freq=29.780kHz 
time_axis = np.linspace(0,np.shape(amp_row)[0],np.shape(amp_row)[0])/302.346*1E3 # in ms 302.346 is fps for N_period=100, freq=29.780kHz
N_period = 100
freq = 5000
fps = freq/N_period
time_axis = np.linspace(0,np.shape(amp_row)[0],np.shape(amp_row)[0])/fps*1E3
#data_name = 'GaAs_QW_2501_19_39_48'
#title_id = os.path.join(date,data_name)
#filepath = os.path.join(path,date,data_name + '.h5')
with h5py.File(filepath, 'r') as f:
    rawI_row = np.flip(np.sum(f['rawI'][:, 10:150, :],axis =1))  # shape: (n_avg, x) # 260:268
    rawQ_row = np.flip(np.sum(f['rawQ'][:, 10:150, :],axis =1))  # 260:268
    #amp_row = np.sqrt((rawI_row-bg_rawI_row) ** 2 + (rawQ_row-bg_rawQ_row) ** 2)
    rawI_imag = f['rawI'][:,:,:]
    
    rawI_row = rawI_row-np.average(rawI_row,axis=0) # average over all frames. 
    rawQ_row = rawQ_row-np.average(rawQ_row,axis=0)
    amp_row = np.sqrt(rawI_row ** 2 + rawQ_row ** 2)
    phase_row = np.arctan2(rawQ_row,rawI_row)
    #amp_row = amp_row[np.max(amp_row,axis=1)>100]
    mean_amp_row = np.mean(amp_row, axis=0)

f, plts = plt.subplots(3, figsize =(4,8),gridspec_kw={'height_ratios': [1, 1.1,2]})
plts[0].plot(approx_x_axis,np.average(amp_row,axis=0))
#plts[0].plot(approx_x_axis,np.average(amp_row/np.cos(phase_row),axis=0))
plts[0].set_ylim(0,9000)
pc = plts[1].pcolor(approx_x_axis,time_axis,amp_row)
#pc = plts[1].pcolor(approx_x_axis,np.linspace(1,np.shape(amp_row)[0],np.shape(amp_row)[0]),np.cos(phase_row))
#pc.set_clim(14,18)
pc.set_clim(14,9000)
clean_phase = np.zeros(np.shape(phase_row))
for i in range(np.shape(phase_row)[1]): 
    window = 2
    clean_phase[:,i] = np.convolve(phase_row[:,i], np.ones(window)/window, mode='same')
    #clean_phase[:,i] = savgol_filter(phase_row[:,i],3,1)
pc = plts[2].pcolor(approx_x_axis,time_axis,np.cos(clean_phase))
pc.set_clim(-1,1)
plts[2].set_xlabel('Energy (meV)')
plts[1].set_ylabel('$(Q^2+I^2)^{(1/2)}$ \n Time (ms)')
plts[2].set_ylabel('$arctan2(Q,I)$ \n Time (ms)')
#plts[1].set_ylim(0,700)
#plts[2].set_ylim(0,700)
plts[0].set_ylabel('Intensity')
plts[0].set_xticks([])
plts[1].set_xticks([])
plts[0].set_title(f'Raw data Nperiod=100 \n {title_id}')

f.colorbar(pc, orientation='horizontal', pad =0.2, shrink=0.9)
#for i in range(3): plts[i].set_xlim(1530,1570)  

f.subplots_adjust(wspace =0,hspace =0)
plt.show()
# % plot time evolution  
plot_evolution = True 
if plot_evolution:
    f, plts = plt.subplots(4, figsize =(4,6))
    #plt.plot(np.average(amp_row[:,218:279],1))
    plts[0].plot(time_axis,np.average(rawI_row[:,10:150],1),label ='rawI')
    plts[1].plot(time_axis,np.average(rawQ_row[:,10:150],1),label ='rawQ')
    plts[2].plot(time_axis,np.average(amp_row[:,10:150],1),label ='$(Q^2+I^2)^{(1/2)}$')
    plts[3].plot(time_axis,np.average(clean_phase[:,10:150],1),label ='$arctan2(Q,I)$')
    #plt.plot(time_axis,np.average(amp_row[:,230:240]/phase_row[:,230:240],1)+30,label ='$(Q^2+I^2)^{(1/2)}$')
    plts[0].set_xlabel('Time (ms)')
    for i in range(3):plts[i].set_xticks([])
    for i in range(4): 
        plts[i].legend()
        plts[i].set_ylabel('Avg. Int.')
    #plt.xlabel('Frame number')
    #plt.ylabel('Averaged intensity pixel row')
    plts[0].set_title(f'Raw data Nperiod=100 \n {title_id}')
    
    f.subplots_adjust(wspace =0,hspace =0)
    plt.show()
    
# %% Plot FFT 


amp_ft = np.fft.fft(amp_row,axis=0)
 
Fs = 1 / (time_axis[1] - time_axis[0])   # Sampling frequency
N = np.shape(amp_row)[0]   
 
freqs = np.fft.fftfreq(N, d=1/Fs)

# keep only half of FT spectrum 
amp_ft = amp_ft[len(freqs)//2:]
amp_ft2 = amp_ft
freqs= -freqs[len(freqs)//2:]
# filter FT spectrum
crit_min = find_idx(freqs,0.0038) #0.006  #0.06 #0.18
crit_max = find_idx(freqs,0.0042) #0.015 #0.075 #0.195
filtered_amp_ft = amp_ft
filtered_amp_ft[:crit_max]= 0 
filtered_amp_ft[crit_min:]= 0 
filtered_amp = np.fft.ifft(np.pad(filtered_amp_ft,((len(freqs),0),(0,0)),mode='constant'),axis=0)

amp_ft = np.fft.fft(amp_row,axis=0)
amp_ft = amp_ft[len(freqs):]

# plot ind FT 
plt.pcolor(approx_x_axis,freqs,np.abs(amp_ft))
plt.title(f'FT data Nperiod=100 \n {title_id}')
plt.ylabel('FT(Raw) \n 1/Time (1/ms)')
plt.xlabel('Energy (meV)')
plt.clim(0,8000)
plt.colorbar()
#plt.xlim(1535,1560)
plt.show()

# plot 
plot_all = True
if plot_all:
    pc = {}
    f, plts = plt.subplots(4, figsize =(4,6))
    pc[0] = plts[0].pcolor(approx_x_axis,time_axis,np.abs(amp_row))
    pc[1] = plts[1].pcolor(approx_x_axis,freqs,np.abs(amp_ft))
    pc[2] = plts[2].pcolor(approx_x_axis,freqs,np.abs(filtered_amp_ft))
    pc[3] = plts[3].pcolor(approx_x_axis,time_axis,np.abs(filtered_amp))
    plts[1].set_ylim(0,0.015)
    plts[2].set_ylim(0,0.015)
    for i in range(4): 
        plts[i].set_xlim(1450,1650)
        f.colorbar(pc[i], pad =0.01, shrink=0.9)
    for i in range(3): plts[i].set_xticks([])
    pc[1].set_clim(0,10000)
    pc[2].set_clim(0,10000)
    plts[3].set_xlabel('Energy (meV)')
    plts[0].set_ylabel('Raw \n Time (ms)')
    plts[1].set_ylabel('FT(Raw) \n 1/Time (1/ms)')
    plts[2].set_ylabel('filtered FT \n 1/Time (1/ms)')
    plts[3].set_ylabel('iFT(FT) \n Time (ms)')
    plts[0].set_title(f'Raw data Nperiod=100 \n {title_id}')
    f.subplots_adjust(wspace =0,hspace =0)
    #plt.colorbar()
    plt.show()

# %% Plot iFT(FT)
pc = {}
f, plts = plt.subplots(4, figsize =(4,6))
plts[0].plot(approx_x_axis,np.average(np.abs(filtered_amp),axis =0))
pc[0] = plts[1].pcolor(approx_x_axis,time_axis,np.real(filtered_amp))
pc[1] = plts[2].pcolor(approx_x_axis,time_axis,np.imag(filtered_amp))
#pc[2] = plts[2].pcolor(approx_x_axis,time_axis,np.abs(filtered_amp))
pc[2] = plts[3].pcolor(approx_x_axis,time_axis,np.sqrt(np.real(filtered_amp)**2+np.imag(filtered_amp)**2))
plts[3].set_xlabel('Energy (meV)')
plts[1].set_ylabel('Real (iFT(FT)) \n Time (ms)')
plts[2].set_ylabel('Imag (iFT(FT)) \n Time (ms)')
plts[3].set_ylabel('Abs(iFT(FT)) \n Time (ms)')
plts[0].set_title(f'Raw data at tau={tau_values[file_idx]}ps \n {title_id}')
plts[0].set_xlim(1450,1650)
for i in range(3): 
    plts[i].set_xlim(1450,1650)
    #f.colorbar(pc[i], pad =0.01, shrink=0.9)
for i in range(2): plts[i].set_xticks([])
f.subplots_adjust(wspace =0,hspace =0)
plt.show()


