# -*- coding: utf-8 -*-
"""
Created on Mon Apr  28 15:09:53 2025

@author: David Tiede
Hardware class for the Alize camera alone. It has no notion of a monochromator and no optical
calibration -- drivers.Spectrograph pairs it with one and owns the wavelength axis. All hardware
classes require a definition of parameter_display_dict (set Spinbox options and read/write) and
set_parameter.

REQUIREMENTS:
Needs PeCamera-SDK-4.14.0 to be installed as a python package. This package is only available
locally. It is stored on the TRUENAS server.

NOTE:
Currently still in testing
- Flatfield correction is currently fixed to HIGHGAIN, 5s integration time. Consider adapting it
  dynamically, if needed.
"""

import numpy as np
from PyQt5 import QtCore
from collections import defaultdict
from pylablib.devices import PrincetonInstruments
import time
import pecamerapy
import os
from multiprocessing import Process, Queue

def camera_worker(cmd_q, res_q):
    # Function to initialize the camera worker. It needs to be implemented globally
    # (not within a class) as multiprocessing needs to pickle the worker around.
    w = CameraWorker(cmd_q, res_q)
    w.run()

class AlizeCamera(QtCore.QThread):

    name = 'Alize'
    caps = frozenset({'acquisition'})
    
    def __init__(self):
        super(AlizeCamera, self).__init__()

        self.spec_length = (512, 640) # get property from Worker
        self.spectrum = np.zeros(self.spec_length)
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
        self.parameter_display_dict['int_time']['max'] = 200000
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

        # initialize camera
        self.cmd_q = Queue()
        self.res_q = Queue()

        self.worker = Process(
            target=camera_worker,
            args=(self.cmd_q, self.res_q),
            daemon=True
        )
        self.worker.start()


    def set_parameter(self, parameter, value):
        """REQUIRED. This function defines how changes in the parameter tree are handled.
        In devices with workers, a pause of continuous acquisition might be required. """
        if parameter == 'int_time':
            self.parameter_dict['int_time'] = value
            self.int_time = value
            self.cmd_q.put({
                "type": "change_int_time",
                "parameter_list": [self.int_time]
            })
        elif parameter == 'avg_scan':
            self.parameter_dict['avg_scan'] = value
            self.avg_scan = int(value)

    def start_acquisition(self):
        """ Sets camera to continuous acquisition mode. """
        #self.camera.start_acquisition()
        #self.worker.acquiring = True

    def stop_acquisition(self):
        """ Disable continuous acquisition mode of camera. """
        #self.worker.acquiring = False
        #self.camera.stop_acquisition()

    def get_intensities(self):
        """ Gets the intensity. The example include the possibility of averaging several spectra and to
        perform a binning. Such functionalities might also be given by the camera.
        This function will be accessible from MeasurementClasses."""
        self.new_spectrum = False
        self.cmd_q.put({"type": "acquire","averages": self.avg_scan})
        while self.res_q.empty():
            time.sleep(0.01)
        self.spectrum,self.parameter_dict['sensor_T'] = self.res_q.get()
        self.new_spectrum = True
        print(time.strftime("%H:%M:%S", time.localtime(time.time())) + ' Spectrum acquired')
        return self.spectrum

    def close_device(self):
        self.cmd_q.put({"type": "STOP"})
        self.worker.join()

class CameraWorker(QtCore.QThread):
    """ This is a DemoWorker for the spectrometer.
    It continously acquires spectra and emits them to the Interface.
    It interrupts data acquisition if an int_time change is requested. Its important because most
    hardware can only handle one command at a time, acquiring or changeing settings.  """


    def __init__(self,command_queue,result_queue):
        super(CameraWorker, self).__init__() # Elevates this thread to be independent.

        # definition of some parameters
        self.spec_length = (512, 640)
        self.change_int_time = False
        self.spectrum = np.zeros(self.spec_length)
        self.int_time = 100
        self.binning = 2
        self.terminate = False
        self.acquiring = False
        self.num_frames = 1
        #
        self.cmd_q = command_queue
        self.res_q = result_queue
        self.running = True

        # Initialize camera
        self.cam = pecamerapy.Camera()

        # Choose the desired connection mode
        mode = pecamerapy.OpenMode.USB3
        # Find index, serial
        index = -1
        try:
            index, serial_num = self.cam.find_first(mode)
        except Exception as e:
            print(f"Error during connection: {e}")
            exit(-1)

        # Open the connection to Alize
        # index = 11
        try:
            self.cam.open(index, mode)
        except pecamerapy.CommOpenError as e:
            print(f"Error during opening: {e}")
            exit(-1)

        # Test Getter/Setter
        my_mode = self.cam.get_trigger_mode()  # should be TRIGGER_NONE (or other specified mode)
        self.cam.set_trigger_mode(my_mode)  # set initial mode

        # set flatfield correction
        cwd = os.getcwd()
        calib_file_path = os.path.join(cwd,'calibrations','Alize_CA000010991',"3 HighGain 5.0.bin")
        if not os.path.exists(calib_file_path):
            raise FileNotFoundError(f"Alize Calibration file not found: '{calib_file_path}'. Check file path and try again.")

        #FLATFIELD_PATH = Path(__file__).parent / "3 HighGain 5.0.bin"

        size_img = self.cam.get_detector_size()
        width, height = size_img[0], size_img[1]

        # Read the flatfield .bin file
        length = width * height
        length_bytes = int(length * 32 / 8)
        nuc_gain = np.fromfile(calib_file_path, dtype=np.float32, count=length)
        nuc_gain = np.reshape(nuc_gain, size_img)
        nuc_offset = np.fromfile(calib_file_path, dtype=np.float32, count=length, offset=length_bytes)
        nuc_offset = np.reshape(nuc_offset, size_img)
        nuc_bp = np.fromfile(calib_file_path, dtype=np.uint32, count=length, offset=2 * length_bytes)

        # Set the flatfield and pixel replacement
        self.cam.set_flatfield(gain=nuc_gain, offset=nuc_offset, width=width, height=height)
        self.cam.set_pixel_replacement(map=nuc_bp, width=width, height=height)

        # Enable the flatfield and pixel replacement
        self.cam.set_flatfield_enabled(True)
        self.cam.set_pixel_replacement_enabled(True)

        # Set integration time to 100ms
        self.cam.set_exposure_time(0.1)

    def acquire(self):
        self.cam.capture(self.num_frames,self.num_frames)
        if self.num_frames >1:
            self.spectrum = np.zeros(self.spec_length)
            for i in range(self.num_frames):
                img, metadata = self.cam.get_image(timeout_sec=210)
                self.spectrum += img
            img = self.spectrum / self.num_frames
        else:
            img, metadata = self.cam.get_image(timeout_sec=210)
        self.res_q.put((np.fliplr(img),self.temperature)) #flip image as camera is mounted upside down.
        #self.sendSpectrum.emit() #flip image as camera is mounted upside down.

    def run(self):
        print(time.strftime("%H_%M_%S", time.localtime(time.time())) + ' Alize worker started')
        while self.running:
            self.temperature = self.cam.get_temperature()
            try:
                cmd = self.cmd_q.get(timeout=0.1)
            except Exception:
                continue

            if cmd["type"] == "STOP":
                self.cam.abort()
                self.cam.close()
                print('Alize camera closed properly')
                self.running = False
                break

            if cmd["type"] == "change_int_time":
                self.int_time = cmd["parameter_list"][0]
                new_int_time = self.int_time / 1E3
                self.cam.set_exposure_time(new_int_time)

            if cmd["type"] == "acquire":
                self.num_frames = cmd["averages"]
                self.acquire()