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







