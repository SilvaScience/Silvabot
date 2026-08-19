# -*- coding: utf-8 -*-
"""
Demo fallback for drivers.SpectraPro2300i.SpectraPro2300i.

Used when no SP2300i is connected (wrong/missing COM port). Implements the same interface the
attached cameras rely on (get_monochromator_parameters, set_parameter, parameter_display_dict/
parameter_dict) so Pixis and Stresing behave the same way whether the real monochromator is
present or not.
"""

import numpy as np
from PyQt5 import QtCore
from collections import defaultdict


class SpectraPro2300iDemo(QtCore.QThread):

    name = 'SpectraPro2300iDemo'
    type = 'Monochromator'

    def __init__(self, port=None):
        super(SpectraPro2300iDemo, self).__init__()

        self.center_wl = 800.0
        self.grating = 1
        self.mirror = 0
        self.num_gratings = 3
        self.grating_densities = np.array([1200.0, 600.0, 300.0])
        self.grating_blazes = np.array([500.0, 750.0, 1000.0])

        self.parameter_display_dict = defaultdict(dict)

        self.parameter_display_dict['central_wave']['val'] = self.center_wl
        self.parameter_display_dict['central_wave']['unit'] = ' nm'
        self.parameter_display_dict['central_wave']['min'] = 200.00
        self.parameter_display_dict['central_wave']['max'] = 1100.00
        self.parameter_display_dict['central_wave']['read'] = False

        self.parameter_display_dict['grating']['val'] = self.grating
        self.parameter_display_dict['grating']['unit'] = ' grat'
        self.parameter_display_dict['grating']['min'] = 1
        self.parameter_display_dict['grating']['max'] = self.num_gratings
        self.parameter_display_dict['grating']['read'] = False

        self.parameter_display_dict['mirror']['val'] = self.mirror
        self.parameter_display_dict['mirror']['unit'] = ' mirror'
        self.parameter_display_dict['mirror']['min'] = 0
        self.parameter_display_dict['mirror']['max'] = 1
        self.parameter_display_dict['mirror']['read'] = False

        self.parameter_dict = {}
        for key in self.parameter_display_dict.keys():
            self.parameter_dict[key] = self.parameter_display_dict[key]['val']

    def set_parameter(self, parameter, value):
        """REQUIRED. This function defines how changes in the parameter tree are handled."""
        if parameter == 'central_wave':
            self.parameter_dict['central_wave'] = value
            self.center_wl = value
        elif parameter == 'grating':
            self.parameter_dict['grating'] = value
            self.grating = value
        elif parameter == 'mirror':
            self.parameter_dict['mirror'] = value
            self.mirror = value

    def get_monochromator_parameters(self):
        """
            Returns the current parameters of the monochromator.
            output:
                - central_wavelength (float): the central wavelength in nm
                - grating_lines_per_mm (float): the number of grooves per mm of the selected grating
        """
        return self.center_wl, self.grating_densities[int(self.grating - 1)]
