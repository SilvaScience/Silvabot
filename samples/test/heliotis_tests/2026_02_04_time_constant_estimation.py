# -*- coding: utf-8 -*-
"""
Created on Wed Feb  4 14:15:14 2026

@author: dtiede
"""

import numpy as np 

#demodulation parameters
demod_freq = np.array([400,1000,5000])
N_period = 10 

# integration time of heliotis
int_time = 1/demod_freq*N_period

# effective cutoff for an analog RC filter. Heliotis uses a rectangular filter. 
# 1-pole lock-in output filter is given by tau = T/2 
# analog RC time constant for 99% suppression is tau = T/5
# use more conservative approximation of analog RC filter. 

tau = int_time/5

# cutoff frequency of a 
f_cut = 1/(2*np.pi*tau)

print(f'N_period = {N_period}')
for i,f in enumerate(demod_freq):
    print(f'demod: {f:.1f} Hz, time constant:{tau[i]*1E3:.1f}ms ,cutoff: {f_cut[i]:.1f} Hz')

