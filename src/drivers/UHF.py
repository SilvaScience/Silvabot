from PyQt5 import QtCore
from collections import defaultdict
import time
from zhinst.toolkit import Session
import numpy as np
import matplotlib.pyplot as plt


class UHF():

    name = 'UHF'

    def __init__(self):
        super(UHF, self).__init__()

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

        # Connect to the UHF device
        self.session = Session("localhost")
        self.device = self.session.connect_device("DEV2037")
        print('Connection established with the Lock-In')

        # Configure the signal input 1
        self.device.sigins[0].range(1.5)
        self.device.sigins[0].ac(False)
        self.device.sigins[0].imp50(True)

        # Configure the signal input 2
        self.device.sigins[1].range(1.5)
        self.device.sigins[1].ac(False)
        self.device.sigins[1].imp50(True)

        # Configure external reference
        self.device.demods[0].enable(1)
        self.device.demods[0].adcselect(1)
        self.device.extrefs[0].enable(True)                                                    

        # Get the internal clock frequency of the device
        self.clockbase = self.device.clockbase()

        self.ts0 = np.nan

        print('Configuration of the Lock-In completed')

    def set_parameter(self,parameter,value):
        if parameter == 'sampling_rate':
            self.update_sampling_rate(value)
            self.sampling_rate = value

    def update_sampling_rate(self, sampling_rate):
        print(f'Sampling rate set to {sampling_rate} samples/s')

    # Modified read_and_collect_data function
    def read_and_collect_data(self, daq_module):
        daq_data = daq_module.read(raw=False, clk_rate=self.clockbase)
        progress = daq_module.raw_module.progress()[0]

        for node in self.sample_nodes:
            if node in daq_data.keys():
                for sig_burst in daq_data[node]:
                    # Determine initial timestamp offset
                    if np.isnan(self.ts0):
                        self.ts0 = sig_burst.header['createdtimestamp'][0] / self.clockbase

                    t0_burst = sig_burst.header['createdtimestamp'][0] / self.clockbase
                    t = (sig_burst.time + t0_burst) - self.ts0

                    value = sig_burst.value[0, :]

                    # Append to results
                    self.results[node]["time"].append(t)
                    self.results[node]["value"].append(value)

    def DAQ_acquire(self):
        self.num_cols = int(np.ceil(self.sampling_rate * self.burst_duration))
        self.num_bursts = int(np.ceil(self.total_duration / self.burst_duration))

        daq_module = self.session.modules.daq
        daq_module.device(self.device)
        daq_module.type(0)
        daq_module.grid.mode(2)
        daq_module.count(self.num_bursts)
        daq_module.duration(self.burst_duration)
        daq_module.grid.cols(self.num_cols)

        daq_module.save.fileformat(1)
        daq_module.save.filename('zi_toolkit_acq_example')
        daq_module.save.saveonread(1)

        self.timeout = 1.5 * self.total_duration

        self.sample_nodes = [self.device.demods[0].sample.x, self.device.demods[0].sample.y]
        for node in self.sample_nodes:
            daq_module.subscribe(node) 

        self.results = {node: {"time": [], "value": []} for node in self.sample_nodes}

        self.start_time = time.time()
        daq_module.execute()

        while time.time() - self.start_time < self.timeout:
            self.read_and_collect_data(daq_module)
            if daq_module.raw_module.finished():
                self.read_and_collect_data(daq_module)
                break

            time.sleep(self.burst_duration)

        daq_module.save.save.wait_for_state_change(0, timeout=10)

        # Convert bursts into single arrays
        node_x = self.device.demods[0].sample.x
        node_y = self.device.demods[0].sample.y

        t_full = np.concatenate(self.results[node_x]["time"])
        x_full = np.concatenate(self.results[node_x]["value"])
        y_full = np.concatenate(self.results[node_y]["value"])
        print(len(t_full))
        print(len(x_full))
        print(len(y_full))
        return t_full, x_full, y_full

