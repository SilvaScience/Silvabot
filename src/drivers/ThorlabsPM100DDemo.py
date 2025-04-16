"""
Created on Mon Oct 10 20:10:53 2022

@author: DT
Hardware class to control cryostat. All hardware classes require a definition of
parameter_dict (set write and read parameter)
parameter_display_dict (set Spinbox options)
set_parameter function (assign set functions)

"""

from PyQt5 import QtCore, QtWidgets
import time
from collections import defaultdict
import socket
import sys
import json
import requests
import numpy as np
import pyvisa


class ThorlabsPM100DDemo(QtCore.QThread):
    name = 'powermeter'

    def __init__(self):
        super(ThorlabsPM100DDemo, self).__init__()

        # connect to Juno
        #self.pm = ThorlabsPM100DInterface()

        # set parameter dict
        self.parameter_dict = defaultdict()

        # setting up variables, open array
        self.stop = False

        """ Set up the parameter dict. 
        Here, all properties of parameters to be handled by the parameter dict are defined."""
        self.parameter_display_dict = defaultdict(dict)
        self.parameter_display_dict['wl']['val'] = 500
        self.parameter_display_dict['wl']['unit'] = ' nm'
        self.parameter_display_dict['wl']['max'] = 1100
        self.parameter_display_dict['wl']['min'] = 200
        self.parameter_display_dict['wl']['read'] = False
        self.parameter_display_dict['current_power']['val'] = 2
        self.parameter_display_dict['current_power']['unit'] = ' nW'
        self.parameter_display_dict['current_power']['max'] = 1E9
        self.parameter_display_dict['current_power']['min'] = -1E6
        self.parameter_display_dict['current_power']['read'] = True
        self.parameter_display_dict['offset']['val'] = 0
        self.parameter_display_dict['offset']['unit'] = ' nW'
        self.parameter_display_dict['offset']['max'] = 1E9
        self.parameter_display_dict['offset']['read'] = False


        # set up parameter dict that only contains value. (faster to access)
        self.parameter_dict = {}
        for key in self.parameter_display_dict.keys():
            self.parameter_dict[key] = self.parameter_display_dict[key]['val']

        # defining waitTime
        self.waitTime = 0.1

        # set range to Auto
        #self.pm.set_auto_range(auto=True)

        # start updating temp
        self.UpdateWorker = UpdateWorker()
        self.UpdateWorker.new_power.connect(self.update_power)
        self.UpdateWorker.start()

    def set_parameter(self, parameter, value):
        if parameter == 'wl':
            pass
            #self.pm.set_wavelength(value)
        elif parameter == 'offset':
            self.parameter_dict['offset'] = value
        else:
            pass

    def update_power(self, new_curr_power):
        self.parameter_dict['current_power'] = new_curr_power - self.parameter_dict['offset']



class UpdateWorker(QtCore.QThread):
    new_power = QtCore.pyqtSignal(float)

    def __init__(self):
        super(UpdateWorker, self).__init__()
        self.avg_time = 2
        self.wait_time = 0.1
        self.stop = False
        self.last_time = time.time()
        self.current_power = 0
        self.idx = 0

    def run(self):
        while not self.stop:
            # calling the read power function
            self.current_power = np.random.rand() + 5
            # waiting to remeasure the power
            time.sleep(self.wait_time)
            self.new_power.emit(self.current_power)



class ThorlabsPM100DInterface(object):
    """
    Thorlabs PM100D power meter

    uses the PyVISA 1.5 library to communicate over USB.
    """

    def __init__(self, port="USB0::0x1313::0x8075::P5002302::INSTR", debug=False):
        self.name = 'PM100D'
        self.port = port
        self.debug = debug
        self.TRIES_BEFORE_FAILURE = 10
        self.RETRY_SLEEP_TIME = 0.010  # in seconds

        self.visa_resource_manager = pyvisa.ResourceManager()

        if debug:
            print('List of resources')
            print(self.visa_resource_manager.list_resources(query='?*'))

        self.pm = self.visa_resource_manager.open_resource(port)

        self.idn = self.query("*IDN?")

        self.sensor_idn = self.query("SYST:SENS:IDN?")
        if debug:
            print('Device name:' + self.sensor_idn)

        self.write("CONF:POW")  # set to power meaurement

        self.wavelength_min = float(self.query("SENS:CORR:WAV? MIN"))
        self.wavelength_max = float(self.query("SENS:CORR:WAV? MAX"))
        self.get_wavelength()

        self.get_attenuation_dB()  # does not exist

        self.write("SENS:POW:UNIT W")  # set to Watts
        self.power_unit = self.query("SENS:POW:UNIT?")

        self.get_auto_range()

        self.get_average_count()  # does not exist

        self.get_power_range()
        self.measure_power()
        self.measure_frequency()  # does not exist

    def query(self, cmd):
        resp = self.pm.query(cmd)
        return resp

    def write(self, cmd):
        resp = self.pm.write(cmd)

    def get_wavelength(self):
        try_count = 0
        while True:
            try:
                self.wl = float(self.query("SENS:CORR:WAV?"))
                break
            except:
                if try_count > 9:
                    break
                else:
                    time.sleep(self.RETRY_SLEEP_TIME)  # take a rest..
                    try_count = try_count + 1
        return self.wl

    def set_wavelength(self, wl):
        try_count = 0
        while True:
            try:
                self.write("SENS:CORR:WAV %f" % wl)
                time.sleep(0.005)  # Sleep for 5 ms before rereading the wl.
                break
            except:
                if try_count > 9:
                    time.sleep(0.005)  # Sleep for 5 ms before rereading the wl.
                    break
                else:
                    time.sleep(self.RETRY_SLEEP_TIME)  # take a rest..
                    try_count = try_count + 1
        return self.get_wavelength()

    def get_attenuation_dB(self):
        # in dB (range for 60db to -60db) gain or attenuation, default 0 dB
        self.attenuation_dB = float(self.query("SENS:CORR:LOSS:INP:MAGN?"))
        return self.attenuation_dB

    def get_average_count(self):
        """each measurement is approximately 3 ms.
        returns the number of measurements
        the result is averaged over"""
        self.average_count = int(self.query("SENS:AVER:COUNt?"))
        return self.average_count

    def set_average_count(self, cnt):
        """each measurement is approximately 3 ms.
        sets the number of measurements
        the result is averaged over"""
        self.write("SENS:AVER:COUNT %i" % cnt)
        return self.get_average_count()

    def measure_power(self):
        self.power = float(self.query("MEAS:POW?"))
        return self.power

    def get_power_range(self):
        # un tested
        self.power_range = self.query("SENS:POW:RANG:UPP?")  # CHECK RANGE
        return self.power_range

    def set_power_range(self, range):
        # un tested
        self.write("SENS:POW:RANG:UPP {}".format(range))

    def get_auto_range(self):
        resp = self.query("SENS:POW:RANG:AUTO?")
        self.auto_range = bool(int(resp))
        return self.auto_range

    def set_auto_range(self, auto=True):
        if auto:
            self.write("SENS:POW:RANG:AUTO ON")  # turn on auto range
        else:
            self.write("SENS:POW:RANG:AUTO OFF")  # turn off auto range

    def measure_frequency(self):
        self.frequency = self.query("MEAS:FREQ?")
        return self.frequency

    def get_zero_magnitude(self):
        resp = self.query("SENS:CORR:COLL:ZERO:MAGN?")
        self.zero_magnitude = float(resp)
        return self.zero_magnitude

    def get_zero_state(self):
        resp = self.query("SENS:CORR:COLL:ZERO:STAT?")
        self.zero_state = bool(int(resp))
        return self.zero_state

    def run_zero(self):
        self.write("SENS:CORR:COLL:ZERO:INIT")
        # resp = self.query("SENS:CORR:COLL:ZERO:INIT")
        # return resp

    def get_photodiode_response(self):
        resp = self.query("SENS:CORR:POW:PDIOde:RESP?")
        # resp = self.query("SENS:CORR:VOLT:RANG?")
        # resp = self.query("SENS:CURR:RANG?")

        self.photodiode_response = float(resp)  # A/W
        return self.photodiode_response

    def measure_current(self):
        resp = self.query("MEAS:CURR?")
        self.current = float(resp)
        return self.current

    def get_current_range(self):
        resp = self.query("SENS:CURR:RANG:UPP?")
        self.current_range = float(resp)
        return self.current_range

    def close(self):
        return self.pm.close()