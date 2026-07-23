"""
Code to control Harpia's delay line and shutters
"""
from lightcon import Harpia
import time
from PyQt5 import QtCore
from collections import defaultdict

class HarpiaDevice():

    name = "Harpia"

    def __init__(self):
        super(HarpiaDevice, self).__init__()
        
        # setting up the parameter dict
        self.parameter_display_dict = defaultdict(dict)

        # Shutter pump and third beam
        self.parameter_display_dict["pump_shutter"]["val"] = False
        self.parameter_display_dict["pump_shutter"]["unit"] = " "
        self.parameter_display_dict["pump_shutter"]["read"] = False

        self.parameter_display_dict["third_beam_shutter"]["val"] = False
        self.parameter_display_dict["third_beam_shutter"]["unit"] = " "
        self.parameter_display_dict["third_beam_shutter"]["read"] = False

        # Delay position
        self.parameter_display_dict["delay_position"]["val"] = 0.0
        self.parameter_display_dict["delay_position"]["unit"] = "ps"
        #self.parameter_display_dict['position']['max'] = 10000 # to be verified
        self.parameter_display_dict["delay_position"]["read"] = True

        # Target delay
        self.parameter_display_dict["target_delay"]["val"] = 0.0
        self.parameter_display_dict["target_delay"]["unit"] = "ps"
        #self.parameter_display_dict["target_delay"]["max"] = 10000 # to be verified
        self.parameter_display_dict["target_delay"]["read"] = False

        # Scan position
        self.parameter_display_dict["scan_initial_position"]["val"] = 0.0
        self.parameter_display_dict["scan_initial_position"]["unit"] = "ps"
        #self.parameter_display_dict["scan_initial_position"]["max"] = 10000 # to be verified
        self.parameter_display_dict["scan_initial_position"]["read"] = False

        self.parameter_display_dict["scan_final_position"]["val"] = 0.0
        self.parameter_display_dict["scan_final_position"]["unit"] = "ps"
        #self.parameter_display_dict["scan_final_position"]["max"] = 10000 # to be verified
        self.parameter_display_dict["scan_final_position"]["read"] = False

        # Fast access dictionary
        self.parameter_dict = {}
        for key in self.parameter_display_dict.keys():
            self.parameter_dict[key] = self.parameter_display_dict[key]["val"]

        # Initialize connection to Harpia
        ip_adress = "192.168.1.134"
        self.harpia = Harpia(ip_adress)

        if not self.harpia.connected:
            raise Exception("Could not connect to Harpia")
        
        print("Connected to Harpia")

        # start updating position
        self.UpdateWorker_Delay = UpdateWorker_Delay(self.harpia)
        self.UpdateWorker_Delay.new_Delay.connect(self.update_delay)
        self.UpdateWorker_Delay.start()  

        # Silvabot parameters interface
        def set_parameter(self, parameter, value):
            if parameter == "pump_shutter":
                self.update_pump_shutter(value)

            elif parameter == "third_beam_shutter":
                self.update_third_beam_shutter(value)
            
            elif parameter == "target_delay":
                self.update_target_delay(value)
            
            elif parameter == "scan_initial_position":
                self.update_scan_initial_position(value)
            
            elif parameter == "scan_final_position":
                self.update_scan_final_position(value)
            
        
        # Shutter
        def update_pump_shutter(self, state):
            if state:
                print("Opening pump shutter")
                self.harpia.open_pump_shutter()
            
            else:
                print("Closing pump shutter")
                self.harpia.close_pump_shutter()








