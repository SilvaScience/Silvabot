#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jun  5 10:52:39 2024

@author: SimonDaneau
"""
import ctypes
import os
import configparser
import time
import numpy as np

# These are the settings structs. It must be the same like in EBST_CAM/shared_src/struct.h regarding order, data formats and size.
class camera_settings(ctypes.Structure):
	_fields_ = [("use_software_polling", ctypes.c_uint32),
		("sti_mode", ctypes.c_uint32),
		("bti_mode", ctypes.c_uint32),
		("stime_in_microsec", ctypes.c_uint32),
		("btime_in_microsec", ctypes.c_uint32),
		("sdat_in_10ns", ctypes.c_uint32),
		("bdat_in_10ns", ctypes.c_uint32),
		("sslope", ctypes.c_uint32),
		("bslope", ctypes.c_uint32),
		("xckdelay_in_10ns", ctypes.c_uint32),
		("sec_in_10ns", ctypes.c_uint32),
		("trigger_mode_integrator", ctypes.c_uint32),
		("SENSOR_TYPE", ctypes.c_uint32),
		("CAMERA_SYSTEM", ctypes.c_uint32),
		("CAMCNT", ctypes.c_uint32),
		("PIXEL", ctypes.c_uint32),
		("is_fft_legacy", ctypes.c_uint32),
		("led_off", ctypes.c_uint32),
		("sensor_gain", ctypes.c_uint32),
		("adc_gain", ctypes.c_uint32),
		("temp_level", ctypes.c_uint32),
		("bticnt", ctypes.c_uint32),
		("gpx_offset", ctypes.c_uint32),
		("FFT_LINES", ctypes.c_uint32),
		("VFREQ", ctypes.c_uint32),
		("fft_mode", ctypes.c_uint32),
		("lines_binning", ctypes.c_uint32),
		("number_of_regions", ctypes.c_uint32),
		("s1s2_read_delay_in_10ns", ctypes.c_uint32),
		("region_size", ctypes.c_uint32 * 8),
		("dac_output", ctypes.c_uint32 * 8 * 8), # 8 channels for 8 possible cameras in line
		("tor", ctypes.c_uint32),
		("adc_mode", ctypes.c_uint32),
		("adc_custom_pattern", ctypes.c_uint32),
		("bec_in_10ns", ctypes.c_uint32),
		("channel_select", ctypes.c_uint32),
		("ioctrl_impact_start_pixel", ctypes.c_uint32),
		("ioctrl_output_width_in_5ns", ctypes.c_uint32 * 8),
		("ioctrl_output_delay_in_5ns", ctypes.c_uint32 * 8),
		("ictrl_T0_period_in_10ns", ctypes.c_uint32),
		("dma_buffer_size_in_scans", ctypes.c_uint32),
		("tocnt", ctypes.c_uint32),
		("sticnt", ctypes.c_uint32),
		("sensor_reset_or_hsir_ec", ctypes.c_uint32),
		("write_to_disc", ctypes.c_uint32),
		("file_path", ctypes.c_char * 256),
		("shift_s1s2_to_next_scan", ctypes.c_uint32),
		("is_cooled_camera_legacy_mode", ctypes.c_uint32),
		("monitor", ctypes.c_uint32),
		("manipulate_data_mode", ctypes.c_uint32),
		("manipulate_data_custom_factor", ctypes.c_double),
		("ec_legacy_mode", ctypes.c_uint32),]

class measurement_settings(ctypes.Structure):
	_fields_ = [("board_sel", ctypes.c_uint32),
	("nos", ctypes.c_uint32),
	("nob", ctypes.c_uint32),
	("contiuous_measurement", ctypes.c_uint32),
	("cont_pause_in_microseconds", ctypes.c_uint32),
	("camera_settings", camera_settings * 5)]

def init_driver(self, path_dll, config):

    # Always use board 0. There is only one PCIe board.
    self.drvno = 0
    
    # Create an instance of the settings struct
    self.settings = measurement_settings()
    
    # Load ESLSCDLL.dll version 4.17.8.0
    self.dll = ctypes.WinDLL(path_dll)
    
    # Set the return type of DLLConvertErrorCodeToMsg to c-string pointer
    self.dll.DLLConvertErrorCodeToMsg.restype = ctypes.c_char_p
    # Get a pointer to the settings
    ptr_settings = ctypes.pointer(self.settings)
    # Init all settings to its default value
    self.dll.DLLInitSettingsStruct(ptr_settings)

    # Set all settings that are needed for the measurement. 
    self.settings.board_sel = int(config.get("General","boardSel")) # Controls which boards are used for the measurement.
    self.settings.nos = int(config.get("General","nos")) # Number of samples (nos). One sample is one readout of the camera.
    self.settings.nob = int(config.get("General","nob")) # Number of blocks (nob). One block contains nos readouts.
    self.settings.camera_settings[self.drvno].CAMCNT = int(config.get("board0","camcnt")) # Number of cameras which are connected to one PCIe board.
    self.settings.camera_settings[self.drvno].fft_mode = int(config.get("board0","fftMode")) # Controls the operating mode for FFT sensors.
    self.settings.camera_settings[self.drvno].FFT_LINES = int(config.get("board0","fftLines")) # Count of vertical lines for FFT sensors (sensor S14290).
    self.settings.camera_settings[self.drvno].VFREQ = int(config.get("board0","vfreq")) # Controls the vertical clock frequency for FFT sensors (sensor S14290). 
    self.settings.camera_settings[self.drvno].use_software_polling = int(config.get("board0","useSoftwarePolling")) # Determines which method is used to copy data from DMA to user buffer.
    self.settings.camera_settings[self.drvno].adc_gain = int(config.get("board0","adcGain")) # Controlling the gain function of the ADC in 3030 high speed cameras (sensor S14290 use 5 or 6).
    self.settings.camera_settings[self.drvno].tor = int(config.get("board0","tor")) # Shows the exposure window at the O output of the PCI card.
    self.settings.camera_settings[self.drvno].trigger_mode_integrator = int(config.get("board0","triggerCc")) # Trigger mode camera control.

    # Scan trigger input (sti) mode determines the signal on which one readout is started :
    #   0 - External trigger on input I of PCIe board 
    #   1 - External trigger on input S1 of PCIe board 
    #   2 - External trigger on input S2 of PCIe board
    #   3 - External trigger by I but only when enabled by S2.
    #   4 - Trigger with internal timer. Select the time between two readouts with stime.
    #   5 - Automatic internal instant trigger at the end of the last readout.
    self.settings.camera_settings[self.drvno].sti_mode = int(config.get("board0","sti"))
    if self.settings.camera_settings[self.drvno].sti_mode == 4:
        self.settings.camera_settings[self.drvno].stime_in_microsec = int(config.get("board0","stimer"))

    # Block trigger input (bti) mode determines the signal on which one block of readouts is started :
    #   0 - External trigger on input I of PCIe board
    #   1 - External trigger on input S1 of PCIe board
    #   2 - External trigger on input S2 of PCIe board
    #   3 - External trigger when inputs S1 and S2 are high
    #   4 - Trigger with internal timer. Select the time between two blocks of readouts with btimer.
    #   5 - S1 chopper
    #   6 - S2 chopper
    #   7 - S1&S2 chopper
    self.settings.camera_settings[self.drvno].bti_mode = int(config.get("board0","bti"))
    if self.settings.camera_settings[self.drvno].bti_mode == 4:
        self.settings.camera_settings[self.drvno].btime_in_microsec = int(float(config.get("board0","btimer")))

    # Sensor type should match the sensor type of your camera :
    #   4 - HSVIS - High speed sensor for visible light. (sensor S14290)
    self.settings.camera_settings[self.drvno].SENSOR_TYPE = int(config.get("board0","sensorType"))

    # Camera system should match the model number of your camera :
    #   2 - 3030 (sensor S14290)
    self.settings.camera_settings[self.drvno].CAMERA_SYSTEM = int(config.get("board0","cameraSystem"))

    # Number of pixels in one sensor :
    #   1088 - Low speed max 97 kHz
    #   1024 - High speed max 103 kHz
    self.settings.camera_settings[self.drvno].PIXEL = int(config.get("board0","pixelcnt")) 

    # Array for output levels of each digital to analog converter.
    self.settings.camera_settings[self.drvno].dac_output[0][0] = int(config.get("board0","dacCameraChannel0"))
    self.settings.camera_settings[self.drvno].dac_output[0][1] = int(config.get("board0","dacCameraChannel1"))
    self.settings.camera_settings[self.drvno].dac_output[0][2] = int(config.get("board0","dacCameraChannel2"))
    self.settings.camera_settings[self.drvno].dac_output[0][3] = int(config.get("board0","dacCameraChannel3"))
    self.settings.camera_settings[self.drvno].dac_output[0][4] = int(config.get("board0","dacCameraChannel4"))
    self.settings.camera_settings[self.drvno].dac_output[0][5] = int(config.get("board0","dacCameraChannel5"))
    self.settings.camera_settings[self.drvno].dac_output[0][6] = int(config.get("board0","dacCameraChannel6"))
    self.settings.camera_settings[self.drvno].dac_output[0][7] = int(config.get("board0","dacCameraChannel7"))

    # Create a variable of type uint8_t
    number_of_boards = ctypes.c_uint8(0)
    # Get the pointer the variable
    ptr_number_of_boards = ctypes.pointer(number_of_boards)
    # Initialize the driver and pass the created pointer to it. number_of_boards should show the number of detected PCIe boards after the next call.
    status = self.dll.DLLInitDriver(ptr_number_of_boards)
    # Check the status code after each DLL call. When it is not 0, which means there is no error, an exception is raised. The error message will be displayed and the script will stop.
    if(status != 0):
        raise BaseException(self.dll.DLLConvertErrorCodeToMsg(status))

    # Initialize the measurement.
    status = self.dll.DLLInitMeasurement(self.settings)
    if(status != 0):
        raise BaseException(self.dll.DLLConvertErrorCodeToMsg(status))
    
    return self

def init_measure(self):

    # Initialize the measurement.
    status = self.dll.DLLInitMeasurement(self.settings)
    if(status != 0):
        raise BaseException(self.dll.DLLConvertErrorCodeToMsg(status))

def measurement_running(self):
    """
        Whether the board still considers a measurement to be in progress.
    """
    return bool(self.dll.DLLGetIsRunning())


def abort_measure(self):
    """
        Stops a measurement the board is still running.
        The export is DLLAbortMeasurement. An earlier version of this called DLLStopMeasurement,
        which this DLL does not export, and swallowed the resulting AttributeError: every timeout
        therefore left the board running, and the next acquisition either failed with 'Measurement
        is already running' or blocked with no way out.
    """
    self.dll.DLLAbortMeasurement()


def wait_for_trigger(self, timeout_s):
    """
        Waits until the board reports a scan trigger, and raises if none appears.
        Used before committing to the blocking start, which cannot be interrupted: this way an
        input with no signal on it is reported instead of freezing the caller.
        input:
            - timeout_s (float): how long to wait for the first trigger
    """
    """ Both take a pointer to the flag as their second argument. Calling them with the board number
    alone compiles and runs, and corrupts memory: it cost an access violation to find out. """
    detected = ctypes.c_uint8(0)
    ptr_detected = ctypes.pointer(detected)
    self.dll.DLLResetScanTriggerDetected(self.drvno, ptr_detected)
    deadline = time.monotonic() + timeout_s
    while True:
        self.dll.DLLGetScanTriggerDetected(self.drvno, ptr_detected)
        if detected.value:
            break
        if time.monotonic() > deadline:
            self.dll.DLLOpenShutter(self.drvno)
            raise TimeoutError(
                'No trigger detected after %.1f s. The board is configured to start its readouts '
                'on an external signal (sti=%d) and nothing is arriving on that input.'
                % (timeout_s, self.settings.camera_settings[self.drvno].sti_mode))
        time.sleep(0.001)


def measure(self, use_blocking_call=True, timeout_s=None):
    """
        Runs one measurement and returns the spectrum averaged over samples and blocks.
        input:
            - use_blocking_call (bool): kept for compatibility. The non-blocking start returns
              'An unknown error occurred' on this board, checked against the instrument, so the
              blocking call is the only one that actually starts a measurement.
            - timeout_s (float): when set, wait this long for a trigger before starting. Leave None
              when the board drives itself, where the readouts are guaranteed to come.
    """
    """ Clear a measurement the board may still be running from a previous attempt. Without this an
    acquisition that was aborted, timed out or killed leaves the board busy, and every later one
    either fails with 'Measurement is already running' or never returns. """
    if measurement_running(self):
        abort_measure(self)

    # The sensor S14290 is a high speed sensor and is not completely cleared by one read out.
    # Therefore it may not be used without a reset signal, or following readouts have a crosstalk.
    status = self.dll.DLLCloseShutter(self.drvno)
    if(status != 0):
        raise BaseException(self.dll.DLLConvertErrorCodeToMsg(status))

    """ The blocking call has no way out, so anything that depends on an external signal waits for a
    trigger to actually appear first. On the internal timer the measurement takes as long as the
    timers say -- 0.11 s for ten readouts at 10 ms, measured -- and is entered directly. """
    if timeout_s is not None:
        wait_for_trigger(self, timeout_s)

    # This is the blocking call: it returns once the measurement is finished, so no data is read before it is all collected.
    status = self.dll.DLLStartMeasurement_blocking()
    if(status != 0):
        raise RuntimeError(self.dll.DLLConvertErrorCodeToMsg(status))

    # This block is showing you how to get all data of the whole measurement with one DLL call
    data_buffer = (ctypes.c_uint16 * (self.settings.camera_settings[self.drvno].PIXEL * (self.settings.nos) * self.settings.camera_settings[self.drvno].CAMCNT * self.settings.nob))(0)
    ptr_data_buffer = ctypes.pointer(data_buffer)
    status = self.dll.DLLCopyAllData(self.drvno, ptr_data_buffer)

    if(status != 0):
        raise BaseException(self.dll.DLLConvertErrorCodeToMsg(status))
    
    status = self.dll.DLLOpenShutter(self.drvno)
    if(status != 0):
        raise BaseException(self.dll.DLLConvertErrorCodeToMsg(status))

    # Convert ctypes array to numpy
    arr = np.ctypeslib.as_array(data_buffer)

    # Reshape to [nob, nos, PIXEL]
    arr = arr.reshape(self.settings.nob, self.settings.nos, self.settings.camera_settings[self.drvno].PIXEL)
    # Example: first block, first sample : arr[0, 0, :]
    

    # Remove the first 5 samples
    arr_trim = arr[:, 4:, :] # shape: [nob, nos-5, PIXEL]


    # Average over samples
    avg_over_samples = np.mean(arr_trim, axis=1)  # shape: [nob, PIXEL]


    # Average over blocks
    final_avg = np.mean(avg_over_samples, axis=0)  # shape: [PIXEL]
    return final_avg

def exit(self):

    # Exit the driver
    status = self.dll.DLLExitDriver()
    if(status != 0):
        raise BaseException(self.dll.DLLConvertErrorCodeToMsg(status))
