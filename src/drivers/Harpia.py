"""
Code to control Harpia's delay line and shutters
"""
from lightcon.harpia import Harpia
import time
from PyQt5 import QtCore
from collections import defaultdict
import sys

class Harpia():

    name = "Harpia"

    def __init__(self):
        super(Harpia, self).__init__()
        
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
        self.parameter_display_dict["delay"]["val"] = 0.0
        self.parameter_display_dict["delay"]["unit"] = "ps"
        #self.parameter_display_dict['delay']['max'] = 10000 # to be verified
        self.parameter_display_dict["delay"]["read"] = True

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
        ip_address = "192.168.1.134"
        harpia = Harpia(ip_address)

        if not harpia.connected:
            sys.exit("Could not connect to Harpia")
        
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
        """    
        elif parameter == "scan_initial_position":
            self.update_scan_initial_position(value)
            
        elif parameter == "scan_final_position":
            self.update_scan_final_position(value)
        """    
        
    # Shutter
    def update_pump_shutter(self, state):
        if state:
            print("Opening pump shutter")
            self.harpia.open_pump_shutter()
            
        else:
            print("Closing pump shutter")
            self.harpia.close_pump_shutter()
            
        self.parameter_dict["pump_shutter"] = state
        
    def update_third_beam_shutter(self, state):
        if state:
            print("Opening third beam shutter")
            self.harpia.open_third_beam_shutter()
            
        # There is no close function for the third beam shutter in the Harpia API, so we will close all shutters instead
        else:
            print("Closing all shutters")
            self.harpia.close_all_shutters()

        self.parameter_dict["third_beam_shutter"] = state
        
    # Delay line
    def update_target_delay(self, target):
        print(f"Moving delay line to {target} ps")
        self.harpia.set_delay_line_target_delay(target)

    def update_delay(self,delay):
        self.parameter_dict["delay"] = delay

    def position_delay(self, target, tolerance=0.001):
        while True:
            current = self.harpia.delay_line_actual_delay()
            if abs(current-target) < tolerance:
                break
            time.sleep(0.2)

class UpdateWorker_Delay(QtCore.QThread):
    new_Delay = QtCore.pyqtSignal(float)
    
    def __init__(self, harpia):
        super().__init__()
        self.harpia = harpia
        self.stop = False
        self.waitTime = 0.05

    def run(self):
        while not self.stop:
            delay = self.read_delay()
            if delay is not None:
                self.new_Delay.emit(delay)
                time.sleep(self.waitTime)
    
    def read_delay(self):
        try:
            return self.harpia.delay_line_actual_delay()
        except:
            return None
        

    

        









