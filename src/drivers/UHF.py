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
        self.sampling_rate = 1000
        self.burst_duration = 0.2        
        self.parameter_display_dict = defaultdict(dict)

        self.parameter_dict['sampling_rate'] = 0
        self.parameter_dict['filter_order'] = 0
        self.parameter_dict['time_constant'] = 0


        self.parameter_display_dict['sampling_rate']['val'] = 1000
        self.parameter_display_dict['sampling_rate']['unit'] = ' samples/s'
        self.parameter_display_dict['sampling_rate']['max'] = 100000
        self.parameter_display_dict['sampling_rate']['read'] = False
        self.parameter_display_dict['filter_order']['val'] = 1
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

        # Connect to the UHF device
        self.session = Session("localhost")                     # Create a session with the Data Server
        self.device = self.session.connect_device("DEV2037")    # Connect to the UHF device (ID DEV2037)
        print('Connection established with the Lock-In')    

        # Configure the signal input
        self.device.sigins[0].range(1.5)  # Set input range to 1.5 V
        self.device.sigins[0].ac(False)   # Set the device to DC coupling
        self.device.sigins[0].imp50(True) # Set the input impedance to 50 Ohm

        # Configure the demodulation
        self.device.demods[0].rate(self.parameter_dict['sampling_rate'])           # Set the sampling rate
        self.device.demods[0].enable(True)                                         # Enable the demodulator
        self.device.demods[0].order(self.parameter_dict['filter_order'])           # Set the filter order
        self.device.demods[0].timeconstant(self.parameter_dict['time_constant'])   # Set the time constant
        self.device.demods[0].oscselect(0)                                         # Set the oscillator to use
        self.device.demods[0].sinc(1)                                              # Enable sinc filter
        self.device.extrefs[0].enable(1)                                           # Enable external reference
        self.device.demods[3].adcselect(2)                                         # Select the input channel to use for the reference


        # Configure the scope parameters
        self.scope_module = self.session.modules.scope # Create scope module
        self.scope_module.mode(1)                      # Select the mode of operation (1 = time domain and triggered acquisition)
        self.wave_node = self.device.scopes[0].wave    # Define node to acquire data from
        self.scope_module.subscribe(self.wave_node)    # Subscribe to the scope wave node
        with self.device.set_transaction():
            self.device.scopes[0].trigenable(True)   # Enable the scope trigger
            self.device.scopes[0].trigchannel(3)     # Selection which input to use for the triger (0 : sig in 1, 1 : sig in 2, 1: ref trigger 1, 2: ref trigger 2)
            self.device.scopes[0].trigrising(1)      # Trigger on rising edge
            self.device.scopes[0].triglevel(0.0)     # Trigger level in V

        # Get the internal clock frequency of the device
        self.clockbase = self.device.clockbase()     # Definition of the internal clock frequency

        print('Configuration of the Lock-In completed')

    def set_parameter(self,parameter,value):
        if parameter == 'sampling_rate':
            self.update_sampling_rate(value)
            self.sampling_rate = value
        if parameter == 'filter_order':
            self.update_filter_order(value)
            self.filter_order = value
        if parameter == 'time_constant':
            self.update_time_constant(value)
            self.time_constant = value

    def update_sampling_rate(self, sampling_rate):
        self.device.demods[0].rate(sampling_rate)
        print(f'Sampling rate set to {sampling_rate} samples/s')
    
    def update_filter_order(self, filter_order):
        self.device.demods[0].order(filter_order)
        print(f'Filter order is set to {filter_order}')

    def update_time_constant(self, time_constant):
        self.device.demods[0].timeconstant(time_constant)
        print(f'Time constant set to {time_constant} s')

    def Scope_acquire(self):
        while True:
            self.scope_module.execute()         # Start the scope acquisition
            self.device.scopes[0].enable(True)  # Enable the scope
            self.session.sync()                 # Sync the session

            # Wait until at least one record is available
            while self.scope_module.records() == 0:
                time.sleep(0.05) 

            data = self.scope_module.read()       # Read the scope data
            self.device.scopes[0].enable(False)   # Disable the scope
            self.scope_module.finish()            # Finish the scope acquisition
            self.records = data[self.wave_node]   # Get the records from the wave node
            self.record = self.records[-1][0]                    # Get the most recent record
            self.wave = self.record["wave"][0, :]                # Extract the waveform data
            self.totalsamples = self.record["totalsamples"]      # Extract the total number of samples
            self.dt = self.record["dt"]                          # Extract the time step
            self.timestamp = self.record["timestamp"]            # Extract the timestamp
            self.triggertimestamp = self.record["triggertimestamp"]  # Extract the trigger timestamp
            t_us = 1e6 * np.arange(-self.totalsamples, 0) * self.dt + (self.timestamp - self.triggertimestamp) / float(self.clockbase) # Create time array            
            return t_us, self.wave

    def FFT_acquire(self, terminate):
        print(0)

class PlotterWorker(QtCore.QThread):
    scan_data = QtCore.pyqtSignal(np.ndarray, np.ndarray)

    def __init__(self, device):
        super().__init__()
        self.is_running = False
        self.device = device.device  # Extract the actual device from the UHF instance
        self.session = device.session
        self.clockbase = device.clockbase

    def run(self):
        self.is_running = True
        sample_node = self.device.demods[0].sample
        sample_node.subscribe()
         
        # Storage for 'continuous' data
        time_array = []
        R_array = []
        
        start_time = time.time()
        last_time = start_time
        
        # Start polling loop
        while self.is_running:
            data = self.session.poll(0.1)   # Poll for new data from the Data Server
            if sample_node in data:
                samples = data[sample_node]                    # Get samples from the node
                R = np.sqrt(samples["x"]**2 + samples["y"]**2) # Compute amplitude R from x and y
                ts = (samples["timestamp"] - samples["timestamp"][0]) / self.clockbase # Convert timestamps to seconds
                
                # Append the data to the storage arrays
                R_array.extend(R)
                time_array.extend(ts + (last_time - start_time))
                last_time = time.time()

            time.sleep(0.1) # buffer
        
        sample_node.unsubscribe() # Unsubscribe from the node when done
        self.scan_data.emit(np.array(time_array), np.array(R_array)) # Emit the collected scan data

    def stop(self):
        self.is_running = False
