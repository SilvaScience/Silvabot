from PyQt5 import QtCore
from collections import defaultdict
import time

class PI863Demo():

    name = 'PI863Demo'

    def __init__(self):
        super(PI863Demo, self).__init__()

        # setting up the parameter dict
        self.parameter_dict = defaultdict()

        self.set_speed = []
        self.current_speed = []
        self.set_position = []
        self.current_position = []
        self.set_position_1 = []
        self.set_position_2 = []
        self.stop = False
        self.parameter_display_dict = defaultdict(dict)

        self.parameter_dict['set_speed'] = 0
        self.parameter_dict['current_speed'] = 0
        self.parameter_dict['set_position'] = 0
        self.parameter_dict['current_position'] = 0
        self.parameter_dict['set_position_1'] = 0
        self.parameter_dict['set_position_2'] = 0
        
        self.parameter_display_dict['set_speed']['val'] = 0
        self.parameter_display_dict['set_speed']['unit'] = ' mm/s'
        self.parameter_display_dict['set_speed']['max'] = 20
        self.parameter_display_dict['set_speed']['read'] = False

        self.parameter_display_dict['current_speed']['val'] = 0
        self.parameter_display_dict['current_speed']['unit'] = ' mm/s'
        self.parameter_display_dict['current_speed']['max'] = 20
        self.parameter_display_dict['current_speed']['read'] = True

        self.parameter_display_dict['set_position']['val'] = 0
        self.parameter_display_dict['set_position']['unit'] = ' mm'
        self.parameter_display_dict['set_position']['max'] = 50
        self.parameter_display_dict['set_position']['read'] = False

        self.parameter_display_dict['current_position']['val'] = 0
        self.parameter_display_dict['current_position']['unit'] = ' mm'
        self.parameter_display_dict['current_position']['max'] = 50
        self.parameter_display_dict['current_position']['read'] = True

        self.parameter_display_dict['set_position_1']['val'] = 0
        self.parameter_display_dict['set_position_1']['unit'] = ' mm'
        self.parameter_display_dict['set_position_1']['max'] = 50
        self.parameter_display_dict['set_position_1']['read'] = False

        self.parameter_display_dict['set_position_2']['val'] = 0
        self.parameter_display_dict['set_position_2']['unit'] = ' mm'
        self.parameter_display_dict['set_position_2']['max'] = 50
        self.parameter_display_dict['set_position_2']['read'] = False

        # set up parameter dict that only contains value. (faster to access)
        self.parameter_dict = {}
        for key in self.parameter_display_dict.keys():
            self.parameter_dict[key] = self.parameter_display_dict[key]['val']

        # defining waitTime
        self.waitTime = 0.1

        # start updating position and speed
        self.UpdateWorker_Speed = UpdateWorker_Speed()
        self.UpdateWorker_Speed.new_Speed.connect(self.update_speed)
        self.UpdateWorker_Speed.start()

        self.UpdateWorker_Position = UpdateWorker_Position()
        self.UpdateWorker_Position.new_Position.connect(self.update_position)
        self.UpdateWorker_Position.start()

    def set_parameter(self,parameter,value):
        if parameter == 'set_speed':
            self.update_set_speed(value)
            self.UpdateWorker_Speed.target = value
        if parameter == 'set_position':
            self.update_set_position(value)
            self.UpdateWorker_Position.target = value
        if parameter == 'set_position_1':
            self.update_set_position_1(value)
            self.set_position_1 = value
        if parameter == 'set_position_2':
            self.update_set_position_2(value)
            self.set_position_2 = value

    def update_set_speed(self, set_speed):
        print(f'Speed set to {set_speed}')
    
    def update_set_position(self, set_position):
        print(f'Moving to {set_position}')
              
    def update_set_position_1(self, set_position_1):
        print(f'Position 1 set to {set_position_1}')

    def update_set_position_2(self, set_position_2):
        print(f'Position 2 set to {set_position_2}')

    def update_speed(self, new_Speed):
        self.parameter_dict['current_speed'] = new_Speed

    def update_position(self, new_Position):
        self.parameter_dict['current_position'] = new_Position

    # function to scan between positions 1 and 2
    def scan(self):
        pass

class UpdateWorker_Speed(QtCore.QThread):
    new_Speed = QtCore.pyqtSignal(float)

    def __init__(self):
        super().__init__()
        self.currentSpeed = []
        self.stop = False
        self.waitTime = 0.1
        self.target = 0

    def run(self):
        while not self.stop:
            # calling the read temperature function
            self.readspeed = self.read_speed()

            # waiting to remeasure the temperature
            time.sleep(self.waitTime)
            self.new_Speed.emit(self.readspeed)

    def read_speed(self):
        target = self.target
        return target
    
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
        target = self.target
        return target