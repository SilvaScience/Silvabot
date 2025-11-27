#This code is a Demo that controles attocube piezos. This routine 
#can move x,y,z axis to any position and then return them home.
#Home is setting in the same position when piezos are turned on

import numpy as np 
from pylablib.devices import Attocube
from PyQt5 import QtCore


class Piezos(QtCore.QThread):

    name = 'piezos'

    def __init__(self):
        super(Piezos, self).__init__()

        
        #This line ensures the main code works if the piezos are not connected
        try:
            self.anc = Attocube.ANC300("COM5") #Entablish communication with ANC300, verify which COM you are using
            self.anc.enable_axis("all") #Enable all axis
        except:
            print("COM5 is not connected")
            self.anc = None
        
        self.axis = np.array([1, 2, 3])  # {x,y,z} axis

        self.parameter_display_dict = {}

        #Piezos parameters

        self.parameter_display_dict['temperature'] = {}
        self.parameter_display_dict['temperature']['val'] = 300
        self.parameter_display_dict['temperature']['unit'] = 'K'
        self.parameter_display_dict['temperature']['max'] = 400
        self.parameter_display_dict['temperature']['min'] = 4
        self.parameter_display_dict['temperature']['read'] = False


        self.parameter_display_dict['voltage'] = {}
        self.parameter_display_dict['voltage']['val'] = 30
        self.parameter_display_dict['voltage']['unit'] = 'V'
        self.parameter_display_dict['voltage']['max'] = 30
        self.parameter_display_dict['voltage']['read'] = False

        self.parameter_display_dict['velocity_x'] = {}
        self.parameter_display_dict['velocity_x']['val'] = 0.2
        self.parameter_display_dict['velocity_x']['unit'] = 'mm/s'
        self.parameter_display_dict['velocity_x']['max'] = 2.9
        self.parameter_display_dict['velocity_x']['read'] = False

        self.parameter_display_dict['velocity_y'] = {}
        self.parameter_display_dict['velocity_y']['val'] = 0.2
        self.parameter_display_dict['velocity_y']['unit'] = 'mm/s'
        self.parameter_display_dict['velocity_y']['max'] = 2.9
        self.parameter_display_dict['velocity_y']['read'] = False

        self.parameter_display_dict['velocity_z'] = {}
        self.parameter_display_dict['velocity_z']['val'] = 0.2
        self.parameter_display_dict['velocity_z']['unit'] = 'mm/s'
        self.parameter_display_dict['velocity_z']['max'] = 2.9
        self.parameter_display_dict['velocity_z']['read'] = False

        self.parameter_display_dict['position_x'] = {}
        self.parameter_display_dict['position_x']['val'] = 0
        self.parameter_display_dict['position_x']['unit'] = 'mm'
        self.parameter_display_dict['position_x']['max'] = 15
        self.parameter_display_dict['position_x']['min'] = -15
        self.parameter_display_dict['position_x']['read'] = False

        self.parameter_display_dict['position_y'] = {}
        self.parameter_display_dict['position_y']['val'] = 0
        self.parameter_display_dict['position_y']['unit'] = 'mm'
        self.parameter_display_dict['position_y']['max'] = 15
        self.parameter_display_dict['position_y']['min'] = -15
        self.parameter_display_dict['position_y']['read'] = False

        self.parameter_display_dict['position_z'] = {}
        self.parameter_display_dict['position_z']['val'] = 0
        self.parameter_display_dict['position_z']['unit'] = 'mm'
        self.parameter_display_dict['position_z']['max'] = 15
        self.parameter_display_dict['position_z']['min'] = -15
        self.parameter_display_dict['position_z']['read'] = False

        
        #This function stores the parameters in a dictionary
        self.parameter_dict = {}
        for key in self.parameter_display_dict.keys():
            self.parameter_dict[key] = self.parameter_display_dict[key]['val']


        #Minimum step size
        self.d_min_step = self.set_temp(self.parameter_dict['temperature'])

        #Frequencies of each axis
        self.f_x = self.velocity_x_to_frequency_x(self.parameter_dict['velocity_x'])
        self.f_y = self.velocity_y_to_frequency_y(self.parameter_dict['velocity_y'])
        self.f_z = self.velocity_z_to_frequency_z(self.parameter_dict['velocity_z'])



    def set_parameter(self, param, value):

        if param in self.parameter_dict:
            self.parameter_dict[param] = value
            if param in self.parameter_display_dict:
                self.parameter_display_dict[param]['val'] = value
            print(f"Updated {param} to {value}")
        else:
            print(f"Parameter {param} not found in PiezosDemo")

    #This function sets the minimum step according to the temperature
    def set_temp(self, temperature):
        if temperature == 300:
            d_min=0.0012
        else:
            d_min=10**(-5)

        return(d_min)

    #This function calculates the frequency of the x-axis piezo movement with the velocity value
    def velocity_x_to_frequency_x(self, velocity_x):
        freq_x=round(velocity_x / self.d_min_step)
        return(freq_x) 

    #This function calculates the frequency of the y-axis piezo movement with the velocity value
    def velocity_y_to_frequency_y(self, velocity_y):
        freq_y=round(velocity_y / self.d_min_step)
        return(freq_y) 
    
    #This function calculates the frequency of the z-axis piezo movement with the velocity value
    def velocity_z_to_frequency_z(self, velocity_z):
        freq_z=round(velocity_z / self.d_min_step)
        return(freq_z) 

    #This function calculates the number of steps of the x-axis piezo movement with the distance value
    def distance_to_steps_x(self, position_x):
        steps_x=round(position_x / self.d_min_step)
        return(steps_x) 

    #This function calculates the number of steps of the y-axis piezo movement with the distance value
    def distance_to_steps_y(self, position_y):
        steps_y=round(position_y / self.d_min_step)
        return(steps_y)

    #This function calculates the number of steps of the z-axis piezo movement with the distance value
    def distance_to_steps_z(self, position_z):
        steps_z=round(position_z / self.d_min_step)
        return(steps_z) 

    #This function set the values of frequency and voltage
    def set_voltage_n_freqs(self):
        self.anc.set_frequency(1, self.f_x)
        self.anc.set_voltage(1, self.parameter_dict['voltage'])
        self.anc.set_frequency(2, self.f_y)
        self.anc.set_voltage(2, self.parameter_dict['voltage'])
        self.anc.set_frequency(3, self.f_z)
        self.anc.set_voltage(3, self.parameter_dict['voltage'])

    #This function saves the first position (when you turn on the system) as home.
    def set_home(self):
        self.positions = {1: 0.0, 2: 0.0, 3: 0.0} #coordinates
        self.d_net={1:0.0,2:0.0,3:0.0} #displacement

    #This function moves the axis
    def move_axis(self, axis):

        new_x_y=np.array([self.parameter_dict['position_x'],self.parameter_dict['position_y'],self.parameter_dict['position_z']])#actual coordinates
        dx1=self.parameter_dict['position_x']-self.positions[1]
        dy1=self.parameter_dict['position_y']-self.positions[2]
        dz1=self.parameter_dict['position_z']-self.positions[3]
        displacement = np.array([dx1,dy1,dz1])
      
        self.steps_all=np.array([self.distance_to_steps_x(dx1),self.distance_to_steps_y(dy1),self.distance_to_steps_y(dz1)])
        
            
        for i, ax in enumerate(axis):
            self.positions[ax] = new_x_y[i]
            self.d_net[ax] += displacement[i]
            self.anc.move_by(ax, self.steps_all[i])
            self.anc.wait_move(ax)

    #This function returns home
    def return_home(self):
        for ax in self.axis:
            steps_r = round(-abs(self.d_net[ax]) / self.d_min_step)
            self.anc.move_by(ax, steps_r)
            self.anc.wait_move(ax)
        self.set_home()

