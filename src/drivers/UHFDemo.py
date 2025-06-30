from PyQt5 import QtCore
from collections import defaultdict
import time

class UHFDemo():

    name = 'UHFDemo'

    def __init__(self):
        super(UHFDemo, self).__init__()

        # setting up the parameter dict
        self.parameter_dict = defaultdict()

###################### These parameters need to be changed
        self.total_duration = 5
        self.sampling_rate = 10000
        self.burst_duration = 0.2        
        self.parameter_display_dict = defaultdict(dict)

        self.parameter_dict['sampling_rate'] = 0

        self.parameter_display_dict['sampling_rate']['val'] = 10000
        self.parameter_display_dict['sampling_rate']['unit'] = ' samples/s'
        self.parameter_display_dict['sampling_rate']['max'] = 100000
        self.parameter_display_dict['sampling_rate']['read'] = False

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