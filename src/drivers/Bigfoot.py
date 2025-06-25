# -*- coding: utf-8 -*-
"""
Created on Thu Tue  10 14:03:53 2025

@author: Beatrice Viscogliosi
Hardware class to control the Bigfoot MDCS spectrometer. All hardware classes require a definition of
parameter_dict (set write and read parameter)
parameter_display_dict (set Spinbox options)
set_parameter function (assign set functions)

This driver can:
manage scan commands
give feedback if motors are idle or not

"""

import requests
import numpy as np
import json
from PyQt5 import QtCore
import time
from collections import defaultdict
import time
from jki_python_bridge_for_labview import labview as lv


class Bigfoot(QtCore.QThread):

    name = 'Bigfoot'
    
    def __init__(self):
        super(Bigfoot, self).__init__()

        # parameters

        # set parameter dict
        self.parameter_dict = defaultdict()
        
        # setting up variables, open array
        self.stop = False
        self.parameter_display_dict = defaultdict(dict)
        self.parameter_display_dict['bf_idle']['val'] = 0
        self.parameter_display_dict['bf_idle']['unit'] = ' per'
        self.parameter_display_dict['bf_idle']['max'] = 100
        self.parameter_display_dict['bf_idle']['read'] = True

        # set up parameter dict that only contains value. (faster to access)
        self.parameter_dict = {}
        for key in self.parameter_display_dict.keys():
            self.parameter_dict[key] = self.parameter_display_dict[key]['val']

        # connect to Labview interface
        lv.connect()
        serv_connect = lv.isConnected
        print(serv_connect)

    def set_parameter(self,parameter,value):
            pass
              
    def run_scan(self,t_delay):
        # change_scan(type, t_length, step_length, fixed_delay)
        # type: 1Q (Single Quantum), 0Q (Zero Quantum), 2Q (Double Quantum), 1Q-NR (Rephasing), 1Q-NR (Non-rephasing)
        # t_length: t-axis Scan Length in ps
        # step_length: 2D-axis Scan Length in ps
        # fixed_delay: Fixed Delay (pulse width) in ps
        #lv.LV_Control.change_scan('1Q-R', t_delay, 0, 1)
        lv.LV_Control.run_scan()
        # to be filled

    def check_stage(self):
        stage_status  = lv.LV_Control.check_stage_move()
        # Returns array of stage movement true (1)/false (0) in the following order: tau/T/t
        if stage_status == [0, 0, 0]:
            self.parameter_dict['bf_idle'] = 100
        else:
            self.parameter_dict['bf_idle'] = 0

