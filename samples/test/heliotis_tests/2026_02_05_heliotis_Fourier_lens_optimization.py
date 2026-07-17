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
import matplotlib.colors as colors


def find_idx(array,value):
    return np.argmin(abs(array-value))

h = 4.135E-15 #eV/Hz
h_c = 1239.841984 #h * c in eV/nm
#lv.connect()
# %%
# input 
date = '2026-02-05' # '2025-07-24' # 
bg_name =  'avg_data14_55_29' # 1999Hz: avg_data15_55_19, 499Hz: avg_data15_32_59, 1999 Hz+AC: avg_data16_55_37
N_period = 100
freq = 25000
path = r"D:\DATA\BIGFOOT"

# %% plot individual spectrum
def load_n_correct_bg(data_name):
    title_id = os.path.join(date,data_name)
    filepath = os.path.join(path,date,data_name + '.h5')
        
    # load background 
    
    limits = np.r_[190:240]
    with h5py.File(os.path.join(path,date,bg_name + '.h5'), 'r') as f:
        bg_rawI = f['averaged_rawI'][:,:] # 264:268
        bg_rawQ = f['averaged_rawQ'][:,:]
        
    
    with h5py.File(filepath, 'r') as f:
        
        rawI_t = f['rawI'][:, :, :]  # shape: (n_avg, x)
        rawQ_t = f['rawQ'][:, :, :] 
        
        wl = f['rawI'].attrs['xaxis']
        
        rawI = (rawI_t-bg_rawI)*freq/N_period
        rawQ = (rawQ_t-bg_rawQ)*freq/N_period
        #rawI = (rawI_t)*freq/N_period
        #rawQ = (rawQ_t)*freq/N_period
        mean_I = np.mean(rawI, axis=0)
        mean_Q = np.mean(rawQ, axis=0)
        
        amp = np.sqrt(rawI ** 2 + rawQ ** 2)
        #mean_amp = np.mean(amp, axis=0)
        mean_amp = np.sqrt(mean_I ** 2 + mean_Q ** 2)
        
    energy_axis = 1240/wl*1E3
    
    return energy_axis,mean_amp,rawI,rawQ,amp

# %% stich several maps
filenames=['raw_data16_06_46', 'raw_data16_06_52', 'raw_data16_06_57', 'raw_data16_07_03', 'raw_data16_07_09'] # 50 53 57  # 1999Hz : raw_data15_56_53, 499Hz: raw_data15_34_30, 1999 Hz+AC: raw_data16_56_03
maps = {}
rawI = {}
rawQ = {}
amp = {}
energy_axis = {}
wl_axis = {}
for f in filenames:
    energy_axis[f],maps[f],rawI[f],rawQ[f],amp[f] = load_n_correct_bg(f)
    wl_axis[f] = 1240/energy_axis[f]*1E3

# %% Plot vs energy
file = filenames[0]
limits_pixel = np.r_[40:60]
limits_pixel = np.r_[310:340]
limits_energy = np.r_[find_idx(energy_axis[file], 1640):find_idx(energy_axis[file], 1630)]
#limits_energy = np.r_[130:131]
limits_pixel_bg = np.r_[40:60]

pixel = np.r_[1:543]
plot_vs_energy = True
if plot_vs_energy:
    plt.pcolor(pixel,energy_axis[file],np.transpose(maps[file]))
    plt.vlines(x0s,1587,1663,linestyle ='--', color = 'grey')
    #plt.clim(50,140)
    plt.title(f'{date}\n{filenames[0]}'.replace('raw_data',''))
    plt.ylabel('Energy (meV)')
    plt.xlabel('Pixel')
    #plt.xlim(120,480)
    #plt.ylim(100,490)
    plt.colorbar()
    
    # add rectangle
    #plt.figure()
    rect = Rectangle((limits_pixel[0],energy_axis[file][limits_energy[0]]), limits_pixel[-1] - limits_pixel[0], energy_axis[file][limits_energy[0]] - energy_axis[file][limits_energy[-1]],
                     fill=False, edgecolor='red', linewidth=2)
    #plt.gca().add_patch(rect)
    rect = Rectangle((limits_pixel_bg[0],energy_axis[file][limits_energy[0]]), limits_pixel_bg[-1] - limits_pixel_bg[0], energy_axis[file][limits_energy[0]] - energy_axis[file][limits_energy[-1]],
                     fill=False, edgecolor='grey', linewidth=2)
    #plt.gca().add_patch(rect)
    
    plt.show()

# % plot time evolution
fps = freq/N_period
file = filenames[0]
I= rawI[file]
Q= rawQ[file]
a = amp[file]
a_avg= np.average(np.average(maps[file][limits_pixel,:],0)[limits_energy],0)
a_bg_avg= np.average(np.average(maps[file][limits_pixel_bg,:],0)[limits_energy],0)
print(f'a_avg:{a_avg}, a_bg_avg:{a_bg_avg}')
bg_value_I = np.average(np.average(I[:,limits_pixel_bg,:],1)[:,limits_energy],1)
bg_value_Q = np.average(np.average(Q[:,limits_pixel_bg,:],1)[:,limits_energy],1)
time_axis = np.linspace(0,np.shape(I)[0],np.shape(I)[0])/fps*1E3
phase_row = np.arctan2(Q,I)  

# %% Cross section
z = np.zeros(np.shape(maps[file]))
x = energy_axis[file]
for file in filenames:
    z = z + maps[file]


x0s = np.array([120,200,280]) # ,360,440
dx = 5 
colors = plt.cm.viridis(np.linspace(0, 1, len(x0s)))
plt.figure()
plt.gca().set_prop_cycle(color=colors)
for x0 in x0s:
    cross_section = np.mean(z[x0 - dx: x0 + dx,:], axis = 0)
    plt.plot(x, cross_section, label =f'{x0} pixel')
plt.legend()
plt.title(f'{date}' +' d$_{lens}$=3cm' + f'\n{filenames}'.replace('raw_data',''))
plt.xlabel('Energy (meV)')
plt.ylabel('Reflectance (arb. u.)')
plt.show()


# %% Plot evolution of ROIs 
plot_evolution = False  
if plot_evolution :
    f, plts = plt.subplots(4, figsize =(4,6))
    #plt.plot(np.average(amp_row[:,218:279],1))
    int_I =np.average(np.average(I[:,limits_pixel,:],1)[:,limits_energy],1)
    int_Q =np.average(np.average(Q[:,limits_pixel,:],1)[:,limits_energy],1)
    int_I_bg =np.average(np.average(I[:,limits_pixel_bg,:],1)[:,limits_energy],1)
    int_Q_bg =np.average(np.average(Q[:,limits_pixel_bg,:],1)[:,limits_energy],1)
    plts[0].plot(time_axis,int_I-bg_value_I,label ='rawI')
    plts[1].plot(time_axis,int_Q-bg_value_Q,label ='rawQ')
    plts[0].plot(time_axis,int_I,c= 'lightskyblue',label ='_rawI')
    plts[1].plot(time_axis,int_Q,c= 'lightskyblue',label ='_rawQ')
    plts[0].plot(time_axis,int_I_bg,c= 'grey', label ='bg')
    plts[1].plot(time_axis,int_Q_bg,c= 'grey', label ='bg')
    plts[2].plot(time_axis,np.average(np.average(a[:,limits_pixel,:],1)[:,limits_energy],1),label ='$(Q^2+I^2)^{(1/2)}$')
    plts[2].plot(time_axis,np.average(np.average(a[:,limits_pixel_bg,:],1)[:,limits_energy],1),c= 'grey',label ='bg')
    plts[3].plot(time_axis,np.average(np.average(phase_row[:,limits_pixel,:],1)[:,limits_energy],1),label ='$arctan2(Q,I)$')
    #plts[3].plot(time_axis,np.average(clean_phase[:,limits],1),label ='$arctan2(Q,I)$')
    #plt.plot(time_axis,np.average(amp_row[:,230:240]/phase_row[:,230:240],1)+30,label ='$(Q^2+I^2)^{(1/2)}$')
    plts[3].set_xlabel('Time (ms)')
    for i in range(4): 
        plts[i].legend()
        plts[i].set_ylabel('Avg. Int.')
    #plt.ylabel('Averaged intensity pixel row')
    plts[0].set_title(f'{date} {filenames[0]}'.replace('raw_data',''))
    
    f.subplots_adjust(wspace =0,hspace =0)
    plt.show()
    print(f'amp average ={np.average(np.average(np.average(a[:,limits_pixel,:],1)[:,limits_energy],1))}')




