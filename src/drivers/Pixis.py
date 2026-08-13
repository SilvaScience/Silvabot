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
import threading
import time
import re

class Pixis(QtCore.QThread):

    name = 'Pixis'

    def __init__(self, hardware_params):
        super(Pixis, self).__init__()

        #self.camera.start()
        self.wavelength = np.linspace(200,1000,1024) # get property from Worker
        self.px0 = np.linspace(1,1024,1024)
        self.spec_length = 1024 #(252,1024) # get property from Worker
        self.image = np.zeros(self.spec_length)
        self.hardware_params = hardware_params
        # By default, no monochromator is attached. Kept as its own attribute (rather than only set
        # in attach_to_monochromator) so calculate_wavelength_array() can be called safely before
        # attachment instead of raising AttributeError.
        self.monochromator = None

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
        """ A reading, not a setting: set_parameter() has no branch for it, and the worker is what
        updates it. Declaring it writable put it among the parameters the updater does not poll, so
        the temperature on screen never changed after startup. """
        self.parameter_display_dict['sensor_T']['read'] = True

        # set up parameter dict that only contains value. (faster to access)
        self.parameter_dict = {}
        for key in self.parameter_display_dict.keys():
            self.parameter_dict[key] = self.parameter_display_dict[key]['val']

        # initialize camera interface
        print('Initialize Camera')
        print(PrincetonInstruments.list_cameras())
        self.camera = PrincetonInstruments.PicamCamera()
        print('Camera connected')

        """ The camera is driven from two threads: the measurement thread through get_intensities(),
        and the GUI thread through set_roi() when a readout region is applied. Interleaving those
        made PICam fail with AcquisitionInProgress. Reentrant because set_roi() starts and stops the
        acquisition while already holding the lock. """
        self.camera_lock = threading.RLock()

        # Determine the number of sensor rows available for vertical binning.
        # The PIXIS used here is 1024 x 256, but ask the camera rather than assume.
        self.sensor_height = int(self.hardware_params.get('sensor_height', 256))
        try:
            detector_size = self.camera.get_detector_size()  # (width, height)
            if detector_size is not None and len(detector_size) == 2:
                self.sensor_height = int(detector_size[1])
        except Exception as e:
            print(f'Pixis: could not query detector size, assuming {self.sensor_height} rows. {e}')

        """ Vertical readout configuration.
        The sensor is 2D: the horizontal axis is wavelength, the vertical axis is position along the
        spectrograph entrance slit. Reading a single row therefore only samples one height in the slit
        and discards the signal collected on every other row.
        set_binned_roi() sums rows ON CHIP (charge is summed before the readout amplifier), so the read
        noise is paid once instead of once per row. That is what makes weak signals usable.
        Defaults come from hardware_params so each setup can record its own alignment. """
        self.roi_y0 = int(self.hardware_params.get('roi_y0', 0))
        self.roi_height = int(self.hardware_params.get('roi_height', self.sensor_height))
        self.roi_binning = int(self.hardware_params.get('roi_binning', self.roi_height))
        self.set_roi(self.roi_y0, self.roi_height, self.roi_binning, restart=False)

        # initialize camera
        self.worker = CameraWorker(self.camera,self.int_time)
        self.worker.sendSpectrum.connect(self.update_spectrum) # connect where signals of worker go to.
        self.worker.sendTemperature.connect(self.update_temperature)
        self.worker.start()

        # set int time once
        self.camera.set_attribute_value("Exposure Time", float(self.int_time))

    def set_parameter(self, parameter, value):
        """REQUIRED. This function defines how changes in the parameter tree are handled.
        In devices with workers, a pause of continuous acquisition might be required. """
        if parameter == 'int_time':
            self.parameter_dict['int_time'] = value
            self.worker.int_time = value
            if self.worker.acquiring: # stops acquisition before changing int time if currently acquiring.
                self.stop_acquisition()
                self.camera.set_attribute_value("Exposure Time", float(value))
                self.start_acquisition()
            else:
                self.camera.set_attribute_value("Exposure Time", float(value))
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
        self.calculate_wavelength_array()
        return self.wavelengths

    def calculate_wavelength_array(self):
        """
        Calculate the wavelength array for a PIXIS camera on a spectrograph, using this camera's own
        hardware_params (set from config.yaml) plus the live grating readout from the attached
        monochromator.

        Returns:
            wavelengths: 1D numpy array of wavelengths (nm)
        """
        if self.monochromator is not None:
            self.center_wavelength,self.grating_lines_per_mm=self.monochromator.get_monochromator_parameters()
            pixel_size_mm =self.hardware_params['pixel_size_mm']
            focal_length_mm = self.hardware_params['focal_length_mm']
            num_pixels = self.hardware_params['num_pixels']

        if self.hardware_params['calibrated']:

            pixel_size_mm = 26 / 1E3  # specs of PIXIS
            focal_length_mm = 300  # specs of SP2300
            num_pixels = 1024  # specs of PIXIS

            wl_center = self.center_wavelength
            m_order = 1
            px = self.px0

            # calibration from notebook
            f=self.hardware_params['f']
            delta=self.hardware_params['delta']
            gamma=self.hardware_params['gamma']
            n0=self.hardware_params['n0']
            offset_adjust=self.hardware_params['offset_adjust']
            d_grating=self.hardware_params['d_grating']
            x_pixel=self.hardware_params['x_pixel']
            curvature=self.hardware_params['curvature']

            n = px - (n0 + offset_adjust * wl_center)

            psi = np.arcsin(m_order * wl_center / (2 * d_grating * np.cos(gamma / 2)))
            eta = np.arctan(n * x_pixel * np.cos(delta) / (f + n * x_pixel * np.sin(delta)))

            self.wavelengths = ((d_grating / m_order) * (np.sin(psi - 0.5 * gamma) + np.sin(psi + 0.5 * gamma + eta))) + curvature * n ** 2
        else:
            pixel_size_mm = 26 / 1E3  # specs of PIXIS
            focal_length_mm = 300  # specs of SP2150
            num_pixels = 1024  # specs of PIXIS

            # Calculate linear dispersion (nm/mm)
            dispersion = 1e6 / (focal_length_mm * self.grating_lines_per_mm)

            # Center pixel
            center_pixel = num_pixels // 2

            # Pixel index array
            pixel_indices = np.arange(num_pixels)

            # Wavelength at each pixel
            self.wavelengths = self.center_wavelength + (pixel_indices - center_pixel) * dispersion * pixel_size_mm

    def attach_to_monochromator(self,monochromator):
        """
            Attaches the camera to a monochromator, letting the camera interface know where to get the monochromator parameters from.
            Only the live grating readout is pulled from the monochromator (via calculate_wavelength_array
            -> get_monochromator_parameters). The optical calibration constants stay in this camera's own
            hardware_params, so this driver has no dependency on which monochromator it happens to be
            paired with and can be reused on a different detection path unchanged.
            input:
                - monochromator (Monochromator QThread): The interface to the monochromator
        """
        self.monochromator=monochromator
        self.type='Spectrometer'

    def set_roi(self, y0, height, binning=None, restart=True):
        """
            Sets the vertical region of the sensor that is read out, and how many of its rows are
            summed on chip.
            input:
                - y0 (int): index of the first sensor row to read
                - height (int): number of sensor rows covered by the region
                - binning (int, default None): number of rows summed on chip. None means sum the whole
                  region into a single row (the high signal-to-noise mode used for measurements).
                  Pass 1 to keep every row separate (the 2D mode used for alignment).
                - restart (bool, default True): restart continuous acquisition if it was running
            output:
                - dict: the region of interest actually applied
        """
        y0 = int(np.clip(y0, 0, max(self.sensor_height - 1, 0)))
        height = int(np.clip(height, 1, self.sensor_height - y0))
        binning = height if binning is None else int(np.clip(binning, 1, height))
        # PICam requires the region height to be an exact multiple of the binning factor
        height = max((height // binning) * binning, binning)

        """ Held for the whole sequence: stopping, reconfiguring and restarting must not interleave
        with the measurement thread starting its own acquisition. """
        with self.camera_lock:
            was_acquiring = getattr(self, 'worker', None) is not None and self.worker.acquiring
            if was_acquiring:
                self.stop_acquisition()

            roi = {"x": 0, "width": 1024, "x_binning": 1,
                   "y": y0, "height": height, "y_binning": binning}
            self.camera.set_attribute_value("ROIs", [roi])
            self.roi_y0, self.roi_height, self.roi_binning = y0, height, binning
            print(f'Pixis ROI: rows {y0}-{y0 + height - 1} of {self.sensor_height}, '
                  f'binning {binning} -> {height // binning} row(s) read out')

            if was_acquiring and restart:
                self.start_acquisition()
        return roi

    def set_binned_roi(self, y0, height):
        """
            Measurement mode: sum `height` sensor rows starting at `y0` into a single row on chip.
            input:
                - y0 (int): index of the first sensor row of the signal
                - height (int): number of rows the signal spans
        """
        return self.set_roi(y0, height, binning=height)

    def set_full_frame(self):
        """
            Alignment mode: read every sensor row separately, giving the full 2D image.
            Slower and noisier per row, but shows where the signal actually sits on the slit.
        """
        return self.set_roi(0, self.sensor_height, binning=1)

    def get_roi(self):
        """
            Returns the currently applied vertical readout configuration.
            output:
                - tuple (y0, height, binning)
        """
        return self.roi_y0, self.roi_height, self.roi_binning

    def acquisition_running(self):
        """
            Whether the camera itself considers an acquisition to be running. Falls back to the
            worker flag if the driver does not expose the query.
        """
        try:
            return bool(self.camera.acquisition_in_progress())
        except Exception:
            # set_roi() runs once before the worker exists, hence the nested getattr.
            return bool(getattr(getattr(self, 'worker', None), 'acquiring', False))

    def start_acquisition(self):
        """
            Sets camera to continuous acquisition mode.
            Idempotent and serialised: PICam raises AcquisitionInProgress when asked to start while
            it is already running. That happened whenever a readout region was applied during a live
            view, because set_roi() and get_intensities() drive the camera from two different threads.
        """
        with self.camera_lock:
            """ If the camera reports an acquisition while the worker was not reading, the two are
            out of step: that acquisition was set up under the previous readout region and delivers
            nothing here. Stop it and start again rather than adopting it, which is what left
            get_intensities() waiting for a frame that never came after a region change. """
            if self.acquisition_running() and not self.worker.acquiring:
                self.camera.stop_acquisition()
            if not self.acquisition_running():
                self.camera.start_acquisition()
            self.worker.acquiring = True

    def stop_acquisition(self):
        """
            Disable continuous acquisition mode of camera.
        """
        with self.camera_lock:
            self.worker.acquiring = False
            if self.acquisition_running():
                self.camera.stop_acquisition()

    def wait_for_frame(self):
        """
            Blocks until the worker delivers the next frame, and returns it.
            The wait used to be an unbounded `while not self.new_spectrum`, so a readout region
            applied mid-acquisition, or a camera that simply stopped delivering, hung the measurement
            thread with no way back. The allowance is ten exposures plus five seconds, which is
            generous next to the 150 ms the camera normally needs.
            output:
                - np.ndarray: the frame received
        """
        allowance = max(self.int_time / 1000.0, 0.1) * 10 + 5
        deadline = time.time() + allowance
        while not self.new_spectrum:
            if time.time() > deadline:
                raise TimeoutError('Pixis delivered no frame within %.1f s (exposure %s ms)'
                                   % (allowance, self.int_time))
            time.sleep(0.01)
        frame = self.spectrum
        self.new_spectrum = False
        return frame

    def get_intensities(self):
        """ Gets the intensity. The example include the possibility of averaging several spectra and to
        perform a binning. Such functionalities might also be given by the camera.
        This function will be accessible from MeasurementClasses."""
        self.start_acquisition()
        """ Drop anything the worker delivered before this call. A frame can arrive just after the
        previous acquisition was stopped, and it was taken with the readout region in force then:
        consuming it here would return the old region's data for the new one. """
        self.new_spectrum = False
        try:
            if self.avg_scan == 1:
                spectrum = self.wait_for_frame()
            else:
                spectrum = self.image
                for i in range(self.avg_scan):
                    time.sleep(self.int_time / 1000 + 0.01)
                    spectrum = spectrum + self.wait_for_frame()
                spectrum = spectrum / self.avg_scan
        finally:
            self.stop_acquisition()
        """ The camera returns one row per binning group: a single row in binned (measurement) mode,
        every sensor row in full frame (alignment) mode. Any remaining rows are summed here so both
        modes hand back a 1D spectrum. Counts therefore scale with the number of rows summed, which
        matters when comparing a spectrum to a background taken with a different region. """
        spectrum = np.asarray(spectrum)
        if spectrum.ndim > 1:
            spectrum = spectrum.sum(axis=0)
        return spectrum

    def update_temperature(self, temperature):
        self.parameter_dict['sensor_T'] = temperature
        self.parameter_display_dict['sensor_T']['val'] = temperature


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
        self.spec_length = 1024
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
                """ read_newest_image() returns None when nothing arrived before the deadline above.
                Emitting that raised TypeError, which was caught and reported as "Spectrum not sent
                from Worker" -- a message that named neither the cause nor the camera state. """
                if isinstance(image, np.ndarray):
                    self.sendSpectrum.emit(image, self.int_time)
                else:
                    print('Pixis: no frame within %.2f s (exposure %s ms). Is the acquisition running?'
                          % (self.int_time / 1E3 + 0.5, self.int_time))
            else:
                time.sleep(1)
            temperature = self.camera.get_attribute_value("Sensor Temperature Reading")
            self.sendTemperature.emit(temperature)
        print('Worker closes')
        return
