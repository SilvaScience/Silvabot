import time
from PyQt5 import QtCore
from collections import defaultdict

class HarpiaDemo():
    
    name = "HarpiaDemo"

    def __init__(self):
        super(HarpiaDemo, self).__init__()
        
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

        self.parameter_dict = {}
        for key in self.parameter_display_dict.keys():
            self.parameter_dict[key] = self.parameter_display_dict[key]["val"]

        self.UpdateWorker_Delay = UpdateWorker_Delay()
        self.UpdateWorker_Delay.new_Delay.connect(self.update_delay)
        self.UpdateWorker_Delay.start()

    def set_parameter(self, parameter, value):
        if parameter == "targer_delay":
            self.update_target_delay(value)

        elif parameter == "pump_shutter":
            self.update_pump_shutter(value)

        elif parameter == "third_beam_shutter":
            self.update_third_beam_shutter(value)

    def update_target_delay(self, target):
        print(f"Moving delay to {target} ps")
        self.UpdateWorker_Delay.target = target

    def update_delay(self, delay):
        self.parameter_dict["delay"] = delay

    def update_pump_shutter(self, state):
        print(f"Pump shutter set to {state}")
        self.parameter_dict["pump_shutter"] = state

    def update_third_beam_shutter(self, state):
        print(f"Third beam shutter set to {state}")
        self.parameter_dict["third_beam_shutter"] = state

class UpdateWorker_Delay(QtCore.QThread):
    new_Delay = QtCore.pyqtSignal(float)

    def __init__(self):
        super().__init__()
        self.stop = False
        self.waitTime = 0.1
        self.current = 0
        self.target = 0

    def run(self):
        while not self.stop:
            # simulate movement
            if self.current < self.target:
                self.current += 0.1
            elif self.current > self.target:
                self.current -= 0.1
            
            self.new_Delay.emit(self.current_delay)
            time.sleep(self.waitTime)

    

