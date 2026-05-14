# -*- coding: utf-8 -*-
"""
@author: Étienne Tremblay
Hardware class to control Pasqal cryostat. It currently monitors the different 
temperatures of the cryostat and allows to set the temperature setpoint, turn 
on/off the compressor and turn on/off the heaters.
"""

from PyQt5 import QtCore
import time
from collections import defaultdict
import pyvisa

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

        # connect to cryo
        rm = pyvisa.ResourceManager()
        self.Opti = rm.open_resource('ASRL9::INSTR',baud_rate=115200,
                                         data_bits=8,
                                         parity=pyvisa.constants.Parity.none,
                                         stop_bits=pyvisa.constants.StopBits.one,
                                         read_termination = '\n',
                                         write_termination = '\n',
                                         timeout=1000)
        time.sleep(3)
        self.Opti.write('*IDN?')
        time.sleep(3)
        print(f'Connected to {self.Opti.read()}')

        # start updating temp
        self.UpdateWorker = UpdateWorker(self.Opti)
        self.UpdateWorker.new_Temps.connect(self.update_temp)
        self.UpdateWorker.start()

    def set_parameter(self,parameter,value):
        if parameter == 'Set_T':
            self.update_Set_T(value)
            self.UpdateWorker.target = value

        elif parameter == 'OnOff_comp':
            self.update_compressor_state(value)
        
        elif parameter == 'OnOff_Loop':
            self.update_heater_state(value)


    def update_Set_T(self, Set_temperature):
        """
        Purpose : Update the temperature setpoint of the cryostat when the value is changed in the GUI
        Input : 
            Set_temperature (float) : the new temperature setpoint to be set in the cryostat
        """
        self.Opti.write(f'source:temperature:spoint (@1),{Set_temperature}')
        self.Opti.write('source:temperature:spoint? (@1)')
        print(f'Temperature set to {self.Opti.read()}')
        
    def update_temp(self, new_Temps):
        """
        Purpose : Update the temperature values in the parameter dictionary
        Input : 
            new_Temps (list) : a list of all the new temperature values
        """
        self.parameter_dict['ChannelA_T'] = float(new_Temps[0])
        self.parameter_dict['ChannelB_T'] = float(new_Temps[1])
        self.parameter_dict['ChannelC_T'] = float(new_Temps[2])
        self.parameter_dict['ChannelD_T'] = float(new_Temps[3])
        self.parameter_dict['HeliumDischarge_T'] = float(new_Temps[4])
        self.parameter_dict['WaterIn_T'] = float(new_Temps[5])
        self.parameter_dict['WaterOut_T'] = float(new_Temps[6])
        self.parameter_dict['MainController_T'] = float(new_Temps[7])
    
    def update_compressor_state(self, value):
        """
        Purpose : Change the state of the compressor when the value is changed in the GUI
        Input :
            value (int) : the new compressor state to be set in the cryostat (0 for OFF, 1 for ON)
        """
        init_state = int(self.Opti.query('control:compressor:state?'))
        if value == init_state:
            print('The desired operation is already started')
        else:
            if init_state == 0:
                self.Opti.write('control:compressor:state on')
                print(f'Cooling down')
            elif init_state == 1:
                self.Opti.write('control:compressor:state off')
                print(f'Warming up')
    
    def update_heater_state(self,value):
        """
        Purpose : Change the state of the heaters when the value is changed in the GUI
        Input :
            value (int) : the new state of the heaters to be set (0 for OFF, 1 for ON)
        """
        init_state = int(self.Opti.query('source:heater:state? (@1)'))
        if value == init_state:
            print('The desired operation is already started')
        else:
            if init_state == 0:
                self.Opti.write('source:heater:state (@1),on')
                final_state = self.Opti.query('source:heater:state? (@1)').strip() #.strip is used to make sure the state is correctly printed on the following line
                print(f'Turning on the heaters to reach Set_T (Heater state : {final_state})')
            elif init_state == 1:
                self.Opti.write('source:heater:state (@1),off')
                final_state = self.Opti.query('source:heater:state? (@1)').strip() #.strip is used to make sure the state is correctly printed on the following line
                print(f'Turning off the heaters (Heater state : {final_state})')

class UpdateWorker(QtCore.QThread):
    """
    Purpose : This worker is used to continuously update the temperature values in the parameter 
              dictionary. It reads the temperature values from the cryostat every 0.1 seconds 
              and emits a signal with the new temperature values to update the parameter dictionary 
              in the main thread.
    """
    new_Temps = QtCore.pyqtSignal(list)

    def __init__(self, Opti):
        super(UpdateWorker, self).__init__()
        self.stop = False
        self.waitTime = 0.1
        self.target = 300
        self.Opti = Opti

    def run(self):
        while not self.stop:
            # calling the read temperature function
            self.readtemp = self.read_T()

            # waiting to remeasure the temperature
            time.sleep(self.waitTime)
            self.readtemp = self.readtemp.split(',')
            for i in range(len(self.readtemp)):
                if self.readtemp[i] == 'nan':
                    self.readtemp[i] = 999
            self.new_Temps.emit(self.readtemp)

    def read_T(self):
        #read the current temperatures
        temps = self.Opti.query('measure:scalar:temperature? (@1,2,3,4,5,6,7,8)')
        return temps