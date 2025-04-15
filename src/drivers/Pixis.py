# -*- coding: utf-8 -*-
"""
Created on Mon Apr  28 15:09:53 2025

@author: David Tiede
Hardware class to control spectrometer. All hardware classes require a definition of
parameter_display_dict (set Spinbox options and read/write)
set_parameter function (assign set functions)

NOTE:
Communication with Pixis is kind of slow (150ms), such that in the current interface a new image is acquired every 150ms
at the fastest. If ever a faster acquisition is required, transfer of multiple frames per communication (eg. with
cam.grab - see manual or pylablib homepage) can be implemented. For the current planned experiments an acquistion rate of
150ms was judged to be sufficient.
To install driver, picam needs to be installed on the PC. It is freely available at:
https://www.teledynevisionsolutions.com/products/pi_max4/?vertical=tvs-princeton-instruments&segment=tvs&aQ=Picam&aPage=1&dlQ=picam&dlPage=1

"""

import numpy as np
from PyQt5 import QtCore
from collections import defaultdict
from pylablib.devices import PrincetonInstruments
import time


class Pixis(QtCore.QThread):

    name = 'Pixis'
    
    def __init__(self):
        super(Pixis, self).__init__()

        #self.camera.start()
        self.wavelength =  np.linspace(200,1000,1024) # get property from Worker
        self.spec_length = (252,1024) # get property from Worker
        self.image = np.zeros(self.spec_length)

        # Indicate shutter, required to discriminate between different detectors
        self.shutter = True

        # Parameters. Defines parameters that are required for by the interface
        self.avg_scan = 1
        self.int_time = 100
        self.binned_spec = np.zeros(self.spec_length)
        self.new_spectrum = False

        # set parameter dict
        self.parameter_dict = defaultdict()
        """ Set up the parameter dict. 
        Here, all properties of parameters to be handled by the parameter dict are defined."""
        self.parameter_display_dict = defaultdict(dict)
        self.parameter_display_dict['int_time']['val'] = self.int_time
        self.parameter_display_dict['int_time']['unit'] = ' ms'
        self.parameter_display_dict['int_time']['max'] = 10000
        self.parameter_display_dict['int_time']['read'] = False
        self.parameter_display_dict['avg_scan']['val'] = 1
        self.parameter_display_dict['avg_scan']['unit'] = ' scan(s)'
        self.parameter_display_dict['avg_scan']['max'] = 1000
        self.parameter_display_dict['avg_scan']['read'] = False
        self.parameter_display_dict['sensor_T']['val'] = 1
        self.parameter_display_dict['sensor_T']['unit'] = ' celsius'
        self.parameter_display_dict['sensor_T']['min'] = -100
        self.parameter_display_dict['sensor_T']['max'] = 100
        self.parameter_display_dict['sensor_T']['read'] = True

        # set up parameter dict that only contains value. (faster to access)
        self.parameter_dict = {}
        for key in self.parameter_display_dict.keys():
            self.parameter_dict[key] = self.parameter_display_dict[key]['val']

        # initialize camera interface
        self.camera = PrincetonInstruments.PicamCamera()

        # initialize camera
        self.worker = CameraWorker(self.camera,self.int_time)
        self.worker.sendSpectrum.connect(self.update_spectrum) # connect where signals of worker go to.
        self.worker.sendTemperature.connect(self.update_temperature)
        self.worker.start()

        # set int time once
        self.camera.set_attribute_value("Exposure Time", int(self.int_time))

    def set_parameter(self, parameter, value):
        """REQUIRED. This function defines how changes in the parameter tree are handled.
        In devices with workers, a pause of continuous acquisition might be required. """
        if parameter == 'int_time':
            self.parameter_dict['int_time'] = value
            self.worker.int_time = value
            if self.worker.acquiring: # stops acquisition before changing int time if currently acquiring.
                self.stop_acquisition()
                self.camera.set_attribute_value("Exposure Time", int(value))
                self.start_acquisition()
            else:
                self.camera.set_attribute_value("Exposure Time", int(value))
            self.int_time = value
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
        return np.linspace(177.2218, 884.00732139, 1024)

    def start_acquisition(self):
        """ Sets camera to continuous acquisition mode. """
        self.camera.start_acquisition()
        self.worker.acquiring = True

    def stop_acquisition(self):
        """ Disable continuous acquisition mode of camera. """
        self.worker.acquiring = False
        self.camera.stop_acquisition()

    def get_intensities(self):
        """ Gets the intensity. The example include the possibility of averaging several spectra and to
        perform a binning. Such functionalities might also be given by the camera.
        This function will be accessible from MeasurementClasses."""
        if self.avg_scan == 1:
            while not self.new_spectrum:
                time.sleep(0.01)
            spectrum = self.spectrum
            self.new_spectrum = False
        else:
            spectrum = self.image
            for i in range(self.avg_scan):
                time.sleep(self.int_time / 1000 + 0.01)
                while not self.new_spectrum:
                    time.sleep(0.01)
                spectrum = spectrum + self.spectrum
                self.new_spectrum = False
        return spectrum

    def update_temperature(self,temperature):
        self.parameter_dict['sensor_T'] = temperature


class CameraWorker(QtCore.QThread):
    """ This is a DemoWorker for the spectrometer.
    It continously acquires spectra and emits them to the Interface.
    It interrupts data acquisition if an int_time change is requested. Its important because most
    hardware can only handle one command at a time, acquiring or changeing settings.  """
    # These are signals that allow to send data from a child thread to the parent hierarchy.
    sendSpectrum = QtCore.pyqtSignal(np.ndarray, float)
    sendTemperature = QtCore.pyqtSignal(float)

    def __init__(self,camera,int_time):
        super(CameraWorker, self).__init__() # Elevates this thread to be independent.

        # definition of some parameters
        self.camera = camera
        self.spec_length = (252,1024)
        self.change_int_time = False
        self.spectrum = np.zeros(self.spec_length)
        self.int_time = int_time
        self.updated_int_time = int_time
        self.binning = 2
        self.avg_scans = 1
        self.terminate = False
        self.acquiring = False

    def run(self):
        """" Continuous tasks of the Worker are defined here.
        If loops check for requested changes in settings prior each acquisition. """
        while not self.terminate: #infinite loop
            if self.acquiring:
                image = None
                timeout_start = time.time()
                while not type(image) == np.ndarray and not time.time() > timeout_start + self.int_time/1E3 + 0.5:
                    time.sleep(0.02)
                    image = self.camera.read_newest_image()
                try:
                    self.sendSpectrum.emit(image, self.int_time)
                except TypeError:
                    print('WARNING: Spectrum not sent from Worker')
            else:
                time.sleep(1)
            temperature = self.camera.get_attribute_value("Sensor Temperature Reading")
            self.sendTemperature.emit(temperature)
        print('Worker closes')
        return