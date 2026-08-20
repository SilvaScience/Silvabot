
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@author: KatieKoch, Felix Thouin

Monochromator driver for the Princeton Instruments SpectraPro family (SP2150, SP2300i, ...),
which share a command set. Only exposes its own live state: central wavelength, grating, mirror.

It has no notion of which camera reads through it. The optical calibration belongs to the
camera/monochromator pairing and lives with drivers.Spectrograph, so this driver stays reusable
across tables.

Older units do not answer ?GRATINGS reliably (seen on the SP2150 of the Alize and Heliotis
tables). Pass `gratings` in init_args to declare the turret instead of querying it.
"""

import numpy as np
from PyQt5 import QtCore
from collections import defaultdict
import time
import serial
import re

def parse_turret(response):
    """
        Reads the installed gratings out of a ?GRATINGS response.
        input:
            - response (str): the controller's answer, decoded
        output:
            - tuple (num_gratings, densities np.ndarray, blazes np.ndarray in nm)

        One line per installed grating, e.g.
        '1  1200 g/mm BLZ=  300NM 
2  1200 g/mm BLZ=  750NM 
3   300 g/mm BLZ=  2.0UM 
 ok',
        plus one bare index-only line per empty turret slot. Matching the whole pattern -- index,
        density, 'g/mm', 'BLZ=', value, unit -- is what tells an installed grating from an empty
        slot, and keeps the blaze's decimal point and unit (NM vs UM) intact. Pulling every digit
        out instead and guessing the count from a fixed-length formula miscounts as soon as a blaze
        reads in UM, because the decimal point splits into two tokens and shifts everything after it.
    """
    matches = re.findall(r'(\d+)\s+(\d+)\s*g/mm\s*BLZ=\s*([\d.]+)\s*(NM|UM)',
                         response, re.IGNORECASE)
    if not matches:
        raise ValueError(f'no grating could be read from {response!r}.')
    densities = np.array([float(d) for _, d, _, _ in matches])
    blazes = np.array([float(b) * (1000 if u.upper() == 'UM' else 1) for _, _, b, u in matches])
    return len(matches), densities, blazes


class SpectraPro(QtCore.QThread):

    type = 'Monochromator'

    def __init__(self, port='COM5', model='SpectraPro2300i', gratings=None, has_mirror=True):
        """
            input:
                - port (str): serial port the controller answers on
                - model (str): unit this is, e.g. 'SpectraPro2300i' or 'SpectraPro2150'. Reported
                  as self.name and matched against the calibration's `monochromator` field.
                - gratings (list, default None): turret declared as [{'density': 600, 'blaze': 1200},
                  ...], for units whose ?GRATINGS answer cannot be trusted. None queries the unit.
                - has_mirror (bool, default True): query and expose the exit mirror
        """
        super(SpectraPro, self).__init__()

        self.name = model
        self.has_mirror = has_mirror

        # set up spectrograph
        self.serial_busy = False
        self.ser = serial.Serial(port=port, baudrate=9600, bytesize=8, parity='N',
                                 stopbits=1, xonxoff=0, rtscts=0, timeout=0.02)
        # get startup values
        self.grating = float(self.write_command('?GRATING')[0])
        if gratings is not None:
            # Declared turret: the unit is not asked. See the module docstring.
            self.num_gratings = len(gratings)
            self.grating_densities = np.array([float(g['density']) for g in gratings])
            self.grating_blazes = np.array([float(g['blaze']) for g in gratings])
            print(f'{self.name}: turret declared in config, ?GRATINGS not queried')
        else:
            self.num_gratings, self.grating_densities, self.grating_blazes = self.query_turret()
        self.center_wl = float(self.write_command('?NM')[0])
        self.mirror = float(self.write_command('?MIR')[0]) if self.has_mirror else 0.0
        print(f'{self.name}: centre {self.center_wl} nm, grating {self.grating} of {self.num_gratings}')
        print(f'{self.name}: densities {self.grating_densities}, blazes {self.grating_blazes}')

        # set parameter dict
        self.parameter_dict = defaultdict()
        """ Set up the parameter dict.
        Here, all properties of parameters to be handled by the parameter dict are defined."""

        self.parameter_display_dict = defaultdict(dict)

        self.parameter_display_dict['central_wave']['val'] = self.center_wl
        self.parameter_display_dict['central_wave']['unit'] = ' nm'
        self.parameter_display_dict['central_wave']['min'] = 0.00
        self.parameter_display_dict['central_wave']['max'] = 1100.00
        self.parameter_display_dict['central_wave']['read'] = False

        self.parameter_display_dict['grating']['val'] = self.grating
        self.parameter_display_dict['grating']['unit'] = ' grat'
        self.parameter_display_dict['grating']['min'] = 1
        self.parameter_display_dict['grating']['max'] = 3
        self.parameter_display_dict['grating']['read'] = False

        if self.has_mirror:  # units without one would get a spinbox driving nothing
            self.parameter_display_dict['mirror']['val'] = self.mirror
            self.parameter_display_dict['mirror']['unit'] = ' mirror'
            self.parameter_display_dict['mirror']['min'] = 0
            self.parameter_display_dict['mirror']['max'] = 1
            self.parameter_display_dict['mirror']['read'] = False

        # set up parameter dict that only contains value. (faster to access)
        self.parameter_dict = {}
        for key in self.parameter_display_dict.keys():
            self.parameter_dict[key] = self.parameter_display_dict[key]['val']

    def query_turret(self):
        """
            Reads the installed gratings from the unit.
            output:
                - tuple (num_gratings, densities np.ndarray, blazes np.ndarray in nm)
        """
        response = self.write_command_raw('?GRATINGS')
        try:
            return parse_turret(response)
        except ValueError as e:
            raise RuntimeError(
                f'{self.name}: {e} Older units answer unreliably; declare the turret with the '
                '`gratings` init_arg instead.')

    def write_command_raw(self, cmd):
        """ Command to write to serial handles timeout by blocking serial commands
        Args:
            ser: serial object
            cmd: write command as defined in PI API

        Returns: the decoded response as-is, with no parsing. Used directly by callers that need
        more than bare digits (e.g. ?GRATINGS, whose blaze values and units write_command's digit
        extraction would otherwise lose).
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
        return out.decode().strip()

    def write_command(self, cmd):
        """ Same handshake as write_command_raw, returning only the digit content. For
        troubleshooting, consider using write_command_raw to see the entire answer string. """
        return re.findall(r'\d+', self.write_command_raw(cmd))

    def set_parameter(self, parameter, value):
        """REQUIRED. This function defines how changes in the parameter tree are handled.
        In devices with workers, a pause of continuous acquisition might be required. """
        if parameter == 'central_wave':
            cmd = f'{value:0.3f} GOTO'
            self.write_command(cmd)
            self.parameter_dict['central_wave'] = value
            self.center_wl = value
        elif parameter == 'grating':
            cmd = f'{value:1.0f} GRATING'
            self.write_command(cmd)
            self.parameter_dict['grating'] = value
            self.grating = value
        elif parameter == 'mirror' and self.has_mirror:
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
