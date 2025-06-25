# -*- coding: utf-8 -*-
"""
Created on Tue May 27 15:58:25 2025

@author: bviscogliosi
"""

import sys
print(sys.prefix)

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



#Loop to discretely scan 0-1ps with 10 points
for i in range(11):
    print(i)
    lv.LV_Control.move_stage_pos(2, (i/10))
    print(lv.LV_Control.check_stage_move())
    phase_AB, phase_CD = lv.LV_Control.acquire_phase()
    print('phase_AB,phase_CD: ', phase_AB, phase_CD)



