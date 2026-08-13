"""
Created on Fri Feb 07 15:26:53 2025

@author: Simon Daneau
Hardware class to control spectrometer. All hardware classes require a definition of
parameter_display_dict (set Spinbox options and read/write)
set_parameter function (assign set functions)

"""
"""TO DOS:
- think of TO DOs
"""

import numpy as np
from PyQt5 import QtCore
from collections import defaultdict
from pathlib import Path
import matplotlib.pyplot as plt
from drivers.StresingDriver import camera_settings
from drivers.StresingDriver import measurement_settings
from drivers.StresingDriver import *
import sys
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
import configparser
import logging
import datetime

logger = logging.getLogger(__name__)

""" Trigger sources the board understands, as documented in StresingDriver.init_driver(). sti and bti
share the numbering for the external inputs but diverge above 4, so they are listed separately rather
than exposed as raw numbers. """
TRIGGER_INPUTS = {'I': 0, 'S1': 1, 'S2': 2, 'I gated by S2': 3}
TRIGGER_TIMER = 4
CHOPPER_INPUTS = {'S1': 5, 'S2': 6, 'S1 and S2': 7}

CONTINUOUS = 'continuous'
EXTERNAL = 'external'
CHOPPER = 'chopper'


class StresingCamera(QtCore.QThread):

    name = 'StresingCamera'

    def __init__(self,hardware_params):
        super(StresingCamera, self).__init__()

        # initialize Worker
        """ The worker is kept as the signal carrier that publishes each acquired spectrum, but its
        thread is not started: the readout is a pull, driven by get_intensities() from the measurement
        thread, so a polling loop has nothing to do. Not starting it also avoids leaving a thread
        running at shutdown. """
        self.worker = StresingWorker()
        self.type = 'Camera'

        # This is the hardware parameters dictionnary. It is provided by hardware-specific configurations and are not changed in operation
        self.hardware_params=hardware_params
        self.monochromator=None#By default, no spectrometer is attached
        
        # Define spectral range
        self.spec_length = self.hardware_params.get('num_pixels', 1024)
        self.spec_range = np.r_[0:self.spec_length]
        
        # Path to the DLL file
        folder_path_dll = Path(__file__).resolve().parent #add or remove parent based on the file location
        path_dll = folder_path_dll / "stresing" / "ESLSCDLL.dll"
        path_dll = str(path_dll)

        # Config lives alongside the DLL in the repo, so it travels with the driver instead of
        # depending on a fixed install path on a given PC.
        path_config = folder_path_dll / "stresing" / "config_UdeM.ini"

        # Create a ConfigParser object
        config = CaseInsensitiveConfig()
        # Read the INI file
        config.read(path_config)

        # Intitalize stresing camera 
        self.driver = init_driver(self, path_dll, config) # type: ignore

        # preallocate arrays
        self.spectrum = np.ndarray([])

        # Parameters. Defines parameters that are required for by the interface
        self.sample = int(config.get("General","nos"))
        self.block = int(config.get("General","nob"))
        self.adc_gain = int(config.get("Board0","adcGain"))
        self.channel0 = int(config.get("Board0","dacCameraChannel0"))
        self.channel1 = int(config.get("Board0","dacCameraChannel1"))
        self.channel2 = int(config.get("Board0","dacCameraChannel2"))
        self.channel3 = int(config.get("Board0","dacCameraChannel3"))
        self.channel4 = int(config.get("Board0","dacCameraChannel4"))
        self.channel5 = int(config.get("Board0","dacCameraChannel5"))
        self.channel6 = int(config.get("Board0","dacCameraChannel6"))
        self.channel7 = int(config.get("Board0","dacCameraChannel7"))
        self.bti = int(config.get("Board0","bti"))
        self.sti = int(config.get("Board0","sti"))
        self.btimer = int(float(config.get("Board0","btimer")))
        self.stimer = int(config.get("Board0","stimer"))
        self.new_spectrum = False

        """ Deadline used when the board is waiting on an external signal. Without it a trigger that
        never arrives leaves the acquisition thread stuck inside the DLL with no way back. """
        self.trigger_timeout_s = 5.0

        # set parameter dict
        self.parameter_dict = defaultdict()
        """ Set up the parameter dict. 
        Here, all properties of parameters to be handled by the parameter dict are defined."""
        self.parameter_display_dict = defaultdict(dict)

        self.parameter_display_dict['No_Sample']['val'] = self.sample
        self.parameter_display_dict['No_Sample']['unit'] = ' '
        self.parameter_display_dict['No_Sample']['min'] = 6
        self.parameter_display_dict['No_Sample']['max'] = 4294967295
        self.parameter_display_dict['No_Sample']['read'] = False

        self.parameter_display_dict['No_Block']['val'] = self.block
        self.parameter_display_dict['No_Block']['unit'] = ' '
        self.parameter_display_dict['No_Block']['min'] = 1
        self.parameter_display_dict['No_Block']['max'] = 4294967295
        self.parameter_display_dict['No_Block']['read'] = False

        self.parameter_display_dict['ADC_Gain']['val'] = self.adc_gain
        self.parameter_display_dict['ADC_Gain']['unit'] = ' '
        self.parameter_display_dict['ADC_Gain']['max'] = 12
        self.parameter_display_dict['ADC_Gain']['read'] = False

        self.parameter_display_dict['DAC_0']['val'] = self.channel0
        self.parameter_display_dict['DAC_0']['unit'] = ' '
        self.parameter_display_dict['DAC_0']['max'] = 65535
        self.parameter_display_dict['DAC_0']['read'] = False

        self.parameter_display_dict['DAC_1']['val'] = self.channel1
        self.parameter_display_dict['DAC_1']['unit'] = ' '
        self.parameter_display_dict['DAC_1']['max'] = 65535
        self.parameter_display_dict['DAC_1']['read'] = False

        self.parameter_display_dict['DAC_2']['val'] = self.channel2
        self.parameter_display_dict['DAC_2']['unit'] = ' '
        self.parameter_display_dict['DAC_2']['max'] = 65535
        self.parameter_display_dict['DAC_2']['read'] = False

        self.parameter_display_dict['DAC_3']['val'] = self.channel3
        self.parameter_display_dict['DAC_3']['unit'] = ' '
        self.parameter_display_dict['DAC_3']['max'] = 65535
        self.parameter_display_dict['DAC_3']['read'] = False

        self.parameter_display_dict['DAC_4']['val'] = self.channel4
        self.parameter_display_dict['DAC_4']['unit'] = ' '
        self.parameter_display_dict['DAC_4']['max'] = 65535
        self.parameter_display_dict['DAC_4']['read'] = False

        self.parameter_display_dict['DAC_5']['val'] = self.channel5
        self.parameter_display_dict['DAC_5']['unit'] = ' '
        self.parameter_display_dict['DAC_5']['max'] = 65535
        self.parameter_display_dict['DAC_5']['read'] = False

        self.parameter_display_dict['DAC_6']['val'] = self.channel6
        self.parameter_display_dict['DAC_6']['unit'] = ' '
        self.parameter_display_dict['DAC_6']['max'] = 65535
        self.parameter_display_dict['DAC_6']['read'] = False

        self.parameter_display_dict['DAC_7']['val'] = self.channel7
        self.parameter_display_dict['DAC_7']['unit'] = ' '
        self.parameter_display_dict['DAC_7']['max'] = 65535
        self.parameter_display_dict['DAC_7']['read'] = False

        self.parameter_display_dict['Block_Trig']['val'] = self.bti
        self.parameter_display_dict['Block_Trig']['unit'] = ' '
        self.parameter_display_dict['Block_Trig']['max'] = 8
        self.parameter_display_dict['Block_Trig']['read'] = False

        self.parameter_display_dict['Scan_Trig']['val'] = self.sti
        self.parameter_display_dict['Scan_Trig']['unit'] = ' '
        self.parameter_display_dict['Scan_Trig']['max'] = 5
        self.parameter_display_dict['Scan_Trig']['read'] = False

        self.parameter_display_dict['Block_Timer']['val'] = self.btimer
        self.parameter_display_dict['Block_Timer']['unit'] = ' '
        self.parameter_display_dict['Block_Timer']['max'] = 1000000
        self.parameter_display_dict['Block_Timer']['read'] = False

        self.parameter_display_dict['Scan_Timer']['val'] = self.stimer
        self.parameter_display_dict['Scan_Timer']['unit'] = ' '
        self.parameter_display_dict['Scan_Timer']['max'] = 1000000
        self.parameter_display_dict['Scan_Timer']['read'] = False
        # set up parameter dict that only contains value. (faster to access)
        self.parameter_dict = {}
        for key in self.parameter_display_dict.keys():
            self.parameter_dict[key] = self.parameter_display_dict[key]['val']

    def set_parameter(self, parameter, value):
        """REQUIRED. This function defines how changes in the parameter tree are handled.
        In devices with workers, a pause of continuous acquisition might be required. """
        if parameter == 'No_Sample':
            self.parameter_dict['No_Sample'] = value
            self.driver.settings.nos = int(value)
            self.sample = value
            self.new_spectrum = False
        elif parameter == 'No_Block':
            self.parameter_dict['No_Block'] = value
            self.driver.settings.nob = int(value)
            self.block = value
            self.new_spectrum = False
        elif parameter == 'ADC_Gain':
            self.parameter_dict['ADC_Gain'] = value
            self.driver.settings.camera_settings[self.driver.drvno].adc_gain = int(value)
            self.adc_gain = value
            self.new_spectrum = False
        elif parameter == 'DAC_0':
            self.parameter_dict['DAC_0'] = value
            self.driver.settings.camera_settings[self.driver.drvno].dac_output[0][0] = int(value)
            self.channel0 = value
            self.new_spectrum = False
        elif parameter == 'DAC_1':
            self.parameter_dict['DAC_1'] = value
            self.driver.settings.camera_settings[self.driver.drvno].dac_output[0][1] = int(value)
            self.channel1 = value
            self.new_spectrum = False
        elif parameter == 'DAC_2':
            self.parameter_dict['DAC_2'] = value
            self.driver.settings.camera_settings[self.driver.drvno].dac_output[0][2] = int(value)
            self.channel2 = value
            self.new_spectrum = False
        elif parameter == 'DAC_3':
            self.parameter_dict['DAC_3'] = value
            self.driver.settings.camera_settings[self.driver.drvno].dac_output[0][3] = int(value)
            self.channel3 = value
            self.new_spectrum = False
        elif parameter == 'DAC_4':
            self.parameter_dict['DAC_4'] = value
            self.driver.settings.camera_settings[self.driver.drvno].dac_output[0][4] = int(value)
            self.channel4 = value
            self.new_spectrum = False
        elif parameter == 'DAC_5':
            self.parameter_dict['DAC_5'] = value
            self.driver.settings.camera_settings[self.driver.drvno].dac_output[0][5] = int(value)
            self.channel5 = value
            self.new_spectrum = False
        elif parameter == 'DAC_6':
            self.parameter_dict['DAC_6'] = value
            self.driver.settings.camera_settings[self.driver.drvno].dac_output[0][6] = int(value)
            self.channel6 = value
            self.new_spectrum = False
        elif parameter == 'DAC_7':
            self.parameter_dict['DAC_7'] = value
            self.driver.settings.camera_settings[self.driver.drvno].dac_output[0][7] = int(value)
            self.channel7 = value
            self.new_spectrum = False
        elif parameter == 'Block_Trig':
            self.driver.settings.camera_settings[self.driver.drvno].bti_mode = int(value)
            self.bti = value
            self.new_spectrum = False
        elif parameter == 'Scan_Trig':
            self.driver.settings.camera_settings[self.driver.drvno].sti_mode = int(value)
            self.sti = value
            self.new_spectrum = False
        elif parameter == 'Block_Timer':
            self.driver.settings.camera_settings[self.driver.drvno].btime_in_microsec = int(value)
            self.btimer = value
            self.new_spectrum = False
        elif parameter == 'Scan_Timer':
            self.driver.settings.camera_settings[self.driver.drvno].stime_in_microsec = int(value)
            self.stimer = value
            self.new_spectrum = False
        init_measure(self) # type: ignore

    def calculate_wavelength_array(self):
        """
            Calculate the wavelength array for the pixels of the Stresing camera using the hardware parameters from the camera and the attached monochromator. 
        """
        if self.monochromator is not None:
            self.center_wavelength,self.grating_lines_per_mm=self.monochromator.get_monochromator_parameters()
            pixel_size_mm =self.hardware_params['pixel_size_mm'] 
            focal_length_mm = self.hardware_params['focal_length_mm']
            num_pixels = self.hardware_params['num_pixels']

            if self.hardware_params['calibrated']:

                pixel_size_mm = 24 / 1E3  # specs of Sresing
                focal_length_mm = 300  # specs of SP2300i
                num_pixels = 1010  # specs of stresing

                wl_center = self.center_wavelength
                m_order = 1
                px = np.linspace(1,1010,1010)

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

                pixel_size_mm = 24 / 1E3  # specs of Stresing
                focal_length_mm = 300  # specs of SP2300i
                num_pixels = 1010  # specs of Stresing

                # Calculate linear dispersion (nm/mm)
                dispersion = 1e6 / (focal_length_mm * self.grating_lines_per_mm)

                # Center pixel
                center_pixel = num_pixels // 2

                # Pixel index array
                pixel_indices = np.arange(num_pixels)

                # Wavelength at each pixel
                self.wavelengths = self.center_wavelength + (pixel_indices - center_pixel) * dispersion * pixel_size_mm

        else:
            self.wavelengths= self.hardware_params['num_pixels']
            logger.warning('%s No grating found attached to Stresing. Returning pixels indices instead of wavelength'%datetime.datetime.now())

    def attach_to_monochromator(self,monochromator):
        """
            Attaches the camera to a monochromator, letting the camera interface know where to get the monochromator parameters from.
            input:
                - monochromator (Monochromator QThread): The interface to the monochromator
        """
        """ Only the live grating readout is pulled from the monochromator (via
        calculate_wavelength_array -> get_monochromator_parameters). The optical calibration
        constants stay in this camera's own hardware_params (set at construction from config.yaml),
        so this driver has no dependency on which monochromator it happens to be paired with and can
        be reused on a different detection path unchanged. """
        self.monochromator=monochromator
        self.type='Spectrometer'

    def get_acquisition_mode(self):
        """
            Returns the current trigger setup in the vocabulary the interface uses, so a widget can
            show the mode rather than the raw sti/bti register values.
        """
        if self.bti in CHOPPER_INPUTS.values():
            mode = CHOPPER
        elif self.sti == TRIGGER_TIMER and self.bti == TRIGGER_TIMER:
            mode = CONTINUOUS
        else:
            mode = EXTERNAL
        inputs = {v: k for k, v in TRIGGER_INPUTS.items()}
        choppers = {v: k for k, v in CHOPPER_INPUTS.items()}
        return {'mode': mode,
                'scan_trigger': 'timer' if self.sti == TRIGGER_TIMER else inputs.get(self.sti, 'I'),
                'chopper': choppers.get(self.bti, 'S1'),
                'scan_interval_us': self.stimer,
                'block_interval_us': self.btimer,
                'timeout_s': self.trigger_timeout_s}

    def set_acquisition_mode(self, mode, scan_trigger='I', chopper='S1',
                             scan_interval_us=None, block_interval_us=None, timeout_s=None):
        """
            Sets sti, bti and their timers as one coherent choice instead of four loose registers.
            input:
                - mode (str): CONTINUOUS (the board drives itself), EXTERNAL (one readout per trigger
                  pulse) or CHOPPER (blocks gated by a chopper signal)
                - scan_trigger (str): key of TRIGGER_INPUTS, or 'timer', for what starts a readout.
                  Ignored in CONTINUOUS.
                - chopper (str): key of CHOPPER_INPUTS. Only used in CHOPPER.
                - scan_interval_us (int): time between readouts, applied only when readouts run on
                  the internal timer
                - block_interval_us (int): time between blocks, applied only in CONTINUOUS
                - timeout_s (float): how long to wait for an external signal before giving up
        """
        if mode == CONTINUOUS:
            sti = bti = TRIGGER_TIMER
        elif mode == EXTERNAL:
            sti = bti = TRIGGER_INPUTS[scan_trigger]
        elif mode == CHOPPER:
            bti = CHOPPER_INPUTS[chopper]
            sti = TRIGGER_TIMER if scan_trigger == 'timer' else TRIGGER_INPUTS[scan_trigger]
        else:
            raise ValueError('Unknown acquisition mode: %s' % mode)

        cam = self.driver.settings.camera_settings[self.driver.drvno]
        cam.sti_mode, cam.bti_mode = sti, bti
        self.sti, self.bti = sti, bti

        """ The board only reads a timer in the mode that uses it. Writing them in the other modes
        would leave values on screen that have no effect, which is what made the old parameter table
        misleading. """
        if sti == TRIGGER_TIMER and scan_interval_us:
            cam.stime_in_microsec = int(scan_interval_us)
            self.stimer = int(scan_interval_us)
        if bti == TRIGGER_TIMER and block_interval_us:
            cam.btime_in_microsec = int(block_interval_us)
            self.btimer = int(block_interval_us)
        if timeout_s is not None:
            self.trigger_timeout_s = float(timeout_s)

        # Keep the generic parameter tree in step with what was set here.
        for key, value in (('Scan_Trig', self.sti), ('Block_Trig', self.bti),
                           ('Scan_Timer', self.stimer), ('Block_Timer', self.btimer)):
            self.parameter_dict[key] = value
            self.parameter_display_dict[key]['val'] = value

        self.new_spectrum = False
        init_measure(self) # type: ignore
        logger.info('%s Stresing acquisition mode: %s (sti=%d, bti=%d)'
                    % (datetime.datetime.now(), mode, sti, bti))

    def waits_for_external_signal(self):
        """
            True when either trigger depends on a signal the board does not generate itself, i.e.
            when an acquisition can legitimately never complete.
        """
        cam = self.driver.settings.camera_settings[self.driver.drvno]
        return cam.sti_mode != TRIGGER_TIMER or cam.bti_mode != TRIGGER_TIMER

    def get_num_pixel(self):
        return self.hardware_params['num_pixels']

    def get_wavelength(self):
        """
            Returns the wavelengths corresponding to each pixel of the camera
        """
        self.calculate_wavelength_array()
        return self.wavelengths

    def get_intensities(self):
        self.acquire_spectrum()
        self.spec = np.array(self.spectrum[13:-1])
        self.spec = self.spec[::-1]
        #self.spec[:12] = 0 # Removes the first indexes (special pixels of the camera)
        """ Publish the same data the caller gets, so a live view can follow the acquisition without
        going through DataHandling. """
        self.worker.sendSpectrum.emit(self.spec)
        return self.spec

    def expected_duration_s(self):
        """
            How long one acquisition should take when the board drives itself, from the timers it was
            given. Used to size the deadline, so a stalled board is caught in proportion to what the
            settings actually ask for.
        """
        cam = self.driver.settings.camera_settings[self.driver.drvno]
        scans, blocks = max(int(self.sample), 1), max(int(self.block), 1)
        seconds = 0.0
        if cam.sti_mode == TRIGGER_TIMER:
            seconds += scans * blocks * self.stimer / 1e6
        if cam.bti_mode == TRIGGER_TIMER:
            seconds += blocks * self.btimer / 1e6
        return seconds

    def acquire_spectrum(self):
        """
            Reads one spectrum off the board, in the calling thread.
            Always polls with a deadline. The blocking DLL call cannot be interrupted and has been
            seen never to return when the board is in a bad state, which hangs whichever thread asked
            for the spectrum with no way back -- including the interface itself. Waiting on the board
            is not worth losing the ability to give up.
        """
        init_measure(self) # type: ignore
        """ Only an acquisition that depends on an external signal needs the trigger watch. On the
        internal timer the board drives itself and the readouts are guaranteed, so waiting for a
        trigger there would just add a delay to every spectrum. """
        timeout_s = self.trigger_timeout_s if self.waits_for_external_signal() else None
        self.spectrum = measure(self, True, timeout_s) # type: ignore
        self.new_spectrum = True

class StresingWorker(QtCore.QThread):
    """ Publishes the spectra acquired from the Stresing camera to the interface.
    The camera is read synchronously by StresingCamera.acquire_spectrum() in the thread that asks for
    a spectrum, so this worker carries the signal only and its thread is never started. """
    # These are signals that allow to send data from a child thread to the parent hierarchy.
    sendSpectrum = QtCore.pyqtSignal(np.ndarray)

    def __init__(self):
        super(StresingWorker, self).__init__() # Elevates this thread to be independent.
        self.new_spectrum = False


class CaseInsensitiveConfig(configparser.ConfigParser):
    """ This class extends Python’s built-in configparser.ConfigParser to make both section names and option names case-insensitive.
    Normally, ConfigParser is only case-insensitive for option names, not section names, so this subclass enforces lowercase normalization for both. """

    def __init__(self, *args, **kwargs):
        """
            Initialize the parent ConfigParser. By inheriting from it, your class gets all the functionality of ConfigParser — things like: 
                Reading .ini files
                Parsing sections and options
                Providing .get(), .set(), .items(), etc.
            Then you can override or extend parts of that functionality to make it case-insensitive.
        """
        super().__init__(*args, **kwargs)

        # Force all option (key) names to be lowercase when stored internally
        # This makes option lookups case-insensitive
        self.optionxform = str.lower

    def read(self, filenames, encoding=None):
        """
            Use the parent class's read method to load the config file(s)
        """
        super().read(filenames, encoding)

        # Convert all section names and their corresponding option names to lowercase
        # This ensures that both sections and options are case-insensitive
        self._sections = {
            k.lower(): {kk.lower(): vv for kk, vv in v.items()}
            for k, v in self._sections.items()
        }

    def get(self, section, option, **kwargs):
        """
            Override the default .get() method so that lookups are case-insensitive
        """
        # Both section and option names are converted to lowercase before lookup
        return super().get(section.lower(), option.lower(), **kwargs)
