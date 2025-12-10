"""
@author: Andres Rojas Sanchez
Hardware class to control LakeShore temperature controller. All hardware classes require a definition of
parameter_dict (set write and read parameter)
parameter_display_dict (set Spinbox options)
set_parameter function (assign set functions)

TO DOs:
- PID values are not yet calibrated. 
- Heater range is set for all temperatures to medium. We might want to adapt this at some point. 

NOTES:
#LakeShore 335 Temperature Controller
#This script reads the temperature values and controls the heater
"""

from lakeshore import Model335, Model335InputSensorSettings
from time import sleep
from PyQt5 import QtCore
from collections import defaultdict


class TCnHLakeshore(QtCore.QThread):

    name = 'tc'
    temperature_updated=QtCore.pyqtSignal(dict)

    def __init__(self):
        super(TCnHLakeshore,self).__init__()
       
        try:
            #Communication with the device
            self.my_model_335 = Model335(57600) # argument is baud rate

            #Set the sensor parameters
            self.sensor_settings = Model335InputSensorSettings(self.my_model_335.InputSensorType.DIODE, True, False,
                                              self.my_model_335.InputSensorUnits.KELVIN,
                                              self.my_model_335.DiodeRange.TWO_POINT_FIVE_VOLTS)
           
            # Apply settings to input A of the instrument
            self.my_model_335.set_input_sensor("A", self.sensor_settings)
            self.my_model_335.set_input_sensor("B", self.sensor_settings)

            # Set diode excitation current on channel A to 10uA
            self.my_model_335.set_diode_excitation_current("A", self.my_model_335.DiodeCurrent.TEN_MICROAMPS)
            self.my_model_335.set_diode_excitation_current("B", self.my_model_335.DiodeCurrent.TEN_MICROAMPS)

            #Get the temperature values, 0 element is the sample one.
            self.temperature_reading = self.my_model_335.get_all_kelvin_reading()
 
        except:
            print("Lakeshore not connected")
            self.my_model_335=None
            self.temperature_reading = [0, 0]

        self.parameter_display_dict = {}
        
        # setting up variables, open array
        self.set_T = []
        self.current_T = []
        self.stop = False

        #Values of the temperature A (the sample one)
        self.parameter_display_dict['TempA'] = {}
        self.parameter_display_dict['TempA']['val'] = self.temperature_reading[0]
        self.parameter_display_dict['TempA']['unit'] = 'K'
        self.parameter_display_dict['TempA']['max'] = 350
        self.parameter_display_dict['TempA']['min'] = 1
        self.parameter_display_dict['TempA']['read'] = True

        #Values of the temperature B (non sample one)
        self.parameter_display_dict['TempB'] = {}
        self.parameter_display_dict['TempB']['val'] = self.temperature_reading[1]
        self.parameter_display_dict['TempB']['unit'] = 'K'
        self.parameter_display_dict['TempB']['max'] = 350
        self.parameter_display_dict['TempB']['min'] = 1
        self.parameter_display_dict['TempB']['read'] = True

        #Values of the setpoint
        self.parameter_display_dict['SetPoint'] = {}
        self.parameter_display_dict['SetPoint']['val'] = 300
        self.parameter_display_dict['SetPoint']['unit'] = 'K'
        self.parameter_display_dict['SetPoint']['max'] = 350
        self.parameter_display_dict['SetPoint']['min'] = 1
        self.parameter_display_dict['SetPoint']['read'] = False

        # set up parameter dict that only contains value. (faster to access)
        self.parameter_dict = {}
        for key in self.parameter_display_dict.keys():
            self.parameter_dict[key] = self.parameter_display_dict[key]['val']

        # defining waitTime
        self.waitTime = 0.1

        # start updating temp
        self.UpdateWorker = UpdateWorker(self.my_model_335)
        self.UpdateWorker.new_T.connect(self.update_temp)
        self.UpdateWorker.start()

    def set_parameter(self, param, value):

        if param == 'SetPoint':
            self.parameter_dict['SetPoint'] = value
            self.my_model_335.set_heater_setup_one(self.my_model_335.HeaterResistance.HEATER_25_OHM, 0.5, self.my_model_335.HeaterOutputDisplay.POWER) #MAX CURRENT 0.7A
            self.my_model_335.set_control_setpoint(1, value)
            self.my_model_335.set_heater_output_mode(1,self.my_model_335.HeaterOutputMode.CLOSED_LOOP,self.my_model_335.InputSensor.CHANNEL_A,powerup_enable=False)
            self.my_model_335.set_heater_range(1, self.my_model_335.HeaterRange.MEDIUM)

    def update_temp(self, new_T):
        self.parameter_dict['TempA'] = new_T[0]
        self.parameter_dict['TempB'] = new_T[1]


class UpdateWorker(QtCore.QThread):
    new_T = QtCore.pyqtSignal(list)

    def __init__(self, model):
        super(UpdateWorker, self).__init__()
        self.stop = False
        self.waitTime = 0.1
        self.my_model_335 = model

    def run(self):
        while not self.stop:
            # calling the read temperature function
            self.readtemp = self.my_model_335.get_all_kelvin_reading()

            # waiting to remeasure the temperature
            sleep(self.waitTime)
            self.new_T.emit(self.readtemp)

