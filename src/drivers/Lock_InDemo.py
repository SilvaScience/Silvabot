from PyQt5 import QtCore
from collections import defaultdict
import time
import numpy as np

class Lock_InDemo():

    name = 'Lock_InDemo'

    def __init__(self, lock_in_type):
        super(Lock_InDemo, self).__init__()

        # setting up the parameter dict
        self.parameter_dict = defaultdict()

        self.total_duration = 5
        self.sampling_rate = 10000
        self.burst_duration = 0.2        
        self.parameter_display_dict = defaultdict(dict)

        self.parameter_dict['filter_order'] = 0
        self.parameter_dict['time_constant'] = 0
        self.parameter_dict['Displayed_signal_input'] = 0
        self.parameter_display_dict = defaultdict(dict)

        self.parameter_display_dict['filter_order']['val'] = 4
        self.parameter_display_dict['filter_order']['unit'] = ' '
        self.parameter_display_dict['filter_order']['max'] = 8
        self.parameter_display_dict['filter_order']['min'] = 1
        self.parameter_display_dict['filter_order']['read'] = False
        
        self.parameter_display_dict['time_constant']['val'] = 0.025
        self.parameter_display_dict['time_constant']['unit'] = 's'
        self.parameter_display_dict['time_constant']['max'] = 100
        self.parameter_display_dict['time_constant']['read'] = False

        # set up parameter dict that only contains value
        self.parameter_dict = {}
        for key in self.parameter_display_dict.keys():
            self.parameter_dict[key] = self.parameter_display_dict[key]['val']

    def set_parameter(self,parameter,value):
        if parameter == 'sampling_rate':
            self.update_sampling_rate(value)
            self.sampling_rate = value

    def update_sampling_rate(self, sampling_rate):
        print(f'Sampling rate set to {sampling_rate} samples/s')

    def read_and_collect_data(self, daq_module):
        pass

    def DAQ_acquire(self):
        t_full = np.linspace(0,1000,10000)
        x_full = np.linspace(0,1000,10000)
        y_full = np.linspace(0,1000,10000)
        return t_full, x_full #, y_full