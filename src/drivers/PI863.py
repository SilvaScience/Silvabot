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

        self.speed = []
        self.target_position = []
        self.position = []
        self.stop = False
        self.parameter_display_dict = defaultdict(dict)

        # self.parameter_dict['speed'] = 0
        # self.parameter_dict['target_position'] = 0
        # self.parameter_dict['position'] = 0

        self.parameter_display_dict['position']['val'] = 0
        self.parameter_display_dict['position']['unit'] = ' mm'
        self.parameter_display_dict['position']['max'] = 50
        self.parameter_display_dict['position']['read'] = True
        
        self.parameter_display_dict['speed']['val'] = 1
        self.parameter_display_dict['speed']['unit'] = ' mm/s'
        self.parameter_display_dict['speed']['max'] = 20
        self.parameter_display_dict['speed']['read'] = False

        self.parameter_display_dict['target_position']['val'] = 0
        self.parameter_display_dict['target_position']['unit'] = ' mm'
        self.parameter_display_dict['target_position']['max'] = 50
        self.parameter_display_dict['target_position']['read'] = False
        
        self.parameter_display_dict['scan_initial_position']['val'] = 0
        self.parameter_display_dict['scan_initial_position']['unit'] = ' mm'
        self.parameter_display_dict['scan_initial_position']['max'] = 50
        self.parameter_display_dict['scan_initial_position']['read'] = False

        self.parameter_display_dict['scan_final_position']['val'] = 50
        self.parameter_display_dict['scan_final_position']['unit'] = ' mm'
        self.parameter_display_dict['scan_final_position']['max'] = 50
        self.parameter_display_dict['scan_final_position']['read'] = False

        self.parameter_display_dict['autocorrelation_interval']['val'] = 1
        self.parameter_display_dict['autocorrelation_interval']['unit'] = ' µm'
        self.parameter_display_dict['autocorrelation_interval']['max'] = 50000
        self.parameter_display_dict['autocorrelation_interval']['read'] = False

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
        if parameter == 'scan_initial_position':
            self.update_scan_initial_position(value)
        if parameter == 'scan_final_position':
            self.update_scan_final_position(value)
        if parameter == 'autocorrelation_interval':
            self.update_autocorrelation_interval(value)

    def update_speed(self, new_speed):
        self.pidevice.VEL(1, new_speed)
        get_speed = self.pidevice.qVEL()
        print(f'Speed set to {get_speed["1"]} mm/s')
    
    def update_target_position(self, new_set_position):
        print(f'Moving to {new_set_position}')
        self.pidevice.MOV(1, new_set_position)

    def update_position(self, new_Position):
        self.parameter_dict['position'] = new_Position
    
    def update_scan_initial_position(self, new_initial_pos):
        self.parameter_dict['scan_initial_position'] = new_initial_pos
    
    def update_scan_final_position(self, new_final_pos):
        self.parameter_dict['scan_final_position'] = new_final_pos

    def update_autocorrelation_interval(self, new_interval):
        self.parameter_dict['autocorrelation_interval'] = new_interval * 1e-3
    
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
    starting_scan = QtCore.pyqtSignal()
    sendProgress = QtCore.pyqtSignal(float)

    def __init__(self, device, initial_pos, final_pos):
        super().__init__()
        self.pidevice = device.pidevice  # Extract the actual GCS device from PI863 instance
        self.initial_pos = initial_pos   # Store the initial position for the scan
        self.final_pos = final_pos       # Store the final position for the scan

    def run(self):
        # Move to initial position before starting the scan at a fast speed
        scan_speed = self.pidevice.qVEL()                     # Get the current speed from the parameter dict
        self.pidevice.VEL(1, 10)                              # Set speed to a fast value (10 mm/s) for moving to the initial position        
        self.pidevice.MOV(1, self.initial_pos)                # Moves the stage to the initial position
        pitools.waitontarget(self.pidevice, 1, timeout=10000) # Waits until the stage reaches the target position
        self.pidevice.VEL(1, scan_speed['1'])                 # Set the speed for scanning to the value from the parameter dict
        
        # Scan from initial position to final position
        self.starting_scan.emit()            # Emit signal to indicate that the scan is starting
        self.pidevice.MOV(1, self.final_pos) # Moves the stage to its maximum position