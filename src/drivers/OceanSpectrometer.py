# -*- coding: utf-8 -*-
"""
Created on Thu Sep  4 13:26:53 2022

@author: NanoUltrafast2
Hardware class to control spectrometer. All hardware classes require a definition of
parameter_dict (set write and read parameter)
parameter_display_dict (set Spinbox options)
set_parameter function (assign set functions)

Based on pyseabreeze (c) A Poehlmann. Unfortunately, some features such as direct binning and averaging in spectrometer
is not implemented and performed manually in this file.

 TODO:
 implement acquiring method in which interface is waiting for new spectrum
"""
import numpy as np
import sys
from PyQt5 import QtCore
import time
from collections import defaultdict
from datetime import datetime
# delete all seabreeze residuals of different spectrometer
# if 'seabreeze' in sys.modules:
#     del sys.modules["seabreeze"]
#     del sys.modules["seabreeze._version"]
#     del sys.modules["seabreeze.backends"]
#     del sys.modules["seabreeze.spectrometers"]
import seabreeze
seabreeze.use('cseabreeze')
from seabreeze.spectrometers import list_devices, Spectrometer

class OceanSpectrometer(QtCore.QThread):

    name = 'Spectrometer'
    
    def __init__(self, port =None):
        super(OceanSpectrometer, self).__init__()

        # load spectrometer
        self.spectrometer = OceanSpectrometerWorker()
        self.spectrometer.sendSpectrum.connect(self.update_spectrum)
        self.spectrometer.start()
        self.wavelength = self.spectrometer.wavelengths
        self.spectrum = np.ndarray([])
        self.spec_length = self.spectrometer.speclength
        self.binnedspec = np.zeros(self.spec_length)
        self.int_time = 500
        self.binning = 1
        self.avg_scan = 1
        self.new_spectrum = False
        self.probe_trigger = False

        # set parameter dict
        self.parameter_dict = defaultdict()
        
        # setting up variables, open array
        self.stop = False
        self.parameter_dict['int_time'] = 500
        self.parameter_dict['binning'] = 1
        self.parameter_dict['avg_scan'] = 1
        self.parameter_display_dict = defaultdict(dict)
        self.parameter_display_dict['int_time']['val'] = 500
        self.parameter_display_dict['int_time']['unit'] = ' ms'
        self.parameter_display_dict['int_time']['max'] = 10000
        self.parameter_display_dict['int_time']['read'] = False
        self.parameter_display_dict['binning']['val'] = 1
        self.parameter_display_dict['binning']['unit'] = ' px'
        self.parameter_display_dict['binning']['max'] = 20  # higher value gives error
        self.parameter_display_dict['binning']['read'] = False
        self.parameter_display_dict['avg_scan']['val'] = 1
        self.parameter_display_dict['avg_scan']['unit'] = ' scan(s)'
        self.parameter_display_dict['avg_scan']['max'] = 1000
        self.parameter_display_dict['avg_scan']['read'] = False

        # set parameter once to initialize
        self.set_parameter("int_time", self.parameter_dict['int_time'])

    def set_parameter(self, parameter, value):
        if parameter == 'int_time':
            self.parameter_dict['int_time'] = value
            self.spectrometer.set_int_time(value)
            self.int_time = value
            self.new_spectrum = False
        elif parameter == 'binning':
            self.parameter_dict['binning'] = value
            self.binning = int(value)
            # self.spectrometer.set_parameter(value, self.parameter_dict['avg_scan'])
        elif parameter == 'avg_scan':
            self.parameter_dict['avg_scan'] = value
            self.avg_scan = int(value)

    def update_spectrum(self, spec, int_time):
        if int_time == self.int_time:  # check if spectrum is acquired with desired int conditions
            self.spectrum = spec
            self.new_spectrum = True

    def get_wavelength(self):
        return self.wavelength

    def get_intensities(self):
        # adapted measurement scheme to have spectrometer in 10ms acquisition if not actively used.
        # This is a compromise between continuously acquiring and having a fast, trigger-like response time
        if self.probe_trigger: # NOT USED CURRENTLY
            self.spectrometer.set_int_time(self.int_time)
            if self.avg_scan == 1:
                while not self.new_spectrum:
                    time.sleep(0.05)
                spectrum = self.spectrum
                self.new_spectrum = False
            else:
                spectrum = np.zeros(len(self.spectrum))
                for i in range(self.avg_scan):
                    time.sleep(self.int_time / 1000 + 0.05)
                    while not self.new_spectrum:
                        time.sleep(0.05)
                    spectrum = spectrum + self.spectrum
                    self.new_spectrum = False
            self.spectrometer.set_int_time(10)
        else:
            if self.avg_scan == 1:
                while not self.new_spectrum:
                    time.sleep(0.05)
                spectrum = self.spectrum
                self.new_spectrum = False
            else:
                spectrum = np.zeros(len(self.spectrum))
                for i in range(self.avg_scan):
                    #time.sleep(self.int_time / 1000 + 0.01)
                    while not self.new_spectrum:
                        time.sleep(0.01)
                    spectrum = spectrum + self.spectrum
                    self.new_spectrum = False
            spectrum = self.do_binning(spectrum)
            time.sleep(0.005)
        return spectrum

    def do_binning(self, spectrum):
        for i in range(len(self.wavelength)):
            if i > self.spec_length - self.binning:
                self.binnedspec[i] = np.sum(spectrum[self.spec_length - self.binning:self.spec_length])
            elif i < self.binning:
                self.binnedspec[i] = np.sum(spectrum[0:i])
            else:
                self.binnedspec[i] = np.sum(spectrum[i - self.binning + 1:i + self.binning])
        return self.binnedspec/(2*(self.binning-1) + 1)/self.avg_scan


class OceanSpectrometerWorker(QtCore.QThread):

    sendSpectrum = QtCore.pyqtSignal(np.ndarray, float)
    sendSave = QtCore.pyqtSignal()

    def __init__(self):
        super(OceanSpectrometerWorker, self).__init__()
        specname = Spectrometer.from_first_available()
        self.spec = specname
        self.speclength = len(self.spec.wavelengths())
        if str(specname.model) == 'USB4000':
            self.speclength = 3646
            self.spec_range = np.r_[0:3646]
        elif str(specname.model) == 'FLAMEX':
            self.speclength = 2048
            self.spec_range = np.r_[88:2136]
        elif str(specname.model) == 'HR4000':
            self.speclength = 3648
            self.spec_range = np.r_[0:3648]
        else:
            self.speclength = 2048
            self.spec_range = np.r_[0:2048]
        self.change_int_time = False
        self.change_settings = False
        self.stop = False                 
        self.spectrum = np.zeros(self.speclength)
        self.wavelengths = self.spec.wavelengths()[self.spec_range]
        self.int_time = 500
        self.binning = 2
        self.avg_scans = 1
        self.curr_int_time = 0
        self.last_acquisition_time = time.time()
        print('Spectrometer ' + str(specname.model) + ' loaded')

    def run(self):
        while self.terminate:
            if not self.change_int_time:
                if time.time() - self.last_acquisition_time < 0.05: # prevent crash due to too fast acquisition
                    time.sleep(0.05)
                self.last_acquisition_time = time.time()
                self.spectrum = self.spec.f.spectrometer.get_intensities()[self.spec_range]
                if not self.change_int_time:                          
                    self.sendSpectrum.emit(self.spectrum, self.curr_int_time)

            else:
                self.change_int_time = False
                self.spec.integration_time_micros(self.int_time * 1000)
                self.curr_int_time = self.int_time
        return

    def set_int_time(self, int_time):
        self.change_int_time = True
        self.int_time = int_time
