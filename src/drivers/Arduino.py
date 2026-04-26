"""
Created on Wed Nov  19 13:26:53 2025

@author: DT
Hardware class to control Arduino. All hardware classes require a definition of
parameter_dict (set write and read parameter)
parameter_display_dict (set Spinbox options)
set_parameter function (assign set functions)

TO DO:
there is currently no homing for the filter wheels.
To options:
- mechanical switch that is flipped during rotation
- hard stop

"""

import serial
from PyQt5 import QtCore
import time
from collections import defaultdict
import subprocess

class Arduino(QtCore.QThread):
    name = 'optical_shutters'

    def __init__(self, port):
        self.port = port
        super(Arduino, self).__init__()
        self.ser = serial.Serial(self.port, 115200)
        time.sleep(1.75)
        self.parameter_dict = defaultdict()

        #setting up variables for 3 shutters
        self.parameter_display_dict = defaultdict(dict)
        self.stop = False

        self.parameter_dict['filter_wheel_1'] = 0
        self.parameter_display_dict['filter_wheel_1']['val'] = 0
        self.parameter_display_dict['filter_wheel_1']['unit'] = ' deg'
        self.parameter_display_dict['filter_wheel_1']['max'] = 360
        self.parameter_display_dict['filter_wheel_1']['read'] = False

        self.parameter_dict['filter_wheel_2'] = 0
        self.parameter_display_dict['filter_wheel_2']['val'] = 0
        self.parameter_display_dict['filter_wheel_2']['unit'] = ' deg'
        self.parameter_display_dict['filter_wheel_2']['max'] = 360
        self.parameter_display_dict['filter_wheel_2']['read'] = False

        self.parameter_dict['filter_wheel_3'] = 0
        self.parameter_display_dict['filter_wheel_3']['val'] = 0
        self.parameter_display_dict['filter_wheel_3']['unit'] = ' deg'
        self.parameter_display_dict['filter_wheel_3']['max'] = 360
        self.parameter_display_dict['filter_wheel_3']['read'] = False

        self.parameter_dict['laser_diode'] = 0
        self.parameter_display_dict['laser_diode']['val'] = 0
        self.parameter_display_dict['laser_diode']['unit'] = ' '
        self.parameter_display_dict['laser_diode']['max'] = 300
        self.parameter_display_dict['laser_diode']['read'] = False

        #defining waitTime
        self.WaitTime = 0.1

        # PROTOCOL FOR HOMING TO BE IMPLEMENTED
        #close all shutters to initialize
        #self.set_parameter('filter_wheel_1', 50)
        #time.sleep(1)
        #self.set_parameter('filter_wheel_2', 50)
        #time.sleep(1)
        #self.set_parameter('filter_wheel_3', 50)
        #time.sleep(1)

    def set_parameter(self, parameter, value):
        if parameter == 'filter_wheel_1':
            change_in_angle = self.parameter_dict['filter_wheel_1'] -value
            steps_to_move = round(change_in_angle*2048/360)
            self.update_shutter(1,steps_to_move)
            self.parameter_dict['filter_wheel_1'] = value
        elif parameter == 'filter_wheel_2':
            change_in_angle = self.parameter_dict['filter_wheel_2'] -value
            steps_to_move = round(change_in_angle*2048/360)
            self.update_shutter(2, steps_to_move)
            self.parameter_dict['filter_wheel_2'] = value
        elif parameter == 'filter_wheel_3':
            change_in_angle = self.parameter_dict['filter_wheel_3'] -value
            steps_to_move = round(change_in_angle*2048/360)
            self.update_shutter(3,steps_to_move)
            self.parameter_dict['filter_wheel_3'] = value
        elif parameter == 'laser_diode':
            command = 'LM=' + str(int(value))
            try:
                self.ser.write(command.encode())
            except serial.SerialTimeoutException:
                print(time.strftime('%H:%M:%S') + 'Arduino serial timeout exception')
                # self.restart()
            self.parameter_dict['laser_diode'] = value

    def update_shutter(self,shutter, set_angle):
        #set shutter1 to some degree
        command = 'SRV' + str(shutter) + '=' + str(set_angle)
        try:
            self.ser.write(command.encode())
            print(command)
            print(type(command))
        except serial.SerialTimeoutException:
            print(time.strftime('%H:%M:%S') + 'Arduino serial timeout exception')
            #self.restart()

    def restart(self):
        # function to restart arduino with devcon.exe. Requires admin privileges to function.
        """ This function is currently unused, but can be used in case of connection issues. """
        self.ser.close()
        print('Serial expection, reconnect')
        succeeded = False
        while not succeeded:
            try:
                #subprocess.run(
                #    [r'C:\Program Files (x86)\Windows Kits\10\Tools\10.0.22621.0\x64\devcon.exe', 'restart',
                #     'USB\VID_2341&PID_0043&REV_0001'])
                self.ser = serial.Serial(self.port, 115200, timeout=2, write_timeout=2)
                succeeded = True
                print('arduino reconnected')
                time.sleep(2)
            except serial.SerialException:
                print('arduino reconnection failed. Try again.')
