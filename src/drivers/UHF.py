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

        self.total_duration = 5
        self.sampling_rate = 10000
        self.burst_duration = 0.2        
        self.parameter_display_dict = defaultdict(dict)

        self.parameter_dict['total_duration'] = 0
        self.parameter_dict['sampling_rate'] = 0
        self.parameter_dict['burst_duration'] = 0

        self.parameter_display_dict['total_duration']['val'] = 5
        self.parameter_display_dict['total_duration']['unit'] = ' s'
        self.parameter_display_dict['total_duration']['max'] = 100
        self.parameter_display_dict['total_duration']['read'] = False

        self.parameter_display_dict['sampling_rate']['val'] = 10000
        self.parameter_display_dict['sampling_rate']['unit'] = ' samples/s'
        self.parameter_display_dict['sampling_rate']['max'] = 100000
        self.parameter_display_dict['sampling_rate']['read'] = False

        self.parameter_display_dict['burst_duration']['val'] = 0.2
        self.parameter_display_dict['burst_duration']['unit'] = ' s'
        self.parameter_display_dict['burst_duration']['max'] = 100
        self.parameter_display_dict['burst_duration']['read'] = False

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

        # Select the sample nodes and subscribe to them
        self.sample_nodes = [self.device.demods[0].sample.x, self.device.demods[0].sample.y]
        for node in self.sample_nodes:
            self.daq_module.subscribe(node) 

        # Get the internal clock frequency of the device
        self.clockbase = self.device.clockbase()

        self.ts0 = np.nan

        self.start_time = time.time()


        print('Configuration of the Lock-In completed')

    def set_parameter(self,parameter,value):
        if parameter == 'sampling_rate':
            self.update_sampling_rate(value)
            self.sampling_rate = value

    def update_sampling_rate(self, sampling_rate):
        print(f'Sampling rate set to {sampling_rate} samples/s')

class DaqMeasurement(QtCore.QThread):
    # set used signal types, destination is set in main script
    sendSpectrum = QtCore.pyqtSignal(np.ndarray, np.ndarray)
    sendProgress = QtCore.pyqtSignal(float)

    def __init__(self,devices, parameter):
        super(DaqMeasurement, self).__init__()
        self.num_cols = int(np.ceil(self.sampling_rate * self.burst_duration))
        self.num_bursts = int(np.ceil(self.total_duration / self.burst_duration))

        # Initialize DAQ module
        self.daq_module = self.session.modules.daq     
        self.daq_module.device(self.device)            
        self.daq_module.type(0)                   
        self.daq_module.grid.mode(2)             
        self.daq_module.count(self.num_bursts)         
        self.daq_module.duration(self.burst_duration)
        self.daq_module.grid.cols(self.num_cols)
        self.daq_module.save.fileformat(1)                                                    
        self.daq_module.save.filename('zi_toolkit_acq_example')                               
        self.daq_module.save.saveonread(1)

    def read_daq_data(self):
        daq_data = self.daq_module.read(raw=False, clk_rate=self.clockbase)    # Gets the data from the DAQ module
        for node in self.sample_nodes:
            if node in daq_data.keys():                              # Check if the node has data
                for sig_burst in daq_data[node]:                     
                    self.results[node].append(sig_burst)                  # Add bursts to results
                    if np.any(np.isnan(self.ts0)):             
                        self.ts0 = sig_burst.header['createdtimestamp'][0] / self.clockbase # This sets ts0 to the absolute time stamp of the first burst which allows for the measurement to start at 0
                    
                    # Convert from device ticks to time in seconds.
                    t0_burst = sig_burst.header['createdtimestamp'][0] / self.clockbase # Calculate the time in ticks when the measurement began and convert it to seconds
                    t = (sig_burst.time + t0_burst) - self.ts0                          # Calculate the total time of the measurement (t is in seconds)
                    
                    value = sig_burst.value[0, :]                                  # Extract the values in each burst (interested only in the first channel ([0]) since x and y only return one channel)
        return t, value

    def run(self):
        self.daq_module.execute()                             # Starting data acquisition             
        while time.time() - self.start_time < self.timeout:   # Start a while loop with a clear end condition (run for a most the timeout time)
            self.results, self.ts0 = self.read_data()                   # Execute the previously defined function
            if self.daq_module.raw_module.finished():         # Check if all the requested bursts have been recorded
                self.results, self.ts0 = self.read_data()               # Final time the function is ran to ensure all the data is recorded
                break
        self.daq_module.save.save.wait_for_state_change(0, timeout=10)
        plt.show()

    def stop(self):
        pass