# -*- coding: utf-8 -*-
"""
Created on Tue May 27 15:58:25 2025

@author: bviscogliosi
"""
import matplotlib.pyplot as plt
import time
import numpy as np

import sys

print('sys.prefix, sys.executable: ', sys.prefix, sys.executable)

from jki_python_bridge_for_labview import labview as lv


unit_map = {
    'nm': 0,
    'meV': 1,
    'THz': 2,
    'cm-1': 3

}

def units(string):
    try:
        return unit_map[string]
    except KeyError:
        raise ValueError(f"Unknown unit: {string}")


######################################################################################
######################################################################################
#TEST SECTION
        
import os
print(os.getuid() if hasattr(os, 'getuid') else os.system("whoami"))     #added to see if running as admin



lv.connect()
serv_connect = lv.isConnected
print('serv_connect: ', serv_connect)


#phase_AB, phase_CD = lv.LV_Control.acquire_phase()
#print('phase_AB,phase_CD (initial): ', phase_AB, phase_CD)


#Function for 1D discrete scan (starts at t=0ps)
#only changes t-stage ; make sure the others are at the right position
def OneD_scan_test(t_resolution, t_length):  #t_resolution: points/picosecond, t_length: length of t-axis in picosecond
    t_position_table = [] #t-stage position in ps
    phase_AB_table = []
    phase_CD_table = []
    t1 = time.time()
    for i in range(int(t_resolution*t_length)+1):
        print(i)
        t_position = i/t_resolution
        #t1 = time.time()
        lv.LV_Control.move_stage_pos(2,t_position)
        #print(lv.LV_Control.check_stage_move())
        print("Stepping time:", time.time()-t1)
        t1 = time.time()
        #time.sleep(0.1)

        phase_AB, phase_CD = lv.LV_Control.acquire_phase()
        phase_AB_table.append(phase_AB)
        phase_CD_table.append(phase_CD)
        t_position_table.append(t_position)

        #instruction to get detection spectrum (amp of each wavelength) at 30kHz for FWM 1D (260kHz for Linear 1D?)
        #need something else ?

#Function for 2D scan
#Moves t and tau stages ; make sure T stage is at the right position before starting the scan
def TwoD_scan_test(t_resolution, t_length, tau_resolution, tau_length):  #tau_resolution = nbr of 1D scan/picosecond,  tau_length = in picosecond
    tau_position_table = []
    for i in range(int(tau_resolution*tau_length)+1):
        print(i)
        tau_position = i/tau_resolution
        lv.LV_Control.move_stage_pos(0,tau_position)
        OneD_scan(t_resolution, t_length)
        #to avoid overwriting the tables, give them names specific to tau_position
        tau_position_table.append(tau_position)

    #FFT each v3 (detection frequency) along the t1 axis (with 1D average spectrum (the one plotted) I guess?)
    #make 2D spectrum...... but need amp. + phase, right?


def TwoD_scan():
    t_position_table = []  # t-stage position in ps
    phase_AB_table = []
    phase_CD_table = []
    scan_axis = np.linspace(0,1,2)
    i = 0
    t1 = time.time()
    for scan_time in scan_axis:
        print(scan_time)
        scan_busy = 1
        lv.LV_Control.change_scan('1Q-R', 0.4, 0.4, 0.1)
        lv.LV_Control.run_scan()
        while scan_busy == 1:
            i = i+1
            t_position = i
            #lv.LV_Control.move_stage_pos(2, t_position)
            # print(lv.LV_Control.check_stage_move())
            print("Stepping time:", time.time() - t1)
            t1 = time.time()
            time.sleep(0.1)

            phase_AB, phase_CD = lv.LV_Control.acquire_phase()
            stage_movement = lv.LV_Control.check_stage_move()
            scan_status = lv.LV_Control.check_scan()
            scan_busy = scan_status[1]
            print(f"Step number : {i} Phase AB: {phase_AB}  Phase CD: {phase_CD} Stage movement: {stage_movement} scan_status: {scan_status}")
            phase_AB_table.append(phase_AB)
            phase_CD_table.append(phase_CD)
            t_position_table.append(t_position)
    #lv.LV_Control.run_scan()
    t1 = time.time()
    for i in range(200):
        t_position = i
        # t1 = time.time()
        # lv.LV_Control.move_stage_pos(2, t_position)
        # print(lv.LV_Control.check_stage_move())
        print("Stepping time:", time.time() - t1)
        t1 = time.time()
        time.sleep(0.1)

        phase_AB, phase_CD = lv.LV_Control.acquire_phase()
        stage_movement = lv.LV_Control.check_stage_move()
        scan_status = lv.LV_Control.check_scan()
        print(
            f"Step number : {i} Phase AB: {phase_AB}  Phase CD: {phase_CD} Stage movement: {stage_movement} scan_status: {scan_status}")
        phase_AB_table.append(phase_AB)
        phase_CD_table.append(phase_CD)
        t_position_table.append(t_position)

    #lv.LV_Control.move_stage_pos(2, 0)

    print('phase_AB_table,phase_CD_table: ', phase_AB_table, phase_CD_table)
    #average the amp. for each wavelength + plot it ? Gives 1D spectrum

    plt.plot(t_position_table, phase_AB_table)
    plt.xlabel('t-stage position (ps)')
    plt.ylabel('AB phase')
    plt.grid()
    plt.show()
    plt.plot(t_position_table, phase_CD_table)
    plt.xlabel('t-stage position (ps)')
    plt.ylabel('CD phase')
    plt.grid()
    plt.show()


TwoD_scan()


#function that keeps the time (hour:min:sec:etc) when the tau stage moved.
def Time_TwoD_scan():
    #...
    scan_busy = lv.LV_Control.check_scan()[1]
    lv.LV_Control.run_scan()
    while scan_busy == 0:
        print('hey')
        #take hour