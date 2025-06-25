# -*- coding: utf-8 -*-
"""
Created on Tue May 27 15:58:25 2025

@author: bviscogliosi
"""

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
        
import os
print(os.getuid() if hasattr(os, 'getuid') else os.system("whoami"))     #added to see if running as admin




lv.connect()
serv_connect = lv.isConnected
print('serv_connect: ', serv_connect)




#move_stage_pos(stage_sel,position in ps)
#stage_sel: 0(tau), 1 (T), 2 (t)
lv.LV_Control.move_stage_pos(2,8)


print(lv.LV_Control.check_stage_move())


phase_AB, phase_CD = lv.LV_Control.acquire_phase()
print('phase_AB,phase_CD: ', phase_AB, phase_CD)



#Loop for 1D discrete scan (starts at t=0ps)
def OneD_scan(resolution, scan_length):  #resolution: points/picosecond, scan_length: length of t-axis in picosecond
    phase_AB_table = []
    phase_CD_table = []
    for i in range(resolution*scan_length): #can add a +1 if want to include the last extremity of the time interval
        print(i)
        lv.LV_Control.move_stage_pos(2,i/resolution)
        #print(lv.LV_Control.check_stage_move())
        phase_AB, phase_CD = lv.LV_Control.acquire_phase()
        phase_AB_table.append(phase_AB)
        phase_CD_table.append(phase_CD)
    print('phase_AB_table,phase_CD_table: ', phase_AB_table, phase_CD_table)

    #ONLY PHASE ACQUISITION IS THERE FOR THE MOMENT (TO KNOW STAGES' POSITIONS)
    #WILL ADD THE REST OF THE SCAN INSTRUCTIONS TOMORROW (get detected spectrum for each "i" and FT S(t1) of each nu along "i-axis" to get back emission for every nu)   nu=detection frequency


OneD_scan(10,2)
