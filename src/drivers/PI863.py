from PyQt5 import QtCore
from collections import defaultdict
import time
import numpy as np
from pipython import GCSDevice, pitools

class PI863():

    name = 'PI863'

    def __init__(self):
        super(PI863, self).__init__()

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
        
        self.parameter_display_dict['set_speed']['val'] = 10
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

        # initialize translation stage
        self.pidevice = GCSDevice('C-863.11')
        self.pidevice.ConnectUSB(serialnum='0025550268')
        print('connected: {}'.format(self.pidevice.qIDN().strip()))
        pitools.startup(self.pidevice, stages='62309120', refmodes='FNL')

        # start updating position
        self.UpdateWorker_Position = UpdateWorker_Position(self.pidevice)
        self.UpdateWorker_Position.new_Position.connect(self.update_position)
        self.UpdateWorker_Position.start()

    def set_parameter(self,parameter,value):
        if parameter == 'set_speed':
            self.update_set_speed(value)
        if parameter == 'set_target_position':
            self.update_set_target_position(value)
        if parameter == 'position':
            self.update_position(value)

    def update_set_speed(self, set_speed):
        self.pidevice.VEL(1, set_speed)
        get_speed = self.pidevice.qVEL()
        print(f'Speed set to {get_speed}')
    
    def update_set_target_position(self, set_position):
        print(f'Moving to {set_position}')
        self.pidevice.MOV(1, set_position)

    def update_position(self, new_Position):
        self.parameter_dict['position'] = new_Position
    
class UpdateWorker_Position(QtCore.QThread):
    new_Position = QtCore.pyqtSignal(float)

    def __init__(self, device):
        super().__init__()
        self.currentPosition = []
        self.stop = False
        self.waitTime = 0.05
        self.target = 0
        self.pidevice = device

    def run(self):
        while not self.stop:
            self.readposition = self.read_position()
            time.sleep(self.waitTime)
            if self.readposition is not None:
                self.new_Position.emit(self.readposition)
    
    def read_position(self):
        try:
            return self.pidevice.qPOS(1)[1]
        except:
            return None
        
class ScanWorker(QtCore.QThread):
    finished_scan = QtCore.pyqtSignal()

    def __init__(self, device):
        super().__init__()
        self.pidevice = device.pidevice  # Extract the actual GCS device from PI863 instance

    def run(self):
        self.pidevice.MOV(1, 50)   # Moves the stage to its maximum position
        pitools.waitontarget(self.pidevice, 1) # Waits until the stage reaches the target position
        self.pidevice.MOV(1, 0)    # Moves the stage to its initial position
        pitools.waitontarget(self.pidevice, 1) # Waits until the stage reaches the target position
        self.finished_scan.emit()