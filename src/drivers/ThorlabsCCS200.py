"""
Created on Fri Apr  11 10:40:53 2025

@author: David Tiede
Hardware class to control spectrometer. All hardware classes require a definition of
parameter_display_dict (set Spinbox options and read/write)
set_parameter function (assign set functions)

IMPORTANT: DEVICE ID might need to be adapted in Update Worker (currently line 149) if different PC/device is used
IMPORTANT: If CCS200 is not detected in ThorSpectra, carefully check drivers. It needs to be exactly as shown in:
https://openproject.silvascience.org/projects/silvabot/wiki/thorlabs-ccs200-drivers

If driuer is not correct, consider reinstalling ThorSpectra, even though it is already installed on the PC.
"""

import numpy as np
from PyQt5 import QtCore
from collections import defaultdict
import time
import os
from ctypes import *


class ThorlabsCCS200(QtCore.QThread):
    name = 'Spectrometer'

    def __init__(self, port =None):
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
        self.parameter_display_dict['int_time']['max'] = 20000
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
        for i in range(self.spec_length):
            if i > self.spec_length - self.binning:
                self.binned_spec[i] = np.sum(spectrum[self.spec_length - self.binning:self.spec_length])
            elif i < self.binning:
                self.binned_spec[i] = np.sum(spectrum[0:i])
            else:
                self.binned_spec[i] = np.sum(spectrum[i - self.binning + 1:i + self.binning])
        return self.binned_spec / (2 * (self.binning - 1) + 1) / self.avg_scan


class SpectrometerWorker(QtCore.QThread):
    """
    Worker for the Thorlabs CCS200 spectrometer.

    Continuously acquires spectra and emits them to the interface.

    If an acquisition does not complete within acquisition_timeout,
    the USB connection to the spectrometer is closed and reinitialized.
    """

    sendSpectrum = QtCore.pyqtSignal(np.ndarray, float)

    DEVICE_ID = b"USB0::0x1313::0x8089::M00582935::RAW"

    def __init__(self):
        super(SpectrometerWorker, self).__init__()

        # Load DLL
        os.chdir(os.path.join(os.getcwd(), "src\\drivers\\dlls"))
        self.lib = cdll.LoadLibrary("TLCCS_64.dll")

        # Parameters
        self.spec_length = 3648
        self.int_time = 500
        self.updated_int_time = 500

        self.change_int_time = False
        self.terminate = False

        self.spectrum = np.zeros(self.spec_length)

        # Connection parameters
        self.ccs_handle = c_int(0)
        self.connected = False

        # Number of reconnect attempts
        self.max_reconnect_attempts = 3

        # Acquisition timeout:
        # integration time + additional margin
        self.acquisition_timeout = 3.0

        # ctypes arrays
        self.wavelengths_c = (c_double * self.spec_length)()
        self.spectrum_c = (c_double * self.spec_length)()

        # Connect to spectrometer
        if not self.connect_spectrometer():
            print("Spectro Worker: Initial connection failed.")

    # ------------------------------------------------------------------
    # CONNECTION MANAGEMENT
    # ------------------------------------------------------------------

    def connect_spectrometer(self):
        """
        Initialize/reinitialize the CCS200 connection.

        Returns
        -------
        bool
            True if connection was successfully initialized.
        """
        try:
            print("Spectro Worker: Connecting to CCS200...")
            self.ccs_handle = c_int(0)
            status = self.lib.tlccs_init(self.DEVICE_ID,1,1,byref(self.ccs_handle))
            # A zero/negative handle generally indicates failure
            if self.ccs_handle.value <= 0:
                self.connected = False
                return False

            # Set integration time
            status = self.lib.tlccs_setIntegrationTime(self.ccs_handle,c_double(self.int_time * 1E-3))

            # Get wavelength calibration
            status = self.lib.tlccs_getWavelengthData(self.ccs_handle ,0 ,
                byref(self.wavelengths_c), c_void_p(None), c_void_p(None))
            self.wavelengths = np.ctypeslib.as_array(self.wavelengths_c).copy()
            self.connected = True
            print("Spectro Worker: CCS200 connected successfully.")
            return True
        except Exception as e:
            print(f"Spectro Worker: Connection error: {e}")
            self.connected = False
            return False

    def disconnect_spectrometer(self):
        """
        Close the CCS200 connection.
        """
        if not self.connected:
            return
        try:
            print("Spectro Worker: Closing CCS200 connection...")
            self.lib.tlccs_close(self.ccs_handle)
        except Exception as e:
            print(f"Spectro Worker: Error while closing CCS200: {e}")
        finally:
            self.connected = False
            self.ccs_handle = c_int(0)

    def reconnect_spectrometer(self):
        """
        Close and reinitialize the CCS200 connection.
        """
        print("Spectro Worker: Restarting spectrometer connection...")
        self.disconnect_spectrometer()
        # Give Windows/USB driver some time to release the device
        time.sleep(0.5)
        for attempt in range(1, self.max_reconnect_attempts + 1):
            print(f"Spectro Worker: Reconnect attempt {attempt}/{self.max_reconnect_attempts}")
            if self.connect_spectrometer():
                # Give the spectrometer a moment to stabilize
                time.sleep(0.2)
                print("Spectro Worker: Reconnection successful.")
                return True
            time.sleep(1.0)
        print("Spectro Worker: Reconnection FAILED.")
        return False

    # ------------------------------------------------------------------
    # THREAD
    # ------------------------------------------------------------------

    def run(self):
        """
        Continuous acquisition loop.
        """
        while not self.terminate:
            # Handle integration-time changes
            if self.change_int_time:
                if self.int_time == self.updated_int_time:
                    self.change_int_time = False
                else:
                    print("Spectro Worker: Acquisition stopped to change int time")
                    self.set_int_time(self.updated_int_time)
                    # Give hardware some time to settle
                    time.sleep(0.1)
                continue
            # Acquire spectrum
            spectrum = self.getIntensities()
            # getIntensities returns None when acquisition failed
            if spectrum is None:
                print("Spectro Worker: Spectrum acquisition failed. Attempting reconnect...")

                if self.reconnect_spectrometer():
                    print("Spectro Worker: Reconnected. Resuming acquisition.")
                    spectrum = self.getIntensities()
                else:
                    print("Spectro Worker: Could not reconnect. Retrying in 2 s.")
                    time.sleep(2.0)
                    spectrum = np.zeros(3648)
                continue

            # Only emit if integration time has not changed
            if not self.change_int_time:
                self.sendSpectrum.emit(spectrum,self.int_time)
        return

    # ------------------------------------------------------------------
    # ACQUISITION
    # ------------------------------------------------------------------

    def getIntensities(self):
        """
        Acquire one spectrum.

        If the spectrometer does not finish the acquisition within
        acquisition_timeout, return None so that the worker can reconnect.
        """

        if not self.connected:
            return None

        try:
            # Start scan
            status_start = self.lib.tlccs_startScan(self.ccs_handle)
            # Maximum allowed waiting time
            timeout = self.int_time * 1E-3 + 2.0
            start_time = time.monotonic()
            status = c_int(0)
            while not self.terminate:
                self.lib.tlccs_getDeviceStatus(self.ccs_handle,byref(status))
                # 0x0010 = scan complete
                if status.value & 0x0010:
                    break
                # Timeout
                if time.monotonic() - start_time > timeout:
                    print(f"Spectro Worker: Acquisition timeout. Status = 0x{status.value:04X}")
                    return None
                time.sleep(0.01)
            # Check termination
            if self.terminate:
                return None
            # Retrieve spectrum
            status_data = self.lib.tlccs_getScanData(self.ccs_handle,byref(self.spectrum_c))
            self.spectrum = np.ctypeslib.as_array(self.spectrum_c).copy()
            return self.spectrum
        except Exception as e:
            print(f"Spectro Worker: Acquisition exception: {e}")
            return None

    # ------------------------------------------------------------------
    # INTEGRATION TIME
    # ------------------------------------------------------------------

    def set_int_time(self, int_time):
        """
        Prepare and apply a new integration time.
        """
        self.change_int_time = True
        self.updated_int_time = int_time
        # Wait approximately until current acquisition has finished
        time.sleep(self.int_time * 1E-3)
        try:
            status = self.lib.tlccs_setIntegrationTime(self.ccs_handle,c_double(int_time * 1E-3))
            self.int_time = self.updated_int_time
        except Exception as e:
            print(f"Spectro Worker: Error changing integration time: {e}")
            # Force reconnection
            self.connected = False