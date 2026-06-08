# -*- coding: utf-8 -*-

import numpy as np
from PyQt5 import QtCore
import time
from collections import defaultdict


class CryoPasqal(QtCore.QThread):

    name = 'cryostat'
    
    def __init__(self):
        super(CryoPasqal, self).__init__()


        # set parameter dict
        self.parameter_dict = defaultdict()
        
        # setting up variables, open array
        self.Set_T = []
        self.OnOff_Comp = []
        self.OnOff_Loop = []
        self.ChannelA_T = []
        self.ChannelB_T = []
        self.ChannelC_T = []
        self.ChannelD_T = []
        self.HeliumDischarge_T = []
        self.WaterIn_T = []
        self.WaterOut_T = []
        self.MainControllet_T = []
        self.stop = False
        self.parameter_display_dict = defaultdict(dict)
        self.parameter_display_dict['Set_T']['val'] = 5
        self.parameter_display_dict['Set_T']['unit'] = ' K'
        self.parameter_display_dict['Set_T']['max'] = 1000
        self.parameter_display_dict['Set_T']['read'] = False
        self.parameter_display_dict['OnOff_comp']['val'] = 0
        self.parameter_display_dict['OnOff_comp']['unit'] = ' '
        self.parameter_display_dict['OnOff_comp']['max'] = 1
        self.parameter_display_dict['OnOff_comp']['read'] = False
        self.parameter_display_dict['OnOff_Loop']['val'] = 0
        self.parameter_display_dict['OnOff_Loop']['unit'] = ' '
        self.parameter_display_dict['OnOff_Loop']['max'] = 1
        self.parameter_display_dict['OnOff_Loop']['read'] = False
        self.parameter_display_dict['ChannelA_T']['val'] = 300
        self.parameter_display_dict['ChannelA_T']['unit'] = ' K'
        self.parameter_display_dict['ChannelA_T']['max'] = 1000
        self.parameter_display_dict['ChannelA_T']['read'] = True
        self.parameter_display_dict['ChannelB_T']['val'] = 300
        self.parameter_display_dict['ChannelB_T']['unit'] = ' K'
        self.parameter_display_dict['ChannelB_T']['max'] = 1000
        self.parameter_display_dict['ChannelB_T']['read'] = True
        self.parameter_display_dict['ChannelC_T']['val'] = 300
        self.parameter_display_dict['ChannelC_T']['unit'] = ' K'
        self.parameter_display_dict['ChannelC_T']['max'] = 1000
        self.parameter_display_dict['ChannelC_T']['read'] = True
        self.parameter_display_dict['ChannelD_T']['val'] = 300
        self.parameter_display_dict['ChannelD_T']['unit'] = ' K'
        self.parameter_display_dict['ChannelD_T']['max'] = 1000
        self.parameter_display_dict['ChannelD_T']['read'] = True
        self.parameter_display_dict['HeliumDischarge_T']['val'] = 300
        self.parameter_display_dict['HeliumDischarge_T']['unit'] = ' K'
        self.parameter_display_dict['HeliumDischarge_T']['max'] = 1000
        self.parameter_display_dict['HeliumDischarge_T']['read'] = True
        self.parameter_display_dict['WaterIn_T']['val'] = 300
        self.parameter_display_dict['WaterIn_T']['unit'] = ' K'
        self.parameter_display_dict['WaterIn_T']['max'] = 1000
        self.parameter_display_dict['WaterIn_T']['read'] = True
        self.parameter_display_dict['WaterOut_T']['val'] = 300
        self.parameter_display_dict['WaterOut_T']['unit'] = ' K'
        self.parameter_display_dict['WaterOut_T']['max'] = 1000
        self.parameter_display_dict['WaterOut_T']['read'] = True
        self.parameter_display_dict['MainController_T']['val'] = 300
        self.parameter_display_dict['MainController_T']['unit'] = ' K'
        self.parameter_display_dict['MainController_T']['max'] = 1000
        self.parameter_display_dict['MainController_T']['read'] = True

        # set up parameter dict that only contains value. (faster to access)
        self.parameter_dict = {}
        for key in self.parameter_display_dict.keys():
            self.parameter_dict[key] = self.parameter_display_dict[key]['val']
        
        # defining waitTime
        self.waitTime = 0.1

        # start updating temp
        self.UpdateWorker = UpdateWorker()
        self.UpdateWorker.new_Temps.connect(self.update_temp)
        self.UpdateWorker.start()

    def set_parameter(self,parameter,value):
        if parameter == 'Set_T':
            self.update_Set_T(value)
            self.UpdateWorker.target = value
        elif parameter == 'OnOff_comp':
            if value == 0:
                print('Warming up')
                # Opti.write('control:compressor:state?')
                # if Opti.read() == 0
                #     Opti.write('control:compressor:state ON')
            elif value == 1:
                # Opti.write('control:compressor:state?')
                # if Opti.read() == 1
                #     Opti.write('control:compressor:state OFF')
                print('Cooling down')
        elif parameter == 'OnOff_Loop':
            if value == 0:
                # Opti.write('SOURce:HEATer:STATe (@1)?')
                # if Opti.read() == 0:
                    # Opti.write('source:heater:state (@1),OFF')
                    print('Loop stoped')
                # else:
                    # print('Loop already stoped')
            elif value == 1:
                # Opti.write('SOURce:HEATer:STATe (@1)?')
                # if Opti.read() == 0:
                    # Opti.write('source:heater:state (@1),OFF')
                    print('Starting loop to reach Set_T')
                #else:
                #    print('Loop already started')


    def update_Set_T(self, Set_temperature):
        #set temperature to some degree K
        # Opti.write(f'source:temperature:spoint (@1),{Set_temperature}')
        print(f'Temperature set to {Set_temperature}')
              
    def start_cool(self):
        #start chamber cooldown
        #requests.post('http://10.131.3.6:47101/v1/controller/methods/cooldown()')
        
        print("Cooldown has started")
        
    def start_warm(self):
        # warmup the chamber
        # requests.post('http://10.131.3.6:47101/v1/controller/methods/warmup()')
        print("Warming Up")
        
    def update_temp(self, new_Temps):
        self.parameter_dict['ChannelA_T'] = float(new_Temps[0])
        self.parameter_dict['ChannelB_T'] = float(new_Temps[1])
        self.parameter_dict['ChannelC_T'] = float(new_Temps[2])
        self.parameter_dict['ChannelD_T'] = float(new_Temps[3])
        self.parameter_dict['HeliumDischarge_T'] = float(new_Temps[4])
        self.parameter_dict['WaterIn_T'] = float(new_Temps[5])
        self.parameter_dict['WaterOut_T'] = float(new_Temps[6])
        self.parameter_dict['MainController_T'] = float(new_Temps[7])

class UpdateWorker(QtCore.QThread):

    new_Temps = QtCore.pyqtSignal(list)

    def __init__(self):
        super(UpdateWorker, self).__init__()
        self.stop = False
        self.waitTime = 0.1
        self.target = 300

    def run(self):
        while not self.stop:
            # calling the read temperature function
            self.readtemp = self.read_T()

            # waiting to remeasure the temperature
            time.sleep(self.waitTime)
            self.new_Temps.emit(self.readtemp)

    def read_T(self):
        #read the current temperatures
        temps = [self.target + np.random.rand(1), self.target + np.random.rand(1), 
                 self.target + np.random.rand(1), self.target + np.random.rand(1),
                 self.target + np.random.rand(1), self.target + np.random.rand(1),
                 self.target + np.random.rand(1), self.target + np.random.rand(1)]
        # Opti.write('measure:scalar:temperature? (@1,2,3,4,5,6,7,8)')
        # temps =(Opti.read())
        return temps