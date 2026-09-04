import requests
import numpy as np
import serial
#from serial.tools import list_ports
from PyQt5 import QtCore
import time
from collections import defaultdict


class ArduinoDemo(QtCore.QThread):
    name = 'optical_shutters'

    def __init__(self, port):
        super(ArduinoDemo,self).__init__()

        self.parameter_dict = defaultdict()

        #setting up variables for 3 shutters
        self.parameter_display_dict = defaultdict(dict)
        self.stop = False

        self.parameter_dict['filter_wheel_1'] = 50
        self.parameter_display_dict['filter_wheel_1']['val'] = 50
        self.parameter_display_dict['filter_wheel_1']['unit'] = ' deg'
        self.parameter_display_dict['filter_wheel_1']['max'] = 360
        self.parameter_display_dict['filter_wheel_1']['read'] = False

        self.parameter_dict['filter_wheel_2'] = 50
        self.parameter_display_dict['filter_wheel_2']['val'] = 50
        self.parameter_display_dict['filter_wheel_2']['unit'] = ' deg'
        self.parameter_display_dict['filter_wheel_2']['max'] = 360
        self.parameter_display_dict['filter_wheel_2']['read'] = False

        self.parameter_dict['filter_wheel_3'] = 50
        self.parameter_display_dict['filter_wheel_3']['val'] = 50
        self.parameter_display_dict['filter_wheel_3']['unit'] = ' deg'
        self.parameter_display_dict['filter_wheel_3']['max'] = 360
        self.parameter_display_dict['filter_wheel_3']['read'] = False

        self.parameter_display_dict['laser_diode']['val'] = 0
        self.parameter_display_dict['laser_diode']['unit'] = ' '
        self.parameter_display_dict['laser_diode']['max'] = 300
        self.parameter_display_dict['laser_diode']['read'] = False

        # defining waitTime
        self.WaitTime = 0.1

    def set_parameter(self, parameter, value):
        if parameter == 'filter_wheel_1':
            self.parameter_dict['filter_wheel_1'] = value
        elif parameter == 'filter_wheel_2':
            self.parameter_dict['filter_wheel_2'] = value

        elif parameter == 'filter_wheel_3':
            self.parameter_dict['filter_wheel_3'] = value

        elif parameter == 'laser_diode':
            self.parameter_dict['laser_diode'] = value