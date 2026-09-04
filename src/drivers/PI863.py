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
        self.parameter_display_dict = defaultdict(dict)
        self.stop = False

        self.parameter_display_dict['position']['val'] = 0
        self.parameter_display_dict['position']['unit'] = ' mm'
        self.parameter_display_dict['position']['max'] = 50
        self.parameter_display_dict['position']['read'] = True
        
        self.parameter_display_dict['speed']['val'] = 1
        self.parameter_display_dict['speed']['unit'] = ' mm/s'
        self.parameter_display_dict['speed']['max'] = 20
        self.parameter_display_dict['speed']['read'] = False

        # set up parameter dict that only contains value. (faster to access)
        self.parameter_dict = {}
        for key in self.parameter_display_dict.keys():
            self.parameter_dict[key] = self.parameter_display_dict[key]['val']

        # initialize translation stage
        self.pidevice = GCSDevice('C-863.11')
        self.pidevice.ConnectUSB(serialnum='0025550268')
        pitools.startup(self.pidevice, stages='62309120', refmodes='FNL')
        print('connected: {}'.format(self.pidevice.qIDN().strip()))
        self.pidevice.VEL(1, self.parameter_dict['speed'])  # set initial speed to the value in parameter dict

        # start updating position
        self.UpdateWorker_Position = UpdateWorker_Position(self.pidevice)
        self.UpdateWorker_Position.new_Position.connect(self.update_position)
        self.UpdateWorker_Position.start()

    def set_parameter(self,parameter,value):
        if parameter == 'speed':
            self.update_speed(value)
            self.parameter_dict['speed'] = value
        if parameter == 'target_position':
            self.update_target_position(value)
        if parameter == 'position':
            self.update_position(value)


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