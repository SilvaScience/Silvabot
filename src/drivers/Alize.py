# -*- coding: utf-8 -*-
"""
Created on Mon Apr  28 15:09:53 2025

@author: David Tiede
Hardware class to control the Alize camera. All hardware classes require a definition of
parameter_display_dict (set Spinbox options and read/write)
set_parameter function (assign set functions)

REQUIREMENTS:
Needs PeCamera-SDK-4.14.0 to be installed as a python package. This package is only available locally. It is stored on
the TRUENAS server.

NOTE:
Currently still in testing
- Flatfield correction is currently fixed to HIGHGAIN, 5s integration time. Consider adapting it dynamically, if needed.

"""

import numpy as np
from PyQt5 import QtCore
from collections import defaultdict
from pylablib.devices import PrincetonInstruments
import time
import serial
import re
import pecamerapy
import os
from multiprocessing import Process, Queue

def camera_worker(cmd_q, res_q):
    # Function to initialize the camera worker. It needs to be implemented globally
    # (not within a class) as multiprocessing needs to pickle the worker around.
    w = CameraWorker(cmd_q, res_q)
    w.run()

class Alize(QtCore.QThread):

    name = 'Alize'
    
    def __init__(self):
        super(Alize, self).__init__()

        #self.camera.start()
        self.wavelength =  np.linspace(200,1000,640) # get property from Worker
        self.px0 = np.linspace(1,640,640)
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

        # set up spectrograph

        self.serial_busy = False
        port = 'COM12'
        self.ser = serial.Serial(port=port, baudrate=9600, bytesize=8, parity='N',
                                 stopbits=1, xonxoff=0, rtscts=0, timeout=2)
        # get startup values
        self.grating = float(self.write_command('?GRATING')[0])
        numbers = self.write_command('?GRATINGS')
        numbers = ['1', '600', '1200', '2', '300', '1200', '3', '4', '5', '6', '7', '8'] # HARDED QUICK FIX as communication with SP2150 does not yield grating information.
        # This communication issue might be related to high COM port number (maybe it has a different cause).
        self.num_gratings = int((len(numbers)-8)/2)
        self.grating_densities = np.zeros(self.num_gratings)
        self.grating_blazes = np.zeros(self.num_gratings)
        for i in range(self.num_gratings):
            self.grating_densities[i] = numbers[i*3 + 1]
            self.grating_blazes[i] = numbers[i * 3 + 2]
        self.center_wl = float(self.write_command('?NM')[0])
        print('SP2150 grating info: ', numbers)
        print('SP2150 grating densities: ',self.grating_densities)
        print('SP2150 grating blazes: ',self.grating_blazes)
        print('SP2150 selected grating: ',self.grating)

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
        self.parameter_display_dict['center_wl']['val'] = self.center_wl
        self.parameter_display_dict['center_wl']['unit'] = ' nm'
        self.parameter_display_dict['center_wl']['max'] = 2000
        self.parameter_display_dict['center_wl']['read'] = False
        self.parameter_display_dict['grating']['val'] = self.grating
        self.parameter_display_dict['grating']['unit'] = ' grat'
        self.parameter_display_dict['grating']['max'] = 3
        self.parameter_display_dict['grating']['read'] = False

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
        elif parameter == 'center_wl':
            cmd = f'{value:0.3f} GOTO'
            self.write_command(cmd)
            self.parameter_dict['center_wl'] = value
            self.center_wl = value
        elif parameter == 'grating':
            cmd = f'{value:1.0f} GRATING'
            self.write_command(cmd)
            self.parameter_dict['grating'] = value
            self.grating = value

    def get_wavelength(self):
        """This simply returns the wavelength. In Colbert this needs to be adapted if the calibration
         changes. This function will be accessible from MeasurementClasses. """
        return self.calculate_wavelength_array(self.center_wl,self.grating_densities[int(self.grating-1)])

    def calculate_wavelength_array(self,center_wavelength_nm,grating_lines_per_mm):
        """
        Calculate the wavelength array for a PIXIS camera on SP-2150 spectrograph.

        Parameters:
            center_wavelength_nm: Central wavelength (nm)
            grating_lines_per_mm: Groove density (lines/mm)

        Returns:
            wavelengths: 1D numpy array of wavelengths (nm)
        """
        calibrated = True
        if calibrated:
            pixel_size_mm = 15 / 1E3  # specs of Alize
            focal_length_mm = 150  # specs of SP2150
            num_pixels = 640  # specs of Alize

            #

            wl_center = center_wavelength_nm
            m_order = 1
            px = self.px0

            # calibration from notebook
            if self.grating == 1:
                f, delta, gamma, n0, offset_adjust, d_grating, x_pixel, curvature = [np.float64(382456483.7755453),
                                                                                     np.float64(6.3514446357904335),
                                                                                     np.float64(1.9092120540448625),
                                                                                     np.float64(273.6666666666667), 0,
                                                                                     6666.666666666667, 15000.0,
                                                                                     np.float64(1.1640095515828127e-06)]
            else:
                # WARNING, NOT CALIBRATED YET, dummy values from grating 1
                f, delta, gamma, n0, offset_adjust, d_grating, x_pixel, curvature = [np.float64(382456483.7755453),
                                                                                     np.float64(6.3514446357904335),
                                                                                     np.float64(1.9092120540448625),
                                                                                     np.float64(273.6666666666667), 0,
                                                                                     6666.666666666667, 15000.0,
                                                                                     np.float64(1.1640095515828127e-06)]
                print('WARNING: grating 2 is not calibrated! CALIBRATE PRIOR USAGE!')


            n = px - (n0 + offset_adjust * wl_center)

            # print('psi top', m_order* wl_center)
            # print('psi bottom', (2*d_grating*np.cos(gamma/2)) )

            psi = np.arcsin(m_order * wl_center / (2 * d_grating * np.cos(gamma / 2)))
            eta = np.arctan(n * x_pixel * np.cos(delta) / (f + n * x_pixel * np.sin(delta)))

            wavelengths = ((d_grating / m_order) * (np.sin(psi - 0.5 * gamma) + np.sin(psi + 0.5 * gamma + eta))) + curvature * n ** 2
        else:
            pixel_size_mm = 15 / 1E3  # specs of Alize
            focal_length_mm = 150  # specs of SP2150
            num_pixels = 640  # specs of Alize

            # Calculate linear dispersion (nm/mm)
            dispersion = 1e6 / (focal_length_mm * grating_lines_per_mm)

            # Center pixel
            center_pixel = num_pixels // 2

            # Pixel index array
            pixel_indices = np.arange(num_pixels)

            # Wavelength at each pixel
            wavelengths = center_wavelength_nm + (pixel_indices - center_pixel) * dispersion * pixel_size_mm

        return wavelengths

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