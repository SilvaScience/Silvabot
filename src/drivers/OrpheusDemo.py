"""
Created on Mon Oct 10 17:43:53 2022

@author: DT
Demo Hardware class to control cryostat. All hardware classes require a definition of
parameter_dict (set write and read parameter)
parameter_display_dict (set Spinbox options)
set_parameter function (assign set functions)

"""

from PyQt5 import QtCore
from collections import defaultdict


class OrpheusDemo(QtCore.QThread):
    name = 'Orpheus'

    def __init__(self):
        super(OrpheusDemo, self).__init__()

        # set parameter dict
        self.parameter_dict = defaultdict()

        # setting up variables, open array
        self.stop = False
        self.parameter_dict['set_wl'] = 10
        self.parameter_dict['current_wl'] = 1
        self.parameter_dict['shutter'] = 0
        self.parameter_display_dict = defaultdict(dict)
        self.parameter_display_dict['shutter']['read'] = False
        self.parameter_display_dict['shutter']['val'] = 0
        self.parameter_display_dict['shutter']['unit'] = ' '
        self.parameter_display_dict['shutter']['max'] = 100
        self.parameter_display_dict['set_wl']['val'] = 5
        self.parameter_display_dict['set_wl']['unit'] = ' nm'
        self.parameter_display_dict['set_wl']['max'] = 2600
        self.parameter_display_dict['set_wl']['read'] = False
        self.parameter_display_dict['current_wl']['val'] = 5
        self.parameter_display_dict['current_wl']['unit'] = ' nm'
        self.parameter_display_dict['current_wl']['max'] = 2600
        self.parameter_display_dict['current_wl']['read'] = True

        # set ignore wavelength separator variable
        self.ignore_user_actions = False

    def set_parameter(self, parameter, value):
        if parameter == 'set_wl':
            self.parameter_dict['current_wl'] = value
        if parameter == "shutter":
            pass
