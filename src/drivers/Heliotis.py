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
from packaging.version import parse
from PyQt5 import QtCore
from collections import defaultdict
from pylablib.devices import PrincetonInstruments
import time
import serial
import re

class Heliotis(QtCore.QThread):

    name = 'Heliotis'

    def __init__(self):
        super(Heliotis, self).__init__()

        #self.camera.start()
        self.wavelength =  np.linspace(200,1000,542) # get property from Worker
        self.px0 = np.linspace(1,1024,542)
        self.spec_length = (542,512) # # pixis length is (xx, 542, 512), xx is acquired frames
        self.image = np.zeros(self.spec_length)

        # Parameters. Defines parameters that are required for by the interface
        self.binned_spec = np.zeros(self.spec_length)
        self.new_spectrum = False

        # set up spectrograph
        self.serial_busy = False
        port = 'COM7'
        self.ser = serial.Serial(port=port, baudrate=9600, bytesize=8, parity='N',
                                 stopbits=1, xonxoff=0, rtscts=0, timeout=0.02)
        # get startup values
        self.grating = float(self.write_command('?GRATING')[0])
        numbers = self.write_command('?GRATINGS')
        print(numbers)
        self.num_gratings = int((len(numbers)-8)/2)
        self.grating_densities = np.zeros(self.num_gratings)
        self.grating_blazes = np.zeros(self.num_gratings)
        for i in range(self.num_gratings):
            self.grating_densities[i] = numbers[i*3 + 1]
            self.grating_blazes[i] = numbers[i * 3 + 2]
        self.center_wl = float(self.write_command('?NM')[0])
        self.num_gratings = 3
        self.grating_densities = [1, 1200, 600]
        self.grating_blazes =[1, 500, 500]
        print(self.center_wl)
        print(self.grating_densities)
        print(self.grating_blazes)
        print(self.grating)

        #initial heliotis settings
        self.num_frames = 40

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

        # create camera object for interaction
        self.camera = self.selectDevice(h)

        # configure camera
        self.cameraConfig()
        print('Heliotis initialized')

        # initialize camera
        self.worker = CameraWorker(self.camera)
        self.worker.sendSpectrum.connect(self.update_spectrum) # connect where signals of worker go to.
        self.worker.start()

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
            time.sleep(2)
            self.cameraConfig()
            time.sleep(2)
            self.worker.acquiring = True



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
        calibrated = False
        if calibrated:
            pixel_size_mm = 24 / 1E3  # specs of Heliotis
            focal_length_mm = 203  # specs of SP2150
            num_pixels = 512  # specs of Heliotis

            #

            wl_center = center_wavelength_nm
            m_order = 1
            px = self.px0

            # calibration from notebook
            f, delta, gamma, n0, offset_adjust, d_grating, x_pixel, curvature = [np.float64(330605663.74965495), np.float64(-0.20488367116307532), np.float64(2.021864300924973), np.float64(508.0), 0, 6666.666666666667, 26000.0, np.float64(3.1224154313329654e-06)]



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

        return wavelengths

    def get_intensities(self):
        """ Gets the intensity. The example include the possibility of averaging several spectra and to
        perform a binning. Such functionalities might also be given by the camera.
        This function will be accessible from MeasurementClasses."""
        while not self.new_spectrum:
            time.sleep(0.01)
        spectrum = self.spectrum
        self.new_spectrum = False

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
        sensitivity = 1
        # Number of intergration periods
        NPeriods = 10
        # Background suppression on/off switch, 'AC' or 'DC'
        coupling = 'AC'
        # Reference frequency in Hz
        refFrequency = 10000.0
        # Source of reference signal, 'Internal' or 'External'
        refSource = 'Internal'
        # Expected frequency deviation of external reference input in %
        expFrequencyDev = 5
        # Number of frames to be recorded
        NFrames = self.num_frames

        # Illumination Driving Signal

        # Signal generator DC offset in % of full range
        sgnOffset = 20.0
        # Signal generator peak-to-peak amplitude in % of full range
        sgnAmplitude = 10.0
        # Signal generator frequency in Hz
        sgnFrequency = 10000.0

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
        self.camera.remote_device.node_map.LockInReferenceFrequencyScaler.value = "Off"
        self.camera.remote_device.node_map.LockInReferenceSourceSignal.value = "FI2"

        # Illumination

        self.camera.remote_device.node_map.SignalGeneratorOffset.value = sgnOffset
        self.camera.remote_device.node_map.SignalGeneratorAmplitude.value = sgnAmplitude
        self.camera.remote_device.node_map.LightControllerSelector.value = "LightController0"
        self.camera.remote_device.node_map.SignalGeneratorModulationMode.value = "On"
        self.camera.remote_device.node_map.SignalGeneratorFrequency.value = sgnFrequency
        self.camera.remote_device.node_map.LightControllerSource.value = "SignalGenerator"





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
        self.acquiring = True

    def run(self):
        """" Continuous tasks of the Worker are defined here.
        If loops check for requested changes in settings prior each acquisition. """
        print('Heliotis worker started')
        while not self.terminate: #infinite loop
            if self.acquiring:
                rawI,rawQ = self.acquire()
                avg_I = np.average(rawI[-2:],axis=0)
                avg_Q = np.average(rawQ[-2:], axis=0)
                offset_I = np.average(rawI, axis=0)
                offset_Q = np.average(rawQ, axis=0)
                #avg_image = np.sqrt(np.square(avg_I-offset_I) + np.square(avg_Q - offset_Q))
                avg_I = np.average(rawI,axis=0)
                avg_Q = np.average(rawQ, axis=0)
                avg_image = np.sqrt(np.square(avg_I) + np.square(avg_Q))

                self.sendSpectrum.emit(avg_image)
            time.sleep(0.7)
        print('Worker closes')
        return

    def acquire(self, timeout=30):
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