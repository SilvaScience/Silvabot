"""
This driver code that controls attocube piezos. This routine
can move x,y,z axis to any position and then return them home.
Home is setting in the same position when piezos are turned on


NOTES: COM Port Adress of piezos need to be changed if computer is changed.
"""




import numpy as np
from pylablib.devices import Attocube
from PyQt5 import QtCore




class Piezos(QtCore.QThread):


    name = 'piezos'


    def __init__(self, port):
        super(Piezos, self).__init__()


       
        #This line ensures the main code works if the piezos are not connected
        #port = 'COM5'
        try:
            self.anc = Attocube.ANC300(port) #Entablish communication with ANC300, verify which COM you are using
            self.anc.enable_axis("all") #Enable all axis
        except:
            print(f"{port} is not connected")
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


        self.parameter_display_dict['velocity'] = {}
        self.parameter_display_dict['velocity']['val'] = 0.05
        self.parameter_display_dict['velocity']['unit'] = 'mm/s'
        self.parameter_display_dict['velocity']['max'] = 0.05
        self.parameter_display_dict['velocity']['read'] = False




        self.parameter_display_dict['position_x'] = {}
        self.parameter_display_dict['position_x']['val'] = 0
        self.parameter_display_dict['position_x']['unit'] = 'mm'
        self.parameter_display_dict['position_x']['max'] = 5
        self.parameter_display_dict['position_x']['min'] = -5
        self.parameter_display_dict['position_x']['read'] = False


        self.parameter_display_dict['position_y'] = {}
        self.parameter_display_dict['position_y']['val'] = 0
        self.parameter_display_dict['position_y']['unit'] = 'mm'
        self.parameter_display_dict['position_y']['max'] = 5
        self.parameter_display_dict['position_y']['min'] = -5
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
        self.d_min_step = self.set_temp(self.parameter_dict['temperature'])# this needs to be reviewed according to spec




    def set_parameter(self, parameter, value):
        """REQUIRED. This function defines how changes in the parameter tree are handled.
        In devices with workers, a pause of continuous acquisition might be required. """


        if parameter == 'voltage':
            self.parameter_dict['voltage'] = value
            for i in range(3): self.anc.set_voltage(i + 1, value)


        if parameter == 'velocity':
            freq =round(self.parameter_dict['velocity'] / self.d_min_step)
            for i in range(3): self.anc.set_frequency(i+1, freq)


        if parameter == 'position_x':
            delta_x = value - self.parameter_dict['position_x']
            self.parameter_dict['position_x'] = value
            self.anc.move_by(1,round(delta_x/self.d_min_step,5))
            self.anc.wait_move(1)


        if parameter == 'position_y':
            delta_y = value - self.parameter_dict['position_y']
            self.parameter_dict['position_y'] = value
            self.anc.move_by(2,round(delta_y/self.d_min_step,5))
            self.anc.wait_move(2)
       
        if parameter == 'position_z':
            delta_z = value - self.parameter_dict['position_z']
            self.parameter_dict['position_z'] = value
            self.anc.move_by(3,round(delta_z/self.d_min_step,5))
            self.anc.wait_move(3)


       
        if self.param in self.parameter_dict:
            self.parameter_dict[self.param] = value
            if self.param in self.parameter_display_dict:
                self.parameter_display_dict[self.param]['val'] = value
            print(f"Updated {self.param} to {value}")
        else:
            print(f"Parameter {self.param} not found in Piezos")


    #This function sets the minimum step according to the temperature
    def set_temp(self, temperature):
        if temperature == 300:
            d_min=0.00005#0.0012 #mm #
        else:
            d_min=0.00001#10**(-5) #mm #


        return(d_min)


    #This function saves the first position (when you turn on the system) as home.
    #def set_home(self):
    #    self.positions = {1: 0.0, 2: 0.0, 3: 0.0} #coordinates
    #    self.d_net={1:0.0,2:0.0,3:0.0} #displacement


    #This function moves the axis
    #def move_axis(self, axis):


    #    new_x_y=np.array([self.parameter_dict['position_x'],self.parameter_dict['position_y'],self.parameter_dict['position_z']])#actual coordinates
    #    dx1=self.parameter_dict['position_x']-self.positions[1]
    #    dy1=self.parameter_dict['position_y']-self.positions[2]
    #    dz1=self.parameter_dict['position_z']-self.positions[3]
    #    displacement = np.array([dx1,dy1,dz1])
     
    #    self.steps_all=np.array([dx1,dy1,dz1])/self.d_min_step
       
           
    #    for i, ax in enumerate(axis):
    #        self.positions[ax] = new_x_y[i]
    #        self.d_net[ax] += displacement[i]
    #        self.anc.move_by(ax, self.steps_all[i])
    #        self.anc.wait_move(ax)


    #This function returns home
    #def return_home(self):
    #    for ax in self.axis:
    #        steps_r = round(-abs(self.d_net[ax]) / self.d_min_step)
    #        self.anc.move_by(ax, steps_r)
    #        self.anc.wait_move(ax)
    #    self.set_home()






