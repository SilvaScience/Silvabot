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
import os
from harvesters.core import Harvester
from collections import defaultdict
from PyQt5 import QtCore, QtWidgets
from pylablib.devices import PrincetonInstruments
import time
from scipy.optimize import curve_fit
import serial
from joblib import Parallel, delayed
import matplotlib.pyplot as plt
import re
import h5py
from scipy.optimize import minimize

class Heliotis(QtCore.QThread):

    name = 'Heliotis'

    request_file = QtCore.pyqtSignal()

    def __init__(self):
        super(Heliotis, self).__init__()

        #self.camera.start()
        self.wavelength =  np.linspace(200,1000,512) # get property from Worker
        self.px0 = np.linspace(1,512,512)
        self.spec_length = (542,512) # # pixis length is (xx, 542, 512), xx is acquired frames
        self.image = np.zeros(self.spec_length)

        # Parameters. Defines parameters that are required for by the interface
        self.binned_spec = np.zeros(self.spec_length)
        self.new_spectrum = False

        # set up spectrograph
        self.serial_busy = False
        port = 'COM10'
        self.ser = serial.Serial(port=port, baudrate=9600, bytesize=8, parity='N',
                                 stopbits=1, xonxoff=0, rtscts=0, timeout=0.02)
        # get startup values
        self.grating = float(self.write_command('?GRATING')[0])
        numbers = self.write_command('?GRATINGS')
        print('Gratings:',numbers)
        self.num_gratings = int((len(numbers)-8)/2)
        self.grating_densities = np.zeros(self.num_gratings)
        self.grating_blazes = np.zeros(self.num_gratings)
        for i in range(self.num_gratings):
            self.grating_densities[i] = numbers[i*3 + 1]
            self.grating_blazes[i] = numbers[i * 3 + 2]
        self.center_wl = float(self.write_command('?NM')[0])
        print(f"Current wl: {float(self.write_command('?NM')[0])}" )
        self.num_gratings = 3
        self.grating_densities = [1, 1200, 600]
        self.grating_blazes =[1, 500, 500]
        print(self.center_wl)
        print(self.grating_densities)
        print(self.grating_blazes)
        print(self.grating)

        #initial heliotis settings
        self.num_frames = 100
        self.take_average = False
        self.sensitivity = 1
        self.N_Periods = 100 #95
        self.ref_freq =  1000 # 29790  # # 71531.2#26662#53325

        # set parameter dict
        self.parameter_dict = defaultdict()
        """ Set up the parameter dict. 
        Here, all properties of parameters to be handled by the parameter dict are defined."""
        self.parameter_display_dict = defaultdict(dict)
        self.parameter_display_dict['num_frames']['val'] = self.num_frames
        self.parameter_display_dict['num_frames']['unit'] = ' frames'
        self.parameter_display_dict['num_frames']['max'] = 10000
        self.parameter_display_dict['num_frames']['read'] = False
        self.parameter_display_dict['center_wl']['val'] = self.center_wl
        self.parameter_display_dict['center_wl']['unit'] = ' nm'
        self.parameter_display_dict['center_wl']['max'] = 2000
        self.parameter_display_dict['center_wl']['read'] = False
        self.parameter_display_dict['grating']['val'] = self.grating
        self.parameter_display_dict['grating']['unit'] = ' grat'
        self.parameter_display_dict['grating']['max'] = 3
        self.parameter_display_dict['grating']['read'] = False
        self.parameter_display_dict['take_average']['val'] = 0
        self.parameter_display_dict['take_average']['unit'] = ' per'
        self.parameter_display_dict['take_average']['max'] = 100
        self.parameter_display_dict['take_average']['read'] = False
        self.parameter_display_dict['sensitivity']['val'] = self.sensitivity
        self.parameter_display_dict['sensitivity']['unit'] = ' '
        self.parameter_display_dict['sensitivity']['max'] = 1
        self.parameter_display_dict['sensitivity']['read'] = False
        self.parameter_display_dict['N_Periods']['val'] = self.N_Periods
        self.parameter_display_dict['N_Periods']['unit'] = ' '
        self.parameter_display_dict['N_Periods']['max'] = 100
        self.parameter_display_dict['N_Periods']['read'] = False
        self.parameter_display_dict['ref_freq']['val'] = self.ref_freq
        self.parameter_display_dict['ref_freq']['unit'] = ' Hz'
        self.parameter_display_dict['ref_freq']['max'] = 150000 # 44700 29796
        self.parameter_display_dict['ref_freq']['read'] = False

        # set up parameter dict that only contains value. (faster to access)
        self.parameter_dict = {}
        for key in self.parameter_display_dict.keys():
            self.parameter_dict[key] = self.parameter_display_dict[key]['val']

        # initialize camera interface
        print('Initialize Heliotis')
        h = Harvester()
        # read heliotis *.CTI path from environment variable
        ctiFile = os.environ['DIAPHUS_GENTL64_FILE']
        print(ctiFile)
        h.add_file(ctiFile)
        #"""  De-comment to run without camera
        # create camera object for interaction
        self.camera = self.selectDevice(h)

        # configure camera
        self.cameraConfig()
        print('Heliotis initialized')

        # initialize camera
        #self.worker = CameraWorker(self.camera)
        #self.worker.sendSpectrum.connect(self.update_spectrum) # connect where signals of worker go to.
        #self.worker.start()
        self.thread = QtCore.QThread()
        self.worker = CameraWorker(self.camera)
        self.worker.moveToThread(self.thread)
        self.worker.sendSpectrum.connect(self.update_spectrum)
        #self.thread.started.connect(self.worker.run)
        #self.thread.start()
        #"""
        self.correct_bg_checkbox = False
        self.ref_filename = None

        self.device_setting_function = dict()
        self.device_setting_function['load_bg'] = ('Action',self.load_bg)
        self.device_setting_function['correct_bg'] = ('Checkbox', self.correct_bg_checkbox_toggle)

    def correct_bg_checkbox_toggle(self, checked):
        self.correct_bg_checkbox = checked
        self.worker.correct_bg_checkbox = checked

    def load_bg(self):
        self.request_file.emit()
        print(f'Loading background image {self.ref_filename}')
        self.worker.change_background(self.ref_filename)

    def set_parameter(self, parameter, value):
        """REQUIRED. This function defines how changes in the parameter tree are handled.
        In devices with workers, a pause of continuous acquisition might be required. """
        if parameter == 'center_wl':
            cmd = f'{value:0.3f} GOTO'
            self.write_command(cmd)
            self.parameter_dict['center_wl'] = value
            self.center_wl = value
        elif parameter == 'grating':
            cmd = f'{value:1.0f} GRATING'
            self.write_command(cmd)
            self.parameter_dict['grating'] = value
            self.grating = value
        elif parameter == 'num_frames':
            self.parameter_dict['num_frames'] = value
            self.num_frames = int(value)
            self.worker.acquiring = False
            time.sleep(0.1)
            self.cameraConfig()
            time.sleep(0.1)
            self.worker.acquiring = True
        elif parameter == 'take_average':
            self.parameter_dict['take_average'] = value
            if value == 100:
                self.take_average = True
            else:
                self.take_average = False
        elif parameter == 'sensitivity':
            self.parameter_dict['sensitivity'] = value
            self.sensitivity = value
            self.worker.acquiring = False
            time.sleep(0.1)
            self.cameraConfig()
            time.sleep(0.1)
        elif parameter == 'N_Periods':
            self.parameter_dict['N_Periods'] = value
            self.N_Periods = int(value)
            self.worker.acquiring = False
            time.sleep(0.1)
            self.cameraConfig()
            time.sleep(0.1)
        elif parameter == 'ref_freq':
            self.parameter_dict['ref_freq'] = value
            self.ref_freq = int(value)
            self.worker.acquiring = False
            time.sleep(0.1)
            self.cameraConfig()
            time.sleep(0.1)

    def update_spectrum(self, spec):
        """REQUIRED. This is the slot function for the sendSpectrum pyqt.signal from the worker.
        It updates the last saved spectrum and changes the self.new_spectrum Boolean to True
        to allow to emit the treated signal from the spectrometer."""
        self.spectrum = spec
        self.new_spectrum = True


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
            pixel_size_mm = 24 / 1E3  # specs of Heliotis
            focal_length_mm = 203  # specs of Isoplane
            num_pixels = 512  # specs of Heliotis

            #

            wl_center = center_wavelength_nm
            m_order = 1
            px = self.px0

            # calibration from notebook
            if self.grating == 3:
                f, delta, gamma, n0, offset_adjust, d_grating, x_pixel, curvature = [np.float64(24739656.496170387), np.float64(4.763915731068521), np.float64(1.4300129817768625), np.float64(243.0), 0, 4926.108374384236, 24000.0, np.float64(-0.0001681610550643024)]
            elif self.grating == 2:
                f, delta, gamma, n0, offset_adjust, d_grating, x_pixel, curvature = [np.float64(1197096958.9926493), np.float64(-18.68106438263782), np.float64(-1.6871589585359328), np.float64(238.25), 0, 4926.108374384236, 24000.0, np.float64(-6.663483223202162e-06)]
            else:
                print('WARNING: GRATING NOT CALIBRATED. Use calib of grating3 ')
                f, delta, gamma, n0, offset_adjust, d_grating, x_pixel, curvature = [np.float64(24739656.496170387),
                                                                                     np.float64(4.763915731068521),
                                                                                     np.float64(1.4300129817768625),
                                                                                     np.float64(243.0), 0,
                                                                                     4926.108374384236, 24000.0,
                                                                                     np.float64(-0.0001681610550643024)]

            n = px - (n0 + offset_adjust * wl_center)

            # print('psi top', m_order* wl_center)
            # print('psi bottom', (2*d_grating*np.cos(gamma/2)) )

            psi = np.arcsin(m_order * wl_center / (2 * d_grating * np.cos(gamma / 2)))
            eta = np.arctan(n * x_pixel * np.cos(delta) / (f + n * x_pixel * np.sin(delta)))

            wavelengths = ((d_grating / m_order) * (np.sin(psi - 0.5 * gamma) + np.sin(psi + 0.5 * gamma + eta))) + curvature * n ** 2
        else:
            pixel_size_mm = 24 / 1E3  # specs of Heliotis
            focal_length_mm = 203  # specs of SP2150
            num_pixels = 512  # specs of Heliotis

            # Calculate linear dispersion (nm/mm)
            dispersion = 1e6 / (focal_length_mm * grating_lines_per_mm)

            # Center pixel
            center_pixel = num_pixels // 2

            # Pixel index array
            pixel_indices = np.arange(num_pixels)

            # Wavelength at each pixel
            wavelengths = center_wavelength_nm + (pixel_indices - center_pixel) * dispersion * pixel_size_mm
        self.wavelength = wavelengths
        return wavelengths

    def get_intensities(self):
        """ Gets the intensity. The example include the possibility of averaging several spectra and to
        perform a binning. Such functionalities might also be given by the camera.
        This function will be accessible from MeasurementClasses."""
        #if not self.worker.acquiring:
        spectrum = self.worker.run(self.take_average,self.wavelength) # self.wavelength needs to be removed in final version
        #else:
        #    print('Worker is busy')
        #    dummy_spectrum = np.zeros((self.num_frames,512,542))
        #    spectrum = dummy_spectrum
        return spectrum

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

    def selectDevice(self,h):
        """
        Scan for available devices and print device list
        let the user select one and open the connection to the device
        if just one device available, open it without user interaction
        \param h harvester object
        \return harvesters camera object
        """

        h.update()
        NDevices = len(h.device_info_list)
        print("{} device(s) detected on the Network:\n".format(NDevices))
        for i, dev in enumerate(h.device_info_list):
            print("{}) {} ({})".format(i + 1, dev.id_, dev.serial_number))

        if NDevices == 1:
            selectionInt = 1
        else:
            selectionStr = input("Select a device (0=exit): ")
            selectionInt = int(selectionStr)
            if ((selectionInt <= 0) or (selectionInt > NDevices)):
                exit('No device selected - exit script')

        deviceID = h.device_info_list[selectionInt - 1].id_
        print('selected device:', deviceID, '\n')
        return h.create(selectionInt - 1)

    def cameraConfig(self):
        """
        simple configuration example of heliCam C4 using internal reference
        \param camera harvesters camera object
        """

        # Experiment Parameters

        # Lock-In Amplification (LIA)

        # Sensor sensitivity in %/100, 0.5 for C4-S40, 0.2 for C4-S40U, 0.05 for C4-S41U and 0.25 for C4M
        sensitivity = self.sensitivity # 0.5
        # Number of intergration periods
        NPeriods = self.N_Periods #49
        # Background suppression on/off switch, 'AC' or 'DC'
        coupling = 'DC'
        # Reference frequency in Hz
        refFrequency = self.ref_freq # 44700.    #3150.    #real : 29796.0  framerate = refFrequency / NPeriods
        # Source of reference signal, 'Internal' or 'External'
        refSource = 'External' # 'External'
        # Expected frequency deviation of external reference input in %
        expFrequencyDev = 1
        # Number of frames to be recorded
        NFrames = self.num_frames

        # Illumination Driving Signal

        # Signal generator DC offset in % of full range
        sgnOffset = 50.0
        # Signal generator peak-to-peak amplitude in % of full range
        sgnAmplitude = 50.0
        # Signal generator frequency in Hz
        sgnFrequency = 29796.0

        # Configuration

        # Trigger

        self.camera.remote_device.node_map.TriggerSelector.value = "RecordingStart"
        self.camera.remote_device.node_map.TriggerMode.value = "Off"
        self.camera.remote_device.node_map.TriggerSelector.value = "FrameStart"
        self.camera.remote_device.node_map.TriggerMode.value = "On"
        self.camera.remote_device.node_map.TriggerSource.value = "Software"

        # LIA

        self.camera.remote_device.node_map.DeviceOperationMode.value = "LockInCam"
        self.camera.remote_device.node_map.Scan3dExtractionMethod.value = "rawIQ"

        self.camera.remote_device.node_map.LockInSensitivity.value = sensitivity
        self.camera.remote_device.node_map.LockInTargetTimeConstantNPeriods.value = NPeriods
        self.camera.remote_device.node_map.LockInCoupling.value = coupling
        self.camera.remote_device.node_map.LockInExpectedFrequencyDeviation.value = expFrequencyDev
        self.camera.remote_device.node_map.LockInTargetReferenceFrequency.value = refFrequency
        self.camera.remote_device.node_map.AcquisitionBurstFrameCount.value = NFrames

        self.camera.remote_device.node_map.LockInReferenceSourceType.value = refSource

        # For external reference signal only
        self.camera.remote_device.node_map.LockInReferenceFrequencyScaler.value = "Off" #"DivideBy8" # 8 #"DivideBy2"  # or "Off", "DivideBy2" etc
        self.camera.remote_device.node_map.LockInReferenceSourceSignal.value = "FI2"

        # Illumination

        #self.camera.remote_device.node_map.SignalGeneratorOffset.value = sgnOffset
        #self.camera.remote_device.node_map.SignalGeneratorAmplitude.value = sgnAmplitude
        #self.camera.remote_device.node_map.LightControllerSelector.value = "LightController0"
        #self.camera.remote_device.node_map.SignalGeneratorModulationMode.value = "On"
        #self.camera.remote_device.node_map.SignalGeneratorFrequency.value = sgnFrequency
        #self.camera.remote_device.node_map.LightControllerSource.value = "SignalGenerator"
        self.camera.remote_device.node_map.LightControllerSource.value = 'Off'

        # See ref. for troubleshooting
        #self.camera.remote_device.node_map.LineSelector.value = "RTIO3"
        #self.camera.remote_device.node_map.LineSource.value = "LockInReference"




class CameraWorker(QtCore.QThread):
    """ This is a DemoWorker for the spectrometer.
    It continously acquires spectra and emits them to the Interface.
    It interrupts data acquisition if an int_time change is requested. Its important because most
    hardware can only handle one command at a time, acquiring or changeing settings.  """
    # These are signals that allow to send data from a child thread to the parent hierarchy.
    sendSpectrum = QtCore.pyqtSignal(np.ndarray)
    sendTemperature = QtCore.pyqtSignal(float)

    def __init__(self,camera):
        super(CameraWorker, self).__init__() # Elevates this thread to be independent.

        # definition of some parameters
        self.camera = camera
        self.spec_length = (252,1024)
        self.change_int_time = False
        self.spectrum = np.zeros(self.spec_length)
        self.terminate = False
        self.paused = False
        self.processing = False
        self.acquiring = False
        self.correct_bg_checkbox = False
        self.background_I = np.zeros((542,512))
        self.background_Q = np.zeros((542,512))

    def run(self, take_average, wavelength):
        """" Continuous tasks of the Worker are defined here.
        If loops check for requested changes in settings prior each acquisition. """

        print(time.strftime("%H_%M_%S", time.localtime(time.time())) + ' Heliotis worker started')
        initial_time = time.time()
        frame_rate = self.camera.remote_device.node_map.FrameRate.value
        print('######### -->> framerate :', frame_rate)

        #if not self.acquiring:
        self.acquiring = True
        t0 = time.time()
        rawI, rawQ = self.acquire()
        print("Acquistion Duration:", time.time() - t0)
        if self.correct_bg_checkbox:
            twoD_avgI = rawI - self.background_I
            twoD_avgQ = rawQ - self.background_Q
        else:
            twoD_avgI = rawI -np.mean(rawI, axis=0)
            twoD_avgQ = rawQ -np.mean(rawQ, axis=0)
        amp = np.sqrt((twoD_avgI)**2 + (twoD_avgQ)**2)
        ty_res = time.localtime(time.time())
        timestamp = time.strftime("%H_%M_%S", ty_res)
        datestamp = time.strftime("20%y-%m-%d", ty_res)
        folder = os.path.join(r"D:\DATA\BIGFOOT",datestamp)
        save_every_spectrum = True
        if take_average:
            filename = os.path.join(folder,"avg_data" + timestamp + '.h5')
            if save_every_spectrum:
                with h5py.File(filename, 'w') as f:
                    #f.create_dataset('averaged_rawI', data=twoD_avgI)
                    #f.create_dataset('averaged_rawQ', data=twoD_avgQ)
                    f.create_dataset('averaged_rawI', data=np.mean(rawI, axis=0))
                    f.create_dataset('averaged_rawQ', data=np.mean(rawQ, axis=0))
                    f['averaged_rawI'].attrs["xaxis"] = wavelength
            print(time.strftime("%H_%M_%S", time.localtime(time.time())) + " Average data acquired")
        else:
            filename = os.path.join(folder,"raw_data" + timestamp + '.h5')
            if save_every_spectrum:
                with h5py.File(filename, 'w') as f:
                    f.create_dataset('rawI', data=rawI)
                    f.create_dataset('rawQ', data=rawQ)
                    f['rawI'].attrs["xaxis"] = wavelength
            print(timestamp + " Raw data acquired")
        self.acquiring = False
        print('Worker closes')
        print()
        return np.mean(amp, axis=0)

    def change_background(self,filename):
        with h5py.File(os.path.join(filename), 'r') as f:
            self.background_I = f['averaged_rawI'][()]
            self.background_Q = f['averaged_rawQ'][()]

    def acquire(self, timeout=10000):
        """
        Initiate a measurement and retrieve lock-in data.
        \param h harvester object
        \param t float
        \return numpy array [IRaw,QRaw]
        """

        outputShape = self.getOutputShape()

        self.camera.start()
        self.camera.remote_device.node_map.TriggerSelector.value = 'FrameStart'
        self.camera.remote_device.node_map.TriggerSoftware.execute()

        with self.camera.fetch(timeout=timeout) as buffer:
            data = np.array([img.data % 2 ** 15 // 4 for img in buffer.payload.components]).reshape(outputShape)

        self.camera.stop()

        return data

    def getOutputShape(self):
        """
        Get shape of measurement's in-phase/quadrature lock-in output.
        \param h harvester object
        \return tuple (NChannels,Nframes,height,width)
        """
        NFrames = self.camera.remote_device.node_map.AcquisitionBurstFrameCount.value
        height = self.camera.remote_device.node_map.Height.value
        width = self.camera.remote_device.node_map.Width.value

        return 2, NFrames, height, width

    def pause(self):
        self.paused = True

    def resume(self):
        self.paused = False