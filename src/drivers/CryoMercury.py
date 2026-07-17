# -*- coding: utf-8 -*-
"""
Created on Wed Feb  08 13:26:53 2023

@author: David Tiede
Hardware class to control cryostat based on mercuryITC driver (https://github.com/OE-FET/mercuryitc).
All hardware classes require a definition of
parameter_dict (set write and read parameter)
parameter_display_dict (set Spinbox options)
set_parameter function (assign set functions)

"""

import numpy as np
from PyQt5 import QtCore
import time
from collections import defaultdict
from Hardware.mercury_driver import MercuryITC


class CryoMercury(QtCore.QThread):
    name = 'cryostat'

    def __init__(self, address):
        super(CryoMercury, self).__init__()

        # set parameter dict
        self.parameter_dict = defaultdict()

        # setting up variables, open array
        self.set_T = []
        self.current_T = []
        self.stop = False
        self.parameter_dict['set_T'] = 10
        self.parameter_dict['current_T'] = 1
        self.parameter_dict['enable'] = 0
        self.parameter_display_dict = defaultdict(dict)
        self.parameter_display_dict['set_T']['val'] = 5
        self.parameter_display_dict['set_T']['unit'] = ' K'
        self.parameter_display_dict['set_T']['max'] = 1000
        self.parameter_display_dict['set_T']['read'] = False
        self.parameter_display_dict['current_T']['val'] = 5
        self.parameter_display_dict['current_T']['unit'] = ' K'
        self.parameter_display_dict['current_T']['max'] = 1000
        self.parameter_display_dict['current_T']['read'] = True
        self.parameter_display_dict['enable']['val'] = 0
        self.parameter_display_dict['enable']['unit'] = ' per'
        self.parameter_display_dict['enable']['max'] = 100
        self.parameter_display_dict['enable']['read'] = False

        # defining waitTime
        self.waitTime = 0.1

        # connect to Mercury Controller
        self.cryostat = MercuryITC(address)
        self.temp_ctrl = self.cryostat.modules[1]

        # start updating temp
        self.UpdateWorker = UpdateWorker(self.cryostat)
        self.UpdateWorker.new_T.connect(self.update_temp)
        self.UpdateWorker.start()

    def set_parameter(self, parameter, value):
        if parameter == 'set_T':
            self.temp_ctrl.loop_tset = value
        if parameter == 'enable':
            if value == 100:
                self.temp_ctrl.loop_enab = 'ON'
                print(time.strftime('%H:%M:%S') + ' Temperature control enabled')
            else:
                self.temp_ctrl.loop_enab = 'OFF'
                print(time.strftime('%H:%M:%S') + ' Temperature control disabled')

    def update_temp(self, new_T):
        self.parameter_dict['current_T'] = new_T


class UpdateWorker(QtCore.QThread):
    new_T = QtCore.pyqtSignal(float)

    def __init__(self, cryostat):
        super(UpdateWorker, self).__init__()
        self.cryostat = cryostat
        self.temp_ctrl = self.cryostat.modules[1]
        self.currentT = []
        self.stop = False
        self.waitTime = 0.1
        self.target = 300

    def run(self):
        while not self.stop:
            # calling the read temperature function
            self.readtemp = self.temp_ctrl.temp[0]
            self.new_T.emit(self.readtemp)
            # waiting to remeasure the temperature
            time.sleep(self.waitTime)


