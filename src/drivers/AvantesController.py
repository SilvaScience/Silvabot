'''
Spectrometer interface based on this module: https://github.com/PyMoDAQ/pymodaq_plugins_avantes/tree/5.0.x/src/pymodaq_plugins_avantes

Since it is not a fully maintained package, we have adapted it for our spectrometer.

Requires avaspec in the same folder.
'''

import time
import numpy as np
from src.drivers import avaspec


class AvantesController:
    """
    Controller for the Avantes Spectrometer AvaSPec-ULS2048CL-EVO
    This class relies on communication with the instrument via USB-3 link

    Additional methods provide control over digital output and analog input
    See Avantes doc. and avaspec.py module
    Remark:
            - The AVS spectrometer functions are managed over 4096 pixels even
              though the spectrometer has only 2048 pixels.
            - Only a single USB spectrometer is controlled.
            - For asynchronous measurement with callback function, see either
              AvantesControllerTestApp.py or PyQt5_demo.py
    """

    def __init__(self):
        """
        Method called at object creation (implementation)
        Init object attributes
        """

        self._initialized = False
        self.hardware_present = False
        self._serial_number = str("none")
        self._measurement_config = avaspec.MeasConfigType()
        self._device_handle = 0
        self._number_of_pixels = 4096
        self._wavelengths = [0.0] * 4096
        self._spectraldata = [0.0] * 4096
        self._scan_count = 0
        # shouldn't this go to the PyMoDAQ parameters?

    def open_communication(self) -> bool:
        """
        Open the USB communication with an Avantes Spectrometer

        Returns
        -------
                True on succes, else False
        """
        # Initializes the communication interface with the spectrometers-
        # param "0" indicates USB use
        if avaspec.lib is None:
            return False

        nb_of_found_devices = avaspec.AVS_Init(0)
        nb_of_found_USB_devices = avaspec.AVS_UpdateUSBDevices()
        if nb_of_found_USB_devices < 1:
            return False

        # Get spectrometer identity, serial number and information
        device_list = avaspec.AVS_GetList(1)
        self._serial_number = str(device_list[0].SerialNumber.decode("utf-8"))
        self._initialized = True

        # Activate spectrometer for communication and get a handle on it
        self._device_handle = avaspec.AVS_Activate(device_list[0])

        # Get device configuration (number of pixels and wavelength)
        device_config = avaspec.AVS_GetParameter(self._device_handle, 63484)

        self._number_of_pixels = device_config.m_Detector_m_NrPixels
        full_wavelength_scale = avaspec.AVS_GetLambda(self._device_handle)

        # The AvaSpec_ULS2048CL_EVO spectrometer has only 2048 elements,
        # so split in 2
        self._wavelengths = full_wavelength_scale
        #devicetype = avaspec.AVS_GetDeviceType(globals_var.dev_handle)

        self.hardware_present = True
        return True

    @property
    def is_initialized(self) -> bool:
        """
        Check if the controller is initialized

        Returns
        -------
                the initialized status True of False
        """
        return self._initialized

    @property
    def serial_number(self) -> str:
        """
        Get the serial number of the Avantes

        Returns
        -------
                serial number (str)
        """
        return self._serial_number

    def close_communication(self):
        """
        Close communication
        """
        avaspec.AVS_Done()

    def set_default_config(self):
        """
        Configure the acquisition using the _measconfig object using
        default parameters and send the configuration to the spectrometer
        """
        avaspec.AVS_UseHighResAdc(self._device_handle, True)
        # NB: return: SUCCESS = 0 or FAILURE <> 0; not currently used

        self._measurement_config.m_StartPixel = 0
        self._measurement_config.m_StopPixel = self._number_of_pixels - 1
        self._measurement_config.m_IntegrationTime = 100 # in ms
        self._measurement_config.m_IntegrationDelay = 0
        self._measurement_config.m_NrAverages = 1
        self._measurement_config.m_CorDynDark_m_Enable = 0
        # nesting of types does NOT work!! ?? whatever that means
        self._measurement_config.m_CorDynDark_m_ForgetPercentage = 0
        self._measurement_config.m_Smoothing_m_SmoothPix = 0
        self._measurement_config.m_Smoothing_m_SmoothModel = 0
        self._measurement_config.m_SaturationDetection = 0
        self._measurement_config.m_Trigger_m_Mode = 0
        self._measurement_config.m_Trigger_m_Source = 0
        self._measurement_config.m_Trigger_m_SourceType = 0
        self._measurement_config.m_Control_m_StrobeControl = 0
        self._measurement_config.m_Control_m_LaserDelay = 0
        self._measurement_config.m_Control_m_LaserWidth = 0
        self._measurement_config.m_Control_m_LaserWaveLength = 0.0
        self._measurement_config.m_Control_m_StoreToRam = 0
        result = avaspec.AVS_PrepareMeasure(self._device_handle,
                                            self._measurement_config)
        # NB: return: SUCCESS = 0 or FAILURE <> 0; not currently used

        # measurement counter
        self._scan_count = 0

        time.sleep(0.001)

    def set_integration_time(self, integration_time: float):
        """
        Set the integration time in [ms]

        Parameter
        ---------
                integration_time in [ms]
        """
        self._measurement_config.m_IntegrationTime = float(integration_time)
        avaspec.AVS_PrepareMeasure(self._device_handle,
                                   self._measurement_config)
        # NB: return: SUCCESS = 0 or FAILURE <> 0; not currently used
        self._integration_time = integration_time

    def set_number_of_averages(self, n_average: int):
        """
        Set the number of average

        Parameter
        ---------
                average_nb
        """
        self._measurement_config.m_NrAverages = n_average
        avaspec.AVS_PrepareMeasure(self._devive_handle,
                                   self._measurement_config)
        # NB: return: SUCCESS = 0 or FAILURE <> 0; not currently used

    def get_digital_input(self, pin_no: int) -> int:
        """
        Returns the status of the specified digital input

        Parameters
        ----------
            portId
            For the AS7010:
            0 = DI1 = Pin 24 at 26-pins connector
            1 = DI2 = Pin 7 at 26-pins connector
            2 = DI3 = Pin 16 at 26-pins

        Returns
        -------
                digital state 0=low or 1=high
        """

        return avaspec.AVS_GetDigIn(self._device_handle, pin_no)

    def set_digital_output(self, pin_no: int, value: int) -> int:
        """
        Set the digital output value for the specified digital output

        Parameters
        ----------
            portId
            For the AS7010:
            0 = DO1 = pin 11 at 26 - pins connector (can be used also as PWM)
            1 = DO2 = pin 2 at 26 - pins connector (can be used also as PWM)
            2 = DO3 = pin 20 at 26 - pins connector (can be used also as PWM)
            3 = DO4 = pin 12 at 26 - pins connector
            4 = DO5 = pin 3 at 26 - pins connector (can be used also as PWM)
            5 = DO6 = pin 21 at 26 - pins connector (can be used also as PWM)
            6 = DO7 = pin 13 at 26 - pins connector (can be used also as PWM)
            7 = DO8 = pin 4 at 26 - pins connector
            8 = DO9 = pin 22 at 26 - pins connector
            9 = DO10 = pin 25 at 26 - pins connector

            value: 0 (low) or 1 (high)

        Returns
        -------
                On success:    0   = ERR_SUCCESS
                On error:      -3  = ERR_DEVICE_NOT_FOUND
                               -28 = ERR_INVALID_DEVICE_ID
                               -6  = ERR_TIMEOUT (error in communication)
                               -1  = ERR_INVALID_PARAMETER
        """

        return avaspec.AVS_SetDigOut(self._device_handle, pin_no, value)

    def set_analog_output(self, pin_no: int, value: float) -> int:
        """
        Set the analog output value for the specified digital output

        Parameters
        ----------
            portId:
            For the AS7010:
            0 = AO1 = pin 17 at 26 - pins connector
            1 = AO2 = pin 26 at 26 - pins connector

            value: 0 or 5.0 V

        Returns
        -------
                On success:    0   = ERR_SUCCESS
                On error:      -3  = ERR_DEVICE_NOT_FOUND
                               -28 = ERR_INVALID_DEVICE_ID
                               -6  = ERR_TIMEOUT (error in communication)
                               -1  = ERR_INVALID_PARAMETER
        """
        return avaspec.AVS_SetAnalogOut(self._devive_handle, pin_no, value)

    @property
    def wavelengths(self):
        """
        Get an array of wavelength used by the spectrometer
        Returns
        -------
                a "standard" array of 4096 elements whom, in case of a
                Avaspec-ULS2048CL-EVO, 2048 has wavelength number,
                other elements are set to zeros  !!!
        """

        full_scale = avaspec.AVS_GetLambda(self._device_handle)
        #return np.array_split(np.array(full_scale), 2)[0]
        return np.array(full_scale)

    def grab_spectrum(self):
        """
        Read the spectrum from the Avantes Spectrometer
        And store result in global_vars.spectrometer_y_values

        Returns
        -------
                none, only update globals_vars
        """
        avaspec.AVS_Measure(self._device_handle, 0, 1)
        # NB: return: SUCCESS = 0 or FAILURE <> 0; not currently used
        buffer = 0.02 # needed to avoid communcation failures. Adapt if needed.
        wait_time = self._measurement_config.m_IntegrationTime/1000 + buffer
        time.sleep(wait_time)
        # at least wait for the integration time !
        # we wait the measurement ends
        while avaspec.AVS_PollScan(self._device_handle):
            time.sleep(0.005)

        # we get the data with internal timestamp of the device
        # which is currently not used
        data = avaspec.AVS_GetScopeData(self._device_handle)
        full_spectrometer_y_values = np.array(data[1])

        # get only 2048 elements by splitting in 2
        result = full_spectrometer_y_values
        self._scan_count += 1
        time.sleep(0.001)
        return result,data[0]

    def abort_measurement(self):
        """
        Abort a running measurement

        Returns
        -------
                SUCCESS = 0 or FAILURE <> 0
        """
        self._is_grabbing = False
        return avaspec.AVS_StopMeasure(self._device_handle)

    def start_continuous_grabbing(self, callback):
        print("controller start grabbing")
        self.pymodaq_callback = callback
        avs_cb = avaspec.AVS_MeasureCallbackFunc(self.avantes_callback)
        self._scan_count = 0
        avaspec.AVS_MeasureCallback(self._device_handle, avs_cb, -1)
        time.sleep(0.1)

    def avantes_callback(self, lparam1, lparam2):
        """
        Retrieve the spectrum from the Avantes Spectrometer
        Use this function in an asynchrone "callback" mechanism

        Returns
        -------
                spectraData: a tuple: timestamp, array of 4096 double
        """
        result = avaspec.AVS_GetScopeData(self._device_handle)
        full_data = np.array(result[1])
        self._scan_count += 1
        self.pymodaq_callback(np.array_split(full_data, 2)[0])

    def heartbeat(self):
        result = avaspec.AVS_Heartbeat(self._device_handle)
