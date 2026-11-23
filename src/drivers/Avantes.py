# -*- coding: utf-8 -*-
"""
Created on Tue Jan  28 15:26:53 2025

@author: Aerin Marin, David Tiede
Hardware class to control Avantes spectrometer. All hardware classes require a definition of
parameter_display_dict (set Spinbox options and read/write)
set_parameter function (assign set functions)

Notes:
    - Basic driver for Avantes spectrometer, currently no worker implemented. Consider this
    if Silvabot will start lacking at some point.
    - Avantes connection gets sometimes lost, it is currently handled through reconnection.
    One might want to improve the sync with the spectrometer and possibly adapt communication
    channel if needed. Refer to python API (was requested from Avantes, stored on the lab
    server) for detailed explanation.
"""

import numpy as np
from PyQt5 import QtCore
from collections import defaultdict
import time
from src.drivers.AvantesController import AvantesController


class Avantes(QtCore.QThread):

    name = 'Spectrometer'
    
    def __init__(self, port = None):
        super(Avantes, self).__init__()

        # initialize spectrometer
        self.AC = AvantesController()
        self.AC.open_communication()
        self.wavelength = self.AC.wavelengths[:-2]
        self.AC.set_default_config()


        # initialize  spectrometerWorker
        #self.spectrometer = SpectrometerWorker(self.AC)
        #self.spectrometer.sendSpectrum.connect(self.update_spectrum) # connect where signals of worker go to.
        #self.spectrometer.start()
        #self.wavelength = self.spectrometer.wavelengths # get property from Worker
        self.spec_length = len(self.wavelength)# get property from Worker

        # Parameters. Defines parameters that are required for by the interface
        self.avg_scan = 1
        self.binning = 1
        self.int_time = 500
        self.binned_spec = np.zeros(self.spec_length)
        self.new_spectrum = False

        # setting up variables, open array
        self.spectrum = np.array([])

        # set parameter dict
        self.parameter_dict = defaultdict()
        """ Set up the parameter dict. 
        Here, all properties of parameters to be handled by the parameter dict are defined."""
        self.parameter_display_dict = defaultdict(dict)
        self.parameter_display_dict['int_time']['val'] = 500
        self.parameter_display_dict['int_time']['unit'] = ' ms'
        self.parameter_display_dict['int_time']['max'] = 10000
        self.parameter_display_dict['int_time']['read'] = False
        self.parameter_display_dict['binning']['val'] = 1
        self.parameter_display_dict['binning']['unit'] = ' px'
        self.parameter_display_dict['binning']['max'] = 1000
        self.parameter_display_dict['binning']['read'] = False
        self.parameter_display_dict['avg_scan']['val'] = 1
        self.parameter_display_dict['avg_scan']['unit'] = ' scan(s)'
        self.parameter_display_dict['avg_scan']['max'] = 1000
        self.parameter_display_dict['avg_scan']['read'] = False

        # set up parameter dict that only contains value. (faster to access)
        self.parameter_dict = {}
        for key in self.parameter_display_dict.keys():
            self.parameter_dict[key] = self.parameter_display_dict[key]['val']


    def set_parameter(self, parameter, value):
        """REQUIRED. This function defines how changes in the parameter tree are handled.
        In devices with workers, a pause of continuous acquisition might be required. """
        if parameter == 'int_time':
            self.parameter_dict['int_time'] = value
            self.AC.set_integration_time(value)
            self.int_time = value
            self.new_spectrum = False
        elif parameter == 'binning':
            self.parameter_dict['binning'] = value
            self.binning = int(value)
        elif parameter == 'avg_scan':
            self.parameter_dict['avg_scan'] = value
            self.AC.set_number_of_averages(int(value))

    def update_spectrum(self, spec, int_time):
        """REQUIRED. This is the slot function for the sendSpectrum pyqt.signal from the worker.
        It updates the last saved spectrum and changes the self.new_spectrum Boolean to True
        to allow to emit the treated signal from the spectrometer."""
        if int_time == self.int_time:  # check if spectrum is acquired with desired int conditions
            self.spectrum = spec
            self.new_spectrum = True

    def get_wavelength(self):
        """This simply returns the wavelength. In Colbert this needs to be adapted if the calibration
         changes. This function will be accessible from MeasurementClasses. """
        return self.wavelength

    def get_intensities(self):
        """ Gets the intensity. The example include the possibility of averaging several spectra and to
        perform a binning. Such functionalities might also be given by the camera.
        This function will be accessible from MeasurementClasses."""
        spectrum = self.AC.grab_spectrum()[0][:-2]
        # check if spectrum has values: if all is 0, do reconnection protocol.
        if np.max(spectrum) == 0:
            print(time.strftime('%H:%M:%S') + ' Avantes communication error: Try to reconnect.')
            time.sleep(1)
            self.AC.close_communication()
            time.sleep(1)
            self.AC.open_communication()
            self.AC.set_default_config()
            self.AC.set_integration_time(self.int_time)
            spectrum = self.AC.grab_spectrum()[0][:-2]
        return self.do_binning(spectrum)

    def do_binning(self, spectrum):
        """ Manual binning of the spectra. Some cameras might allow to readout pixel together to increase
        signal-to-noise at the cost of lower resolution. """
        #print(spectrum)
        for i in range(self.spec_length):
            if i > self.spec_length - self.binning:
                self.binned_spec[i] = np.sum(spectrum[self.spec_length - self.binning:self.spec_length])
            elif i < self.binning:
                self.binned_spec[i] = np.sum(spectrum[0:i])
            else:
                self.binned_spec[i] = np.sum(spectrum[i - self.binning + 1:i + self.binning])
        return self.binned_spec/(2 * (self.binning - 1) + 1)/self.avg_scan
