"""
Created on Fri Apr  11 10:40:53 2025

@author: David Tiede
Hardware class to control spectrometer. All hardware classes require a definition of
parameter_display_dict (set Spinbox options and read/write)
set_parameter function (assign set functions)

"""

import numpy as np
from PyQt5 import QtCore
from collections import defaultdict
import time
import os
from ctypes import *


class ThorlabsCCS200(QtCore.QThread):
    name = 'Spectrometer'

    def __init__(self):
        super(ThorlabsCCS200, self).__init__()

        # load and initialize  spectrometerWorker
        self.spectrometer = SpectrometerWorker()
        self.spectrometer.sendSpectrum.connect(self.update_spectrum)  # connect where signals of worker go to.
        self.spectrometer.start()
        self.wavelength = self.spectrometer.wavelengths  # get property from Worker
        self.spec_length = self.spectrometer.spec_length  # get property from Worker
        self.int_time = self.spectrometer.int_time  # get property from Worker

        # preallocate arrays
        self.spectrum = np.ndarray([])
        self.binned_spec = np.zeros(self.spec_length)

        # Parameters. Defines parameters that are required for by the interface
        self.avg_scan = 1
        self.binning = 1
        self.int_time = 500
        self.binned_spec = np.zeros(self.spec_length)
        self.new_spectrum = False

        # setting up variables, open array
        self.spectrum = np.array([])
        self.wavelength = np.array([])

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
            self.spectrometer.set_int_time(value)
            self.int_time = value
            self.new_spectrum = False
        elif parameter == 'binning':
            self.parameter_dict['binning'] = value
            self.binning = int(value)
        elif parameter == 'avg_scan':
            self.parameter_dict['avg_scan'] = value
            self.avg_scan = int(value)

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
        return self.spectrometer.wavelengths

    def get_intensities(self):
        """ Gets the intensity. The example include the possibility of averaging several spectra and to
        perform a binning. Such functionalities might also be given by the camera.
        This function will be accessible from MeasurementClasses."""
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
        return self.do_binning(spectrum)

    def do_binning(self, spectrum):
        """ Manual binning of the spectra. Some cameras might allow to readout pixel together to increase
        signal-to-noise at the cost of lower resolution. """
        # print(spectrum)
        for i in range(self.spec_length):
            if i > self.spec_length - self.binning:
                self.binned_spec[i] = np.sum(spectrum[self.spec_length - self.binning:self.spec_length])
            elif i < self.binning:
                self.binned_spec[i] = np.sum(spectrum[0:i])
            else:
                self.binned_spec[i] = np.sum(spectrum[i - self.binning + 1:i + self.binning])
        return self.binned_spec / (2 * (self.binning - 1) + 1) / self.avg_scan


class SpectrometerWorker(QtCore.QThread):
    """ This is a DemoWorker for the spectrometer.
    It continously acquires spectra and emits them to the Interface.
    It interrupts data acquisition if an int_time change is requested. Its important because most
    hardware can only handle one command at a time, acquiring or changeing settings.  """
    # These are signals that allow to send data from a child thread to the parent hierarchy.
    sendSpectrum = QtCore.pyqtSignal(np.ndarray, float)

    def __init__(self):
        super(SpectrometerWorker, self).__init__()  # Elevates this thread to be independent.

        # definition of some parameters
        os.chdir(r"C:\Program Files\IVI Foundation\VISA\Win64\Bin")
        self.lib = cdll.LoadLibrary("TLCCS_64.dll")
        self.ccs_handle = c_int(0)

        self.spec_length = 3648
        self.int_time = 10
        integration_time = c_double(10.0e-3)
        integration_time = c_double(0.2)
        self.lib.tlccs_setIntegrationTime(self.ccs_handle, c_double(self.int_time/1E3))
        # start scan
        self.lib.tlccs_startScan(self.ccs_handle)


        self.wavelengths_c = (c_double * self.spec_length)()
        self.spectrum_c = (c_double * self.spec_length)()
        self.lib.tlccs_getWavelengthData(self.ccs_handle, 0, byref(self.wavelengths_c), c_void_p(None), c_void_p(None))
        self.wavelengths = np.ctypeslib.as_array(self.wavelengths_c)
        print(self.wavelengths)

        self.spec_range = np.r_[0:2048]
        self.change_int_time = False
        self.spectrum = np.zeros(self.spec_length)
        self.updated_int_time = 500
        self.avg_scans = 1
        self.terminate = False
        print("CCS200 init finished")

    def run(self):
        """" Continuous tasks of the Worker are defined here.
        If loops check for requested changes in settings prior each acquisition. """
        while not self.terminate:  # infinite loop
            print("Enter run")
            if not self.change_int_time:
                self.spectrum = self.getIntensities()
                print("after intensities")
                if not self.change_int_time:
                    self.sendSpectrum.emit(self.spectrum, self.int_time)
                print("First spectrum")
            else:
                if self.int_time == self.updated_int_time:
                    self.change_int_time = False
                else:
                    time.sleep(0.1)
            print("while loop")
                # Here needs to go a command that changes the int time at the spectrometer.
                # print(time.strftime('%H:%M:%S') + ' PL Spectrum acquired')
        return

    def getIntensities(self):
        # create random spectrum. Some varying random signal helps to check functionality.
        print("in intensities")
        self.lib.tlccs_startScan(self.ccs_handle)
        status = c_int(0)
        while (status.value & 0x0010) == 0:
            self.lib.tlccs_getDeviceStatus(self.ccs_handle, byref(status))
        self.lib.tlccs_getScanData(self.ccs_handle, byref(self.spectrum_c))
        self.spectrum = np.ctypeslib.as_array(self.spectrum_c)
        return self.spectrum

    def set_int_time(self, int_time):
        # This function is called from the interface.
        # It prepares the change of the integration before the next spectrum is acquired.
        self.change_int_time = True
        self.updated_int_time = int_time
        self.lib.tlccs_setIntegrationTime(self.ccs_handle, int_time)
        self.int_time = self.updated_int_time