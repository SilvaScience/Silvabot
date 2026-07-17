from PyQt5 import QtCore
from collections import defaultdict
import time
import numpy as np

class PI863Demo():

    name = 'PI863Demo'

    def __init__(self):
        super(PI863Demo, self).__init__()

        # setting up the parameter dict
        self.parameter_dict = defaultdict()

        self.set_speed = []
        self.set_target_position = []
        self.position = []
        self.stop = False
        self.parameter_display_dict = defaultdict(dict)

        self.parameter_dict['set_speed'] = 0
        self.parameter_dict['set_target_position'] = 0
        self.parameter_dict['position'] = 0
        
        self.parameter_display_dict['set_speed']['val'] = 0
        self.parameter_display_dict['set_speed']['unit'] = ' mm/s'
        self.parameter_display_dict['set_speed']['max'] = 20
        self.parameter_display_dict['set_speed']['read'] = False

        self.parameter_display_dict['set_target_position']['val'] = 0
        self.parameter_display_dict['set_target_position']['unit'] = ' mm'
        self.parameter_display_dict['set_target_position']['max'] = 50
        self.parameter_display_dict['set_target_position']['read'] = False

        self.parameter_display_dict['position']['val'] = 0
        self.parameter_display_dict['position']['unit'] = ' mm'
        self.parameter_display_dict['position']['max'] = 50
        self.parameter_display_dict['position']['read'] = True

        # set up parameter dict that only contains value. (faster to access)
        self.parameter_dict = {}
        for key in self.parameter_display_dict.keys():
            self.parameter_dict[key] = self.parameter_display_dict[key]['val']

        # start updating speed
        self.UpdateWorker_Position = UpdateWorker_Position()
        self.UpdateWorker_Position.new_Position.connect(self.update_position)
        self.UpdateWorker_Position.start()

    def set_parameter(self,parameter,value):
        if parameter == 'set_speed':
            self.update_set_speed(value)
        if parameter == 'set_target_position':
            self.update_set_target_position(value)
        if parameter == 'position':
            self.update_position(value)
            self.position = value

    def update_set_speed(self, set_speed):
        print(f'Speed set to {set_speed}')
    
    def update_set_target_position(self, set_position):
        print(f'Moving to {set_position}')
        self.UpdateWorker_Position.target = set_position


    def update_position(self, new_Position):
        self.parameter_dict['position'] = new_Position

    # function to scan between positions 1 and 2
    def scan(self):
        pass
    
class UpdateWorker_Position(QtCore.QThread):
    new_Position = QtCore.pyqtSignal(float)

    def __init__(self):
        super().__init__()
        self.currentPosition = []
        self.stop = False
        self.waitTime = 0.1
        self.target = 0

    def run(self):
        while not self.stop:
            # calling the read temperature function
            self.readposition = self.read_position()

            # waiting to remeasure the temperature
            time.sleep(self.waitTime)
            self.new_Position.emit(self.readposition)
    
    def read_position(self):
        pos = self.target + np.random.rand(1)
        return pos