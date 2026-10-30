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


        self.parameter_display_dict['THz stage position']['val'] = 0
        self.parameter_display_dict['THz stage position']['unit'] = ' mm'
        self.parameter_display_dict['THz stage position']['max'] = 50
        self.parameter_display_dict['THz stage position']['read'] = True

        self.parameter_display_dict['THz stage speed']['val'] = 1
        self.parameter_display_dict['THz stage speed']['unit'] = ' mm/s'
        self.parameter_display_dict['THz stage speed']['max'] = 20
        self.parameter_display_dict['THz stage speed']['read'] = False

        self.parameter_display_dict['THz stage target position']['val'] = 0
        self.parameter_display_dict['THz stage target position']['unit'] = ' mm'
        self.parameter_display_dict['THz stage target position']['max'] = 50
        self.parameter_display_dict['THz stage target position']['min'] = 0
        self.parameter_display_dict['THz stage target position']['read'] = False

        self.parameter_display_dict['Pump-probe stage position']['val'] = 0
        self.parameter_display_dict['Pump-probe stage position']['unit'] = ' mm'
        self.parameter_display_dict['Pump-probe stage position']['max'] = 300
        self.parameter_display_dict['Pump-probe stage position']['read'] = True

        self.parameter_display_dict['Pump-probe stage speed']['val'] = 1
        self.parameter_display_dict['Pump-probe stage speed']['unit'] = ' mm/s'
        self.parameter_display_dict['Pump-probe stage speed']['max'] = 20
        self.parameter_display_dict['Pump-probe stage speed']['read'] = False

        self.parameter_display_dict['Pump-probe stage target position']['val'] = 0
        self.parameter_display_dict['Pump-probe stage target position']['unit'] = ' mm'
        self.parameter_display_dict['Pump-probe stage target position']['max'] = 300
        self.parameter_display_dict['Pump-probe stage target position']['min'] = 0
        self.parameter_display_dict['Pump-probe stage target position']['read'] = False


        # set up parameter dict that only contains value. (faster to access)
        self.parameter_dict = {}
        for key in self.parameter_display_dict.keys():
            self.parameter_dict[key] = self.parameter_display_dict[key]['val']

        # initialize translation stage
        self.THz_stage_Ctrl = GCSDevice('C-863.11')          # Instantiate the THz stage controller
        self.Pump_probe_stage_Ctrl = GCSDevice('C-863.11')   # Instantiate the Pump-probe stage controller

        self.THz_stage_Ctrl.OpenUSBDaisyChain(description='0025550268')  # Open USB daisy chain on the master controller
        daisychainid = self.THz_stage_Ctrl.dcid                          # Get the daisy chain ID from the master controller

        self.THz_stage_Ctrl.ConnectDaisyChainDevice(1, daisychainid)         # Connect the THz stage controller to the first device in the daisy chain
        self.Pump_probe_stage_Ctrl.ConnectDaisyChainDevice(2, daisychainid)  # Connect the Pump-probe stage controller to the second device in the daisy chain

        pitools.startup(self.THz_stage_Ctrl, stages='62309120', refmodes='FNL')        # Initialize the THz stage controller with the specified stage and reference mode
        print('Connected Controller 1: {}'.format(self.THz_stage_Ctrl.qIDN().strip())) # Print the identification of the THz stage controller
        pitools.startup(self.Pump_probe_stage_Ctrl, stages='62309180', refmodes='FNL')        # Initialize the Pump-probe stage controller with the specified stage and reference mode
        print('Connected Controller 2: {}'.format(self.Pump_probe_stage_Ctrl.qIDN().strip())) # Print the identification of the Pump-probe stage controller

        self.THz_stage_Ctrl.VEL(1, self.parameter_dict['THz stage speed'])                # set initial speed to the value in parameter dict
        self.Pump_probe_stage_Ctrl.VEL(1, self.parameter_dict['Pump-probe stage speed'])  # set initial speed to the value in parameter dict

        # Start updating position
        self.UpdateWorker_Position = UpdateWorker_Position(self.THz_stage_Ctrl, self.Pump_probe_stage_Ctrl)
        self.UpdateWorker_Position.new_THz_stage_Position.connect(self.update_THz_stage_position)
        self.UpdateWorker_Position.new_Pump_probe_stage_Position.connect(self.update_Pump_probe_stage_position)
        self.UpdateWorker_Position.start()

    def set_parameter(self,parameter,value):
        if parameter == 'THz stage speed':
            self.THz_stage_Ctrl.VEL(1, value)
            self.parameter_dict['THz stage speed'] = value
        if parameter == 'THz stage target position':
            self.THz_stage_Ctrl.MOV(1, value)
            self.parameter_dict['THz stage target position'] = value
        if parameter == 'THz stage position':
            self.update_THz_stage_position(value)
        if parameter == 'Pump-probe stage speed':
            self.Pump_probe_stage_Ctrl.VEL(1, value)
            self.parameter_dict['Pump-probe stage speed'] = value
        if parameter == 'Pump-probe stage target position':
            self.Pump_probe_stage_Ctrl.MOV(1, value)
            self.parameter_dict['Pump-probe stage target position'] = value
        if parameter == 'Pump-probe stage position':
            self.update_Pump_probe_stage_position(value)

    def update_THz_stage_position(self, position):
        self.parameter_dict['THz stage position'] = position

    def update_Pump_probe_stage_position(self, position):
        self.parameter_dict['Pump-probe stage position'] = position

    def close_device(self):
        self.THz_stage_Ctrl.CloseConnection()
        self.Pump_probe_stage_Ctrl.CloseConnection()
        print('Translation stages have been safely disconnected')


class UpdateWorker_Position(QtCore.QThread):
    new_THz_stage_Position = QtCore.pyqtSignal(float)
    new_Pump_probe_stage_Position = QtCore.pyqtSignal(float)

    def __init__(self, THz_device, Pump_probe_device):
        super().__init__()
        self.currentPosition = []
        self.stop = False
        self.waitTime = 0.05
        self.target = 0
        self.THz_stage_Ctrl = THz_device
        self.Pump_probe_stage_Ctrl = Pump_probe_device

    def run(self):
        while not self.stop:
            self.readposition = self.read_position()
            time.sleep(self.waitTime)
            if self.readposition is not None:
                self.new_THz_stage_Position.emit(self.readposition[0])
                self.new_Pump_probe_stage_Position.emit(self.readposition[1])
    
    def read_position(self):
        try:
            return self.THz_stage_Ctrl.qPOS(1)[1], self.Pump_probe_stage_Ctrl.qPOS(1)[1]  # Reads the position of both stages and returns them as a tuple
        except:
            return None