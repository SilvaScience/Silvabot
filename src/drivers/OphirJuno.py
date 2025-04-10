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
import win32com.client
import numpy as np


class OphirJuno(QtCore.QThread):
    name = 'OphirJuno'

    def __init__(self):
        super(OphirJuno, self).__init__()

        # connect to Juno
        self.connected = False
        self.OphirCOM = win32com.client.Dispatch("OphirLMMeasurement.CoLMMeasurement")
        # Stop & Close all devices
        self.OphirCOM.StopAllStreams()
        self.OphirCOM.CloseAll()
        # Scan for connected Devices
        DeviceList = self.OphirCOM.ScanUSB()
        for Device in DeviceList:  # if any device is connected
            self.DeviceHandle = self.OphirCOM.OpenUSBDevice(Device)  # open first device
            exists = self.OphirCOM.IsSensorExists(self.DeviceHandle, 0)
            if exists:
                print('Powermeter S/N {0} connected'.format(Device))
                self.connected = True

        # set parameter dict
        self.parameter_dict = defaultdict()

        # setting up variables, open array
        self.stop = False
        self.parameter_dict['wl'] = 550
        self.parameter_dict['avg_time'] = 2
        self.parameter_dict['current_power'] = 1
        self.parameter_dict['avg_power'] = 2
        self.parameter_dict['offset'] = 0
        self.parameter_dict['PM_filter'] = 0
        self.parameter_display_dict = defaultdict(dict)
        self.parameter_display_dict['wl']['val'] = 550
        self.parameter_display_dict['wl']['unit'] = ' nm'
        self.parameter_display_dict['wl']['max'] = 1100
        self.parameter_display_dict['wl']['min'] = 200
        self.parameter_display_dict['wl']['read'] = False
        self.parameter_display_dict['avg_time']['val'] = 2
        self.parameter_display_dict['avg_time']['unit'] = ' s'
        self.parameter_display_dict['avg_time']['max'] = 1100
        self.parameter_display_dict['avg_time']['read'] = False
        self.parameter_display_dict['current_power']['val'] = 2
        self.parameter_display_dict['current_power']['unit'] = ' nW'
        self.parameter_display_dict['current_power']['max'] = 1E9
        self.parameter_display_dict['current_power']['min'] = -1E6
        self.parameter_display_dict['current_power']['read'] = True
        self.parameter_display_dict['avg_power']['val'] = 2
        self.parameter_display_dict['avg_power']['unit'] = ' nW'
        self.parameter_display_dict['avg_power']['max'] = 1E9
        self.parameter_display_dict['avg_power']['min'] = -1E6
        self.parameter_display_dict['avg_power']['read'] = True
        self.parameter_display_dict['offset']['val'] = 0
        self.parameter_display_dict['offset']['unit'] = ' nW'
        self.parameter_display_dict['offset']['max'] = 1E9
        self.parameter_display_dict['offset']['read'] = False
        self.parameter_display_dict['PM_filter']['val'] = 0
        self.parameter_display_dict['PM_filter']['unit'] = ' pos'
        self.parameter_display_dict['PM_filter']['max'] = 2
        self.parameter_display_dict['PM_filter']['read'] = False

        # defining waitTime
        self.waitTime = 0.1

        # set wavelength to last in list
        self.OphirCOM.SetWavelength(self.DeviceHandle, 0, 5)

        # set range to Auto
        self.OphirCOM.SetRange(self.DeviceHandle, 0, 0)

        # start updating temp
        self.UpdateWorker = UpdateWorker(self.OphirCOM, self.DeviceHandle)
        self.UpdateWorker.new_power.connect(self.update_power)
        self.UpdateWorker.start()

    def set_parameter(self, parameter, value):
        if parameter == 'wl':
            self.OphirCOM.StopAllStreams()
            self.OphirCOM.ModifyWavelength(self.DeviceHandle, 0, 5, int(value))
            self.OphirCOM.StartStream(self.DeviceHandle, 0)
        elif parameter == 'avg_time':
            self.UpdateWorker.change_avg_array(value)
        elif parameter == 'offset':
            self.parameter_dict['offset'] = value
        elif parameter == 'PM_filter':
            self.OphirCOM.StopAllStreams()
            self.OphirCOM.SetFilter(self.DeviceHandle, 0, int(value))
            self.OphirCOM.StartStream(self.DeviceHandle, 0)
        else:
            pass

    def update_power(self, new_curr_power, new_avg_power):
        self.parameter_dict['current_power'] = new_curr_power - self.parameter_dict['offset']
        self.parameter_dict['avg_power'] = new_avg_power - self.parameter_dict['offset']


class UpdateWorker(QtCore.QThread):
    new_power = QtCore.pyqtSignal(float, float)

    def __init__(self, OphirCOM, DeviceHandle):
        super(UpdateWorker, self).__init__()
        self.OphirCOM = OphirCOM
        self.DeviceHandle = DeviceHandle
        self.current_power = 0
        self.avg_power = 0
        self.avg_time = 2
        self.wait_time = 0.1
        self.stop = False
        self.last_time = time.time()
        self.avg_array_size = int(self.avg_time / self.wait_time)
        self.power_array = np.zeros(self.avg_array_size)
        self.idx = 0

    def run(self):
        self.OphirCOM.StartStream(self.DeviceHandle, 0)
        while not self.stop:
            # calling the read power function
            self.read_power()
            # waiting to remeasure the power
            time.sleep(self.wait_time)
            self.new_power.emit(self.current_power, self.avg_power)

    def change_avg_array(self, avg_time):
        self.avg_array_size = int(avg_time / self.wait_time)
        self.power_array = np.zeros(self.avg_array_size)

    def read_power(self):
        # read the current power
        data = self.OphirCOM.GetData(self.DeviceHandle, 0)
        if len(data[0]) > 0:
            self.idx = self.idx + 1
            if self.idx > self.avg_array_size - 1:
                self.idx = 0
            power_read = np.average(data[0])
            self.current_power = power_read*1E9
            self.power_array[self.idx] = power_read
            self.avg_power = np.average(self.power_array)*1E9
