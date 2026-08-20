# -*- coding: utf-8 -*-
"""
Created on Mon Apr  28 15:09:53 2025

@author: David Tiede
Hardware class for the Heliotis camera alone. It has no notion of a monochromator and no optical
calibration -- drivers.Spectrograph pairs it with one and owns the wavelength axis, writing it
back to self.wavelength because the worker saves it alongside each raw frame.

All hardware classes require a definition of
parameter_display_dict (set Spinbox options and read/write)
set_parameter function (assign set functions)

NOTE:
This driver deals with heavy data and computations. It uses multithreading (NOT QT) to have truly independent workers and independent GIL.
Communication with the worker process needs to be simple (cannot include QT objects), but heavy tasks can easily be outsourced
to the worker.

This driver has device_setting_function implemented, allowing to interact directly from the GUI to the driver.

TO DO

- Background correct button is currently hardcorded and changes its status upon toggle. Should be synced to actual GUI status of button.

"""

import numpy as np
import os
from harvesters.core import Harvester
from collections import defaultdict
from PyQt5 import QtCore, QtWidgets
import time
import re
import h5py
from multiprocessing import Process, Queue
import threading
from genicam.gentl import InvalidHandleException


def camera_worker(cmd_q, res_q):
    # Function to initialize the camera worker. It needs to be implemented globally
    # (not within a class) as multiprocessing needs to pickle the worker around.
    w = CameraWorker(cmd_q, res_q)
    w.run()

class HeliotisCamera(QtCore.QObject):

    name = 'Heliotis'
    caps = frozenset({'output_mode'})

    request_file = QtCore.pyqtSignal()

    def __init__(self):
        super(HeliotisCamera, self).__init__()

        self.wavelength = np.linspace(200,1000,512)  # set by Spectrograph, saved with each raw frame
        self.px0 = np.linspace(1,512,512)
        self.spec_length = (542,512) # # pixis length is (xx, 542, 512), xx is acquired frames

        # Parameters. Defines parameters that are required for by the interface
        self.new_spectrum = False
        self.output_mode = '2D'

        #initial heliotis settings
        self.num_frames = 100
        self.take_average = False
        self.sensitivity = 1
        self.N_Periods = 100 #95
        self.ref_freq =  1000 # 29790  # # 71531.2#26662#53325
        self.freq_dev = 5  # 29790  # # 71531.2#26662#53325
        self.ac_coupling = 0
        self.timeout = 30

        # set parameter dict
        self.parameter_dict = defaultdict()
        """ Set up the parameter dict. 
        Here, all properties of parameters to be handled by the parameter dict are defined."""
        self.parameter_display_dict = defaultdict(dict)
        self.parameter_display_dict['num_frames']['val'] = self.num_frames
        self.parameter_display_dict['num_frames']['unit'] = ' frames'
        self.parameter_display_dict['num_frames']['min'] = 4
        self.parameter_display_dict['num_frames']['max'] = 910 # 910 is heliotis max
        self.parameter_display_dict['num_frames']['read'] = False
        self.parameter_display_dict['take_average']['val'] = 0
        self.parameter_display_dict['take_average']['unit'] = ' per'
        self.parameter_display_dict['take_average']['max'] = 100 # 100 is heliotis max
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
        self.parameter_display_dict['freq_dev']['val'] = self.freq_dev
        self.parameter_display_dict['freq_dev']['unit'] = ' per'
        self.parameter_display_dict['freq_dev']['max'] = 100 # 44700 29796
        self.parameter_display_dict['freq_dev']['read'] = False
        self.parameter_display_dict['AC_coupling']['val'] = self.ac_coupling
        self.parameter_display_dict['AC_coupling']['unit'] = ' per'
        self.parameter_display_dict['AC_coupling']['max'] = 100 # 44700 29796
        self.parameter_display_dict['AC_coupling']['read'] = False
        self.parameter_display_dict['timeout']['val'] = self.timeout
        self.parameter_display_dict['timeout']['unit'] = ' s'
        self.parameter_display_dict['timeout']['max'] = 500 # 44700 29796
        self.parameter_display_dict['timeout']['read'] = False

        # set up parameter dict that only contains value. (faster to access)
        self.parameter_dict = {}
        for key in self.parameter_display_dict.keys():
            self.parameter_dict[key] = self.parameter_display_dict[key]['val']

        # initialize camera interface
        print('Heliotis initialized')

        # initialize camera
        self.cmd_q = Queue()
        self.res_q = Queue()

        self.worker = Process(
            target=camera_worker,
            args=(self.cmd_q, self.res_q),
            daemon=True
        )
        self.worker.start()
        self.cmd_q.put({
            "type": "PARAMETERS",
            "parameter_list": [self.num_frames, self.sensitivity, self.N_Periods, self.ref_freq, self.freq_dev,self.ac_coupling],
        })

        # Timer to check whether new spectrum is available for get_intensities
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.check_results)
        self.timer.start(200)
        self.correct_bg_checkbox = False
        self.ref_filename = None

        self.device_setting_function = dict()
        self.device_setting_function['load_bg'] = ('Action',self.load_bg)
        self.device_setting_function['correct_bg'] = ('Checkbox', self.correct_bg_checkbox_toggle)

    def correct_bg_checkbox_toggle(self, checked):
        if self.correct_bg_checkbox:
            self.correct_bg_checkbox = False
        else:
            self.correct_bg_checkbox = True
        self.cmd_q.put({
            "type": "BG_CHECKED",
            "argument": self.correct_bg_checkbox
        })

    def load_bg(self):
        self.request_file.emit()
        print(f'Loading background image {self.ref_filename}')
        self.cmd_q.put({
            "type": "BG_FILENAME",
            "argument": self.ref_filename
        })

    def set_parameter(self, parameter, value):
        """REQUIRED. This function defines how changes in the parameter tree are handled.
        In devices with workers, a pause of continuous acquisition might be required. """
        if parameter == 'num_frames':
            self.parameter_dict['num_frames'] = value
            self.num_frames = int(value)
            self.cmd_q.put({
                "type": "PARAMETERS",
                "parameter_list": [self.num_frames,self.sensitivity,self.N_Periods,self.ref_freq, self.freq_dev,self.ac_coupling]
            })
        elif parameter == 'take_average':
            self.parameter_dict['take_average'] = value
            if value == 100:
                self.take_average = True
            else:
                self.take_average = False
        elif parameter == 'sensitivity':
            self.parameter_dict['sensitivity'] = value
            self.sensitivity = value
            self.cmd_q.put({
                "type": "PARAMETER",
                "parameter_list": [self.num_frames,self.sensitivity,self.N_Periods,self.ref_freq, self.freq_dev,self.ac_coupling]
            })
        elif parameter == 'N_Periods':
            self.parameter_dict['N_Periods'] = value
            self.N_Periods = int(value)
            self.cmd_q.put({
                "type": "PARAMETER",
                "parameter_list": [self.num_frames,self.sensitivity,self.N_Periods,self.ref_freq, self.freq_dev,self.ac_coupling]
            })
        elif parameter == 'ref_freq':
            self.parameter_dict['ref_freq'] = value
            self.ref_freq = int(value)
            self.cmd_q.put({
                "type": "PARAMETER",
                "parameter_list": [self.num_frames,self.sensitivity,self.N_Periods,self.ref_freq, self.freq_dev,self.ac_coupling]
            })
        elif parameter == 'freq_dev':
            self.parameter_dict['freq_dev'] = value
            self.freq_dev = int(value)
            self.cmd_q.put({
                "type": "PARAMETER",
                "parameter_list": [self.num_frames,self.sensitivity,self.N_Periods,self.ref_freq, self.freq_dev,self.ac_coupling]
            })
        elif parameter == 'AC_coupling':
            self.parameter_dict['AC_coupling'] = value
            self.freq_dev = int(value)
            self.cmd_q.put({
                "type": "PARAMETER",
                "parameter_list": [self.num_frames,self.sensitivity,self.N_Periods,self.ref_freq, self.freq_dev,self.ac_coupling]
            })
        elif parameter == 'timeout':
            self.parameter_dict['timeout'] = value
            self.timeout = int(value)
            self.cmd_q.put({"type": "TIMEOUT","argument": self.timeout})


    def update_spectrum(self, spec):
        """REQUIRED. This is the slot function for the sendSpectrum pyqt.signal from the worker.
        It updates the last saved spectrum and changes the self.new_spectrum Boolean to True
        to allow to emit the treated signal from the spectrometer."""
        self.spectrum = spec
        self.new_spectrum = True

    def check_results(self):
        while not self.res_q.empty():
            self.spectrum = self.res_q.get()
            self.new_spectrum = True


    def set_output_mode(self, mode):
        """
            Chooses what get_intensities() hands back.
            input:
                - mode (str): '2D' delivers the frame as read, for the four-ROI maths in the
                  spectrum view. '1D' sums its rows into a single spectrum.
        """
        if mode not in ('1D', '2D'):
            raise ValueError(f"output mode must be '1D' or '2D', not {mode!r}")
        self.output_mode = mode
        return self.output_mode

    def get_output_mode(self):
        """
            output:
                - str: '1D' or '2D'
        """
        return self.output_mode

    def get_intensities(self):
        """ Gets the intensity. The example include the possibility of averaging several spectra and to
        perform a binning. Such functionalities might also be given by the camera.
        This function will be accessible from MeasurementClasses."""
        #print(
        #    "Current thread:", QtCore.QThread.currentThread(), int(QtCore.QThread.currentThreadId())
        #)
        self.new_spectrum = False
        self.cmd_q.put({"type": "ACQUIRE","take_average": self.take_average,"wavelength": self.wavelength,"save": True,"folder": r"D:\DATA\BIGFOOT"})
        while not self.new_spectrum:
            time.sleep(0.05)
        print(time.strftime("%H:%M:%S", time.localtime(time.time())) + ' Spectrum acquired')
        spectrum = np.asarray(self.spectrum)
        if spectrum.ndim > 1 and self.output_mode == '1D':
            spectrum = spectrum.sum(axis=0)  # counts scale with the number of rows summed
        return spectrum

class CameraWorker:
    """ This is a DemoWorker for the spectrometer.
    It continously acquires spectra and emits them to the Interface.
    It interrupts data acquisition if an int_time change is requested. Its important because most
    hardware can only handle one command at a time, acquiring or changeing settings.  """

    def __init__(self, command_queue, result_queue):
        super(CameraWorker, self).__init__() # Elevates this thread to be independent.

        # definition of some parameters
        #self.camera = camera
        self.spec_length = (252,1024)
        self.spectrum = np.zeros(self.spec_length)
        self.terminate = False
        self.paused = False
        self.processing = False
        self.acquiring = False
        self.correct_bg_checkbox = False
        self.background_I = np.zeros((542,512))
        self.background_Q = np.zeros((542,512))

        #initial heliotis settings
        self.num_frames = 100
        self.take_average = False
        self.sensitivity = 1
        self.N_Periods = 100 #95
        self.ref_freq =  1000 # 29790  # # 71531.2#26662#53325
        self.freq_dev = 5
        self.ac_coupling = 0
        self.timeout = 30

        self.cmd_q = command_queue
        self.res_q = result_queue
        self.running = True

        self.bad_acquisition = False

        print('Initialize Heliotis')
        self.h = Harvester()
        # read heliotis *.CTI path from environment variable
        ctiFile = os.environ['DIAPHUS_GENTL64_FILE']
        print(ctiFile)
        self.h.add_file(ctiFile)
        self.camera = self.selectDevice()

        # configure camera
        self.cameraConfig(self.num_frames, self.sensitivity, self.N_Periods, self.ref_freq, self.freq_dev, self.ac_coupling)

    def run(self):
        print(time.strftime("%H_%M_%S", time.localtime(time.time())) + ' Heliotis worker started')
        while self.running:
            try:
                cmd = self.cmd_q.get(timeout=0.1)
            except Exception:
                continue

            if cmd == "STOP":
                self.running = False
                break

            if cmd["type"] == "PARAMETERS":
                self.num_frames, self.sensitivity, self.N_Periods, self.ref_freq, self.freq_dev, self.ac_coupling = cmd["parameter_list"]
                try:
                    self.cameraConfig(self.num_frames, self.sensitivity, self.N_Periods, self.ref_freq, self.freq_dev,self.ac_coupling)
                except:
                    print("Camera config error. Config not updated. Consider taking an acquisiton to reset connection with heliotis")
            if cmd["type"] == 'BG_FILENAME':
                self.change_background(cmd["argument"])

            if cmd["type"] == 'BG_CHECKED':
                self.correct_bg_checkbox = cmd["argument"]

            if cmd["type"] == 'TIMEOUT' :
                self.timeout = cmd["argument"]

            if cmd["type"] == "ACQUIRE":
                take_avg = cmd["take_average"]
                wavelength = cmd["wavelength"]
                print(time.strftime("%H:%M:%S", time.localtime(time.time())) + ' Acquire started')
                t0 = time.time()
                rawI, rawQ = self.safe_acquire()
                print("Acquistion Duration:", time.time() - t0)
                if self.correct_bg_checkbox:
                    twoD_avgI = rawI - self.background_I
                    twoD_avgQ = rawQ - self.background_Q
                    print('External background correction done')
                else:
                    twoD_avgI = rawI - np.mean(rawI, axis=0)
                    twoD_avgQ = rawQ - np.mean(rawQ, axis=0)
                amp = np.sqrt((np.mean(twoD_avgI,axis=0)) ** 2 + (np.mean(twoD_avgQ,axis=0)) ** 2)
                if self.bad_acquisition:
                    print('Acquisition failed even after several attempts. Place background as replacement data')
                    amp = np.sqrt((self.background_I) ** 2 + (self.background_Q) ** 2)
                ty_res = time.localtime(time.time())
                timestamp = time.strftime("%H_%M_%S", ty_res)
                datestamp = time.strftime("20%y-%m-%d", ty_res)
                folder = os.path.join(r"D:\DATA\BIGFOOT", datestamp)
                os.makedirs(folder, exist_ok=True)
                folder_raw = os.path.join(folder, 'raw')
                os.makedirs(folder_raw, exist_ok=True)
                save_every_spectrum = True
                if take_avg:
                    filename = os.path.join(folder_raw, "avg_data" + timestamp + '.h5')
                    if save_every_spectrum:
                        with h5py.File(filename, 'w') as f:
                            f.create_dataset('averaged_rawI', data=np.mean(rawI, axis=0))
                            f.create_dataset('averaged_rawQ', data=np.mean(rawQ, axis=0))
                            f['averaged_rawI'].attrs["xaxis"] = wavelength
                    #print(time.strftime("%H:%M:%S", time.localtime(time.time())) + " Average data acquired")
                else:
                    filename = os.path.join(folder_raw, "raw_data" + timestamp + '.h5')
                    if save_every_spectrum:
                        with h5py.File(filename, 'w') as f:
                            f.create_dataset('rawI', data=rawI)
                            f.create_dataset('rawQ', data=rawQ)
                            f['rawI'].attrs["xaxis"] = wavelength
                    #print(timestamp.replace('_',':') + " Raw data acquired")

                # send back result
                #spectrum = np.mean(amp, axis=0)
                self.res_q.put(amp)

    def change_background(self,filename):
        if os.path.exists(filename):
            with h5py.File(os.path.join(filename), 'r') as f:
                try:
                    self.background_I = f['averaged_rawI'][:,:]
                    self.background_Q = f['averaged_rawQ'][:,:]
                except KeyError:
                    print("WARNING Background file has incorrect data structure")
        else:
            print('Background file does not exist')

    def safe_acquire(self, retries=3):
        for attempt in range(retries):
            try:
                result = self.acquire()
                if self.bad_acquisition: # Repeat acquistion if data was not taken properly
                    self.reconnect_heliotis()
                    self.bad_acquisition = False
                    print(time.strftime("%H:%M:%S", time.localtime(time.time())) + " Repeat acquisition")
                    result = self.acquire()
                return result

            except InvalidHandleException as e:
                print(f"[WARNING] Camera handle lost (attempt {attempt + 1}): {e}")

                self.reconnect_heliotis()

            except Exception as e:
                print(f"[ERROR] Unexpected error: {e}")
                raise

        raise RuntimeError("Acquisition failed after retries")

    def acquire(self):
        outputShape = self.getOutputShape()
        self.camera.start()
        self.camera.remote_device.node_map.TriggerSelector.value = 'FrameStart'
        self.camera.remote_device.node_map.TriggerSoftware.execute()

        result = {}
        t = threading.Thread(target=self.grab_frame, args=(result,))
        t.start()
        t.join(timeout=self.timeout)

        if t.is_alive():
            print(time.strftime("%H:%M:%S", time.localtime(time.time())) + " Killing stuck process (timeout reached). Repeat acquisition. ")
            print("NOTE: if this happens often, consider adapting timeout.")
            self.bad_acquisition = True
            data = (self.background_I, self.background_Q)
        else:
            #result = result.get()
            #if isinstance(result, Exception):
            #    raise result
            data = result.get("data")
            self.camera.stop()


        #with self.camera.fetch(timeout=10000) as buffer:
        #    data = np.array([img.data % 2 ** 15 // 4 for img in buffer.payload.components]).reshape(outputShape)
        #self.camera.stop()
        return data

    def grab_frame(self,result):
        outputShape = self.getOutputShape()
        try:
            with self.camera.fetch(timeout=10000) as buffer:
                result["data"] = np.array([
                    img.data % 2 ** 15 // 4
                    for img in buffer.payload.components
                ]).reshape(outputShape)
            #q.put(data)
        except Exception as e:
            #q.put(e)
            print(e)

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

    def cameraConfig(self, num_frames,sensitivity,Nperiods,ref_freq, freq_dev, ac_coupling):
        """
        simple configuration  of heliCam C4 using internal reference
        \param camera harvesters camera object
        """
        # Experiment Parameters
        # Sensor sensitivity in %/100, 0.5 for C4-S40, 0.2 for C4-S40U, 0.05 for C4-S41U and 0.25 for C4M
        sensitivity = sensitivity # 0.5
        # Number of intergration periods
        NPeriods = Nperiods #49
        # Background suppression on/off switch, 'AC' or 'DC'
        if ac_coupling == 100:
            coupling = 'AC'  # DC before
        else:
            coupling = 'DC' # DC before
        # Reference frequency in Hz
        refFrequency = ref_freq # 44700.    #3150.    #real : 29796.0  framerate = refFrequency / NPeriods
        # Source of reference signal, 'Internal' or 'External'
        refSource = 'External' # 'External'
        # Expected frequency deviation of external reference input in %
        #expFrequencyDev = 1
        # Number of frames to be recorded
        NFrames = num_frames

        # Configuration
        self.camera.remote_device.node_map.TriggerSelector.value = "RecordingStart"
        self.camera.remote_device.node_map.TriggerMode.value = "On" # changed
        self.camera.remote_device.node_map.TriggerSource.value = "FI3" # can be uncommented
        self.camera.remote_device.node_map.TriggerSelector.value = "FrameStart"
        self.camera.remote_device.node_map.TriggerMode.value = "On"
        self.camera.remote_device.node_map.TriggerSource.value = "Software" # "Software"

        # LIA

        self.camera.remote_device.node_map.DeviceOperationMode.value = "LockInCam"
        self.camera.remote_device.node_map.Scan3dExtractionMethod.value = "rawIQ"

        self.camera.remote_device.node_map.LockInSensitivity.value = sensitivity
        self.camera.remote_device.node_map.LockInTargetTimeConstantNPeriods.value = NPeriods
        self.camera.remote_device.node_map.LockInCoupling.value = coupling
        self.camera.remote_device.node_map.LockInExpectedFrequencyDeviation.value = freq_dev
        self.camera.remote_device.node_map.LockInTargetReferenceFrequency.value = refFrequency
        self.camera.remote_device.node_map.AcquisitionBurstFrameCount.value = NFrames

        self.camera.remote_device.node_map.LockInReferenceSourceType.value = refSource

        # For external reference signal only
        self.camera.remote_device.node_map.LockInReferenceFrequencyScaler.value = "DivideBy4" # "Off" "DivideBy8" # 8 #"DivideBy2"  # or "Off", "DivideBy2" etc
        self.camera.remote_device.node_map.LockInReferenceSourceSignal.value = "FI2"

        # Illumination
        self.camera.remote_device.node_map.LightControllerSource.value = 'Off'

    def selectDevice(self):
        """
        Scan for available devices and print device list
        let the user select one and open the connection to the device
        if just one device available, open it without user interaction
        \param h harvester object
        \return harvesters camera object
        """

        self.h.update()
        NDevices = len(self.h.device_info_list)
        print("{} device(s) detected on the Network:\n".format(NDevices))
        #for i, dev in enumerate(self.h.device_info_list):
        #    print("{}) {} ({})".format(i + 1, dev.id_, dev.serial_number))

        if NDevices == 1:
            selectionInt = 1
        elif NDevices == 0:
            print("WARNING: no heliotis detected. Wait and retry")
            time.sleep(3)
            self.h.update()
            NDevices = len(self.h.device_info_list)
            print("After wait: {} device(s) detected on the Network:\n".format(NDevices))
            selectionInt = 1
        else:
            selectionStr = input("Select a device (0=exit): ")
            selectionInt = int(selectionStr)
            if ((selectionInt <= 0) or (selectionInt > NDevices)):
                exit('No device selected - exit script')

        deviceID = self.h.device_info_list[selectionInt - 1].id_
        #print('selected device:', deviceID, '\n')
        return self.h.create(selectionInt - 1)

    def reconnect_heliotis(self):
        print('Kill current connection')
        try:
            # Try to stop safely (may already be broken)
            self.camera.stop()
        except Exception:
            pass

        try:
            self.camera.destroy()
        except Exception:
            pass

        try:
            self.redo_heliotis_connection()
        except Exception:
            print("Reconnection failed, try again")
            time.sleep(5)
            self.redo_heliotis_connection()


        # configure camera again
        self.cameraConfig(self.num_frames, self.sensitivity, self.N_Periods, self.ref_freq, self.freq_dev, self.ac_coupling)
        #time.sleep(5)
        print('Heliotis reconnected')

    def redo_heliotis_connection(self):
        try:
            if self.h is not None:
                self.h.reset()  # clears internal device list
                self.h = None
        except Exception as e:
            print(f"WARNING: Harvester reset failed: {e}")

        time.sleep(1)

        print('Reconnect Heliotis')
        self.h = Harvester()
        # read heliotis *.CTI path from environment variable
        ctiFile = os.environ['DIAPHUS_GENTL64_FILE']
        self.h.add_file(ctiFile)
        self.camera = self.selectDevice()

    def pause(self):
        self.paused = True

    def resume(self):
        self.paused = False
        
