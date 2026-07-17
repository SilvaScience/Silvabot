"""
Hardware class to control attocube piezos. All hardware classes require a definition of
parameter_dict (set write and read parameter)
parameter_display_dict (set Spinbox options)
set_parameter function (assign set functions)

This routine can move x,y,z axis to any position.

NOTES: 
- COM Port Adress of piezos need to be changed if computer is changed.
- The step size is currently defined in an arbitrary way, only following roughly the device specs. 
step size needs to be reviewed once precise mapping measurements will be performed. 
The step size depends on temperature, but it is not specified how (check attocube manual). 
We can probably implement a linear dependency. 

"""

import numpy as np
from pylablib.devices import Attocube
from PyQt5 import QtCore
import time

class Piezos(QtCore.QThread):

    name = 'piezos'

    def __init__(self, port):
        super(Piezos, self).__init__()
 
        #This line ensures the main code works if the piezos are not connected
        try:
            self.anc = Attocube.ANC300(port) #Entablish communication with ANC300, verify which COM you are using
            self.anc.enable_axis("all") #Enable all axis
        except:
            print(f"No piezos found at port {port}.Use Demo.")
            self.anc = None
       
        self.axis = np.array([1, 2, 3])  # {x,y,z} axis
        self.parameter_display_dict = {}
        #Piezos parameters
        self.parameter_display_dict['temperature'] = {}
        self.parameter_display_dict['temperature']['val'] = 300
        self.parameter_display_dict['temperature']['unit'] = ' K'
        self.parameter_display_dict['temperature']['max'] = 400
        self.parameter_display_dict['temperature']['min'] = 4
        self.parameter_display_dict['temperature']['read'] = False

        self.parameter_display_dict['voltage'] = {}
        self.parameter_display_dict['voltage']['val'] = 30
        self.parameter_display_dict['voltage']['unit'] = ' V'
        self.parameter_display_dict['voltage']['max'] = 40 # in exceptional cases (piezo stuck), this can be briefly raised to up to 70V. Carefully doublecheck with manual
        self.parameter_display_dict['voltage']['read'] = False

        self.parameter_display_dict['velocity'] = {}
        self.parameter_display_dict['velocity']['val'] = 10
        self.parameter_display_dict['velocity']['unit'] = ' um/s'
        self.parameter_display_dict['velocity']['max'] = 50 #allowing for max 1000 Hz at high T. in exceptional cases (piezo stuck), this can be briefly raised to up to 8kHz. Carefully doublecheck with manual
        self.parameter_display_dict['velocity']['read'] = False

        self.parameter_display_dict['position_x'] = {}
        self.parameter_display_dict['position_x']['val'] = 0
        self.parameter_display_dict['position_x']['unit'] = ' um'
        self.parameter_display_dict['position_x']['max'] = 5000
        self.parameter_display_dict['position_x']['min'] = -5000
        self.parameter_display_dict['position_x']['read'] = False

        self.parameter_display_dict['position_y'] = {}
        self.parameter_display_dict['position_y']['val'] = 0
        self.parameter_display_dict['position_y']['unit'] = ' um'
        self.parameter_display_dict['position_y']['max'] = 5000
        self.parameter_display_dict['position_y']['min'] = -5000
        self.parameter_display_dict['position_y']['read'] = False

        self.parameter_display_dict['position_z'] = {}
        self.parameter_display_dict['position_z']['val'] = 0
        self.parameter_display_dict['position_z']['unit'] = ' um'
        self.parameter_display_dict['position_z']['max'] = 5000
        self.parameter_display_dict['position_z']['min'] = -5000
        self.parameter_display_dict['position_z']['read'] = False

        #This function stores the parameters in a dictionary
        self.parameter_dict = {}
        for key in self.parameter_display_dict.keys():
            self.parameter_dict[key] = self.parameter_display_dict[key]['val']

        # additional functions
        self.device_setting_function = dict()
        self.device_setting_function['reset_piezos'] = ('Action', self.reset_positions)

        #Minimum step size
        self.d_min_step = self.set_temp(self.parameter_dict['temperature'])# TO BE REVIEWED/calibrated properly

    def set_parameter(self, parameter, value):
        """REQUIRED. This function defines how changes in the parameter tree are handled.
        In devices with workers, a pause of continuous acquisition might be required. """
        if parameter == 'voltage':
            self.parameter_dict['voltage'] = value
            for i in range(3): self.anc.set_voltage(i + 1, value)
        if parameter == 'velocity':
            self.parameter_dict['velocity'] = value
            freq =round(self.parameter_dict['velocity'] / self.d_min_step)
            for i in range(3): self.anc.set_frequency(i+1, freq)
        if parameter == 'position_x':
            delta_x = value - self.parameter_dict['position_x']
            self.parameter_dict['position_x'] = value
            self.anc.wait_move(1) # check if stage is still moving from previous command
            self.anc.move_by(1,round(delta_x/self.d_min_step,5))
        if parameter == 'position_y':
            delta_y = value - self.parameter_dict['position_y']
            self.parameter_dict['position_y'] = value
            self.anc.wait_move(2) # check if stage is still moving from previous command
            self.anc.move_by(2,round(delta_y/self.d_min_step,5))
        if parameter == 'position_z':
            delta_z = value - self.parameter_dict['position_z']
            self.parameter_dict['position_z'] = value
            self.anc.wait_move(3) # check if stage is still moving from previous command
            self.anc.move_by(3,round(delta_z/self.d_min_step,5))

    def reset_positions(self):
        # resets all write parameter to 0.
        self.parameter_dict['position_x'] = 0
        self.parameter_dict['position_y'] = 0
        self.parameter_dict['position_z'] = 0

    #This function sets the minimum step according to the temperature
    # THIS NEEDS TO BE REVIEWED 
    def set_temp(self, temperature):
        if temperature == 300:
            d_min=0.05#0.0012 #um #
        else:
            d_min=0.01#10**(-5) #um #
        return(d_min)






