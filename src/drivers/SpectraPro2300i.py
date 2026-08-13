
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@author: KatieKoch, Felix Thouin

Monochromator driver. Only exposes its own live state (central wavelength, grating, mirror).
Cameras that read through this monochromator carry their own optical calibration constants in
their own hardware_params (set from config.yaml) and pull the live grating readout from here via
get_monochromator_parameters() -- this driver has no notion of which cameras are attached, so it
stays reusable across setups.
"""

import numpy as np
from PyQt5 import QtCore
from collections import defaultdict
import time
import serial
import re

class SpectraPro2300i(QtCore.QThread):

    name = 'SpectraPro2300i'
    type = 'Monochromator'

    def __init__(self, port='COM5'):
        super(SpectraPro2300i, self).__init__()

        # set up spectrograph
        self.serial_busy = False
        self.ser = serial.Serial(port=port, baudrate=9600, bytesize=8, parity='N',
                                 stopbits=1, xonxoff=0, rtscts=0, timeout=0.02)
        # get startup values
        self.grating = float(self.write_command('?GRATING')[0])
        numbers = self.write_command('?GRATINGS')
        self.num_gratings = int((len(numbers)-8)/2)
        self.grating_densities = np.zeros(self.num_gratings)
        self.grating_blazes = np.zeros(self.num_gratings)
        for i in range(self.num_gratings):
            self.grating_densities[i] = numbers[i*3 + 1]
            self.grating_blazes[i] = numbers[i * 3 + 2]
        self.center_wl = float(self.write_command('?NM')[0])
        self.mirror = float(self.write_command('?MIR')[0])
        print(self.center_wl)
        print(self.grating_densities)
        print(self.grating_blazes)
        print(self.grating)
        print('SP2300 grating info: ', numbers)
        print('SP2300 grating densities: ',self.grating_densities)
        print('SP2300 grating blazes: ',self.grating_blazes)
        print('SP2300 selected grating: ',self.grating)

        # set parameter dict
        self.parameter_dict = defaultdict()
        """ Set up the parameter dict.
        Here, all properties of parameters to be handled by the parameter dict are defined."""

        self.parameter_display_dict = defaultdict(dict)

        self.parameter_dict['central_wave'] = self.center_wl
        self.parameter_dict['grating'] = self.grating
        self.parameter_dict['mirror'] = self.mirror

        self.parameter_display_dict['central_wave']['val'] = self.center_wl
        self.parameter_display_dict['central_wave']['unit'] = ' nm'
        self.parameter_display_dict['central_wave']['min'] = 200.00
        self.parameter_display_dict['central_wave']['max'] = 1100.00
        self.parameter_display_dict['central_wave']['read'] = False

        self.parameter_display_dict['grating']['val'] = self.grating
        self.parameter_display_dict['grating']['unit'] = ' grat'
        self.parameter_display_dict['mirror']['min'] = 1
        self.parameter_display_dict['grating']['max'] = 3
        self.parameter_display_dict['grating']['read'] = False

        self.parameter_display_dict['mirror']['val'] = self.mirror
        self.parameter_display_dict['mirror']['unit'] = ' mirror'
        self.parameter_display_dict['mirror']['min'] = 0
        self.parameter_display_dict['mirror']['max'] = 1
        self.parameter_display_dict['mirror']['read'] = False

        # set up parameter dict that only contains value. (faster to access)
        self.parameter_dict = {}
        for key in self.parameter_display_dict.keys():
            self.parameter_dict[key] = self.parameter_display_dict[key]['val']

    def write_command(self, cmd):
        """ Command to write to serial handles timeout by blocking serial commands
        Args:
            ser: serial object
            cmd: write command as defined in PI API

        Returns: read string with only digit content. For troubleshooting, consider printing
        the entire answer string
        """
        cmd_bytes = cmd.encode('ASCII')
        self.ser.write(cmd_bytes + b"\r")
        out = bytearray()
        char = b""
        missed_char_count = 0
        while char != b"k":
            char = self.ser.read()
            if char == b"":  # handles a timeout here
                missed_char_count += 1
                self.serial_busy = True
                time.sleep(0.1)
            out += char
        self.serial_busy = False
        return re.findall(r'\d+', out.decode().strip())

    def set_parameter(self, parameter, value):
        """REQUIRED. This function defines how changes in the parameter tree are handled.
        In devices with workers, a pause of continuous acquisition might be required. """
        if parameter == 'central_wave':
            cmd = f'{value:0.3f} GOTO'
            self.write_command(cmd)
            self.parameter_dict['center_wave'] = value
            self.center_wl = value
        elif parameter == 'grating':
            cmd = f'{value:1.0f} GRATING'
            self.write_command(cmd)
            self.parameter_dict['grating'] = value
            self.grating = value
        elif parameter == 'mirror':
            cmd = f'{value:1.0f} MIRROR'
            self.write_command(cmd)
            self.parameter_dict['mirror'] = value
            self.mirror = value

    def get_monochromator_parameters(self):
        """
            Returns the current parameters of the monochromator.
            output:
                - central_wavelength (np.float): the central wavelength in nm
                - grating_lines_per_mm (np.float): the number of groove per mm of the selected grating
        """
        return self.center_wl, self.grating_densities[int(self.grating-1)]
