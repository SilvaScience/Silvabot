#TCLakeshoreDemo
#LakeShore 335 Temperature Controller
#This script just read the temperature values


#import csv
from lakeshore import Model335, Model335InputSensorSettings
from time import sleep
from PyQt5 import QtCore

class TCLakeshore(QtCore.QThread):

    name = 'tc'

    temperature_updated=QtCore.pyqtSignal(dict)

    def __init__(self):

        super(TCLakeshore,self).__init__()

        #Communication with the device
        try:
            self.my_model_335 = Model335(57600)

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
            print("COM not connected")
            self.my_model_335=None
            self.temperature_reading = [0, 0]
        

        #Parameter values
        self.parameter_display_dict = {}

        self.parameter_display_dict['Temperature A'] = {}
        self.parameter_display_dict['Temperature A']['val'] = self.temperature_reading[0]
        self.parameter_display_dict['Temperature A']['unit'] = 'K'
        self.parameter_display_dict['Temperature A']['max'] = 400
        self.parameter_display_dict['Temperature A']['min'] = 1
        self.parameter_display_dict['Temperature A']['read'] = True

        self.parameter_display_dict['Temperature B'] = {}
        self.parameter_display_dict['Temperature B']['val'] = self.temperature_reading[1]
        self.parameter_display_dict['Temperature B']['unit'] = 'K'
        self.parameter_display_dict['Temperature B']['max'] = 400
        self.parameter_display_dict['Temperature B']['min'] = 1
        self.parameter_display_dict['Temperature B']['read'] = True

        self.parameter_dict = {}
        for key in self.parameter_display_dict.keys():
            self.parameter_dict[key] = self.parameter_display_dict[key]['val']

        self.running = True


    #This function reads the temperature values each second
    def run(self):

        while self.running:
                temperatures = self.my_model_335.get_all_kelvin_reading() 
                self.parameter_display_dict['Temperature A']['val']=temperatures[0]
                self.parameter_display_dict['Temperature B']['val']=temperatures[1]
 
                for key in self.parameter_display_dict.keys():
                    self.parameter_dict[key] = self.parameter_display_dict[key]['val']

                #  Emite los valores actualizados hacia la GUI
                self.temperature_updated.emit(self.parameter_dict)

        
        sleep(1)  


    def set_parameter(self, param, value):

        if param in self.parameter_dict:
            self.parameter_dict[param] = value
            if param in self.parameter_display_dict:
                self.parameter_display_dict[param]['val'] = value
            print(f"Updated {param} to {value}")
        else:
            print(f"Parameter {param} not found in TCLakeshoreDemo")
