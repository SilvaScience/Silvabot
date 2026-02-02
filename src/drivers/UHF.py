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
        self.parameter_dict['sampling_rate'] = 0
        self.parameter_dict['filter_order'] = 0
        self.parameter_dict['time_constant'] = 0
        self.parameter_dict['Displayed_signal_input'] = 0
        self.parameter_dict['Demodulator_trigger_input'] = 0
        self.parameter_display_dict = defaultdict(dict)


        self.parameter_display_dict['sampling_rate']['val'] = 1000
        self.parameter_display_dict['sampling_rate']['unit'] = ' samples/s'
        self.parameter_display_dict['sampling_rate']['max'] = 100000
        self.parameter_display_dict['sampling_rate']['read'] = False
        self.parameter_display_dict['filter_order']['val'] = 4
        self.parameter_display_dict['filter_order']['unit'] = ' '
        self.parameter_display_dict['filter_order']['max'] = 8
        self.parameter_display_dict['filter_order']['min'] = 1
        self.parameter_display_dict['filter_order']['read'] = False
        self.parameter_display_dict['time_constant']['val'] = 0.025
        self.parameter_display_dict['time_constant']['unit'] = 's'
        self.parameter_display_dict['time_constant']['max'] = 100
        self.parameter_display_dict['time_constant']['read'] = False
        self.parameter_display_dict['Displayed_signal_input']['val'] = 1
        self.parameter_display_dict['Displayed_signal_input']['unit'] = ' '
        self.parameter_display_dict['Displayed_signal_input']['min'] = 1
        self.parameter_display_dict['Displayed_signal_input']['max'] = 2
        self.parameter_display_dict['Displayed_signal_input']['read'] = False
        self.parameter_display_dict['Demodulator_trigger_input']['val'] = 1
        self.parameter_display_dict['Demodulator_trigger_input']['unit'] = ' '
        self.parameter_display_dict['Demodulator_trigger_input']['min'] = 1
        self.parameter_display_dict['Demodulator_trigger_input']['max'] = 2
        self.parameter_display_dict['Demodulator_trigger_input']['read'] = False

        # set up parameter dict that only contains value
        self.parameter_dict = {}
        for key in self.parameter_display_dict.keys():
            self.parameter_dict[key] = self.parameter_display_dict[key]['val']

        # Connect to the UHF device
        self.session = Session("localhost")                     # Create a session with the Data Server
        self.device = self.session.connect_device("DEV2037")    # Connect to the UHF device (ID DEV2037)
        print('Connection established with the Lock-In')    

        # Configure the signal input 1
        self.device.sigins[0].range(1.5)  # Set input range to 1.5 V
        self.device.sigins[0].ac(False)   # Set the device to DC coupling
        self.device.sigins[0].imp50(True) # Set the input impedance to 50 Ohm

        # Configure the signal input 2
        self.device.sigins[1].range(1.5)  # Set input range to 1.5 V
        self.device.sigins[1].ac(False)   # Set the device to DC coupling
        self.device.sigins[1].imp50(True) # Set the input impedance to 50 Ohm

        # Configure the first demodulation
        self.device.demods[0].adcselect(0)                                         # Select the input channel to use
        self.device.demods[0].rate(self.parameter_dict['sampling_rate'])           # Set the sampling rate
        self.device.demods[0].enable(True)                                         # Enable the demodulator
        self.device.demods[0].order(self.parameter_dict['filter_order'])           # Set the filter order
        self.device.demods[0].timeconstant(self.parameter_dict['time_constant'])   # Set the time constant
        self.device.demods[0].oscselect(0)                                         # Set the oscillator to use
        self.device.demods[0].sinc(1)                                              # Enable sinc filter
        self.device.extrefs[0].enable(1)                                           # Enable external reference
        self.device.demods[3].adcselect(2)                                         # Select the input channel to use for the reference

        # Configure the second demodulation
        self.device.demods[4].adcselect(1)                                         # Select the input channel to use
        self.device.demods[4].rate(self.parameter_dict['sampling_rate'])           # Set the sampling rate
        self.device.demods[4].enable(True)                                         # Enable the demodulator
        self.device.demods[4].order(self.parameter_dict['filter_order'])           # Set the filter order
        self.device.demods[4].timeconstant(self.parameter_dict['time_constant'])   # Set the time constant
        self.device.demods[4].oscselect(1)                                         # Set the oscillator to use
        self.device.demods[4].sinc(1)                                              # Enable sinc filter
        self.device.extrefs[1].enable(1)                                           # Enable external reference
        self.device.demods[7].adcselect(2)                                         # Select the input channel to use for the reference

        # Configure the scope parameters
        self.scope_module = self.session.modules.scope # Create scope module
        self.scope_module.mode(1)                      # Select the mode of operation (1 = time domain and triggered acquisition)
        self.wave_node = self.device.scopes[0].wave    # Define node to acquire data from
        self.scope_module.subscribe(self.wave_node)    # Subscribe to the scope wave node
        with self.device.set_transaction():
            self.device.scopes[0].channel(self.parameter_dict['Displayed_signal_input']) # Select the input channel to acquire
#            print(self.parameter_dict['Displayed_signal_input']-1)
            self.device.scopes[0].trigenable(True)   # Enable the scope trigger
            self.device.scopes[0].trigchannel(3)     # Selection which input to use for the triger (0 : sig in 1, 1 : sig in 2, 2: ref trigger 1, 3: ref trigger 2)
            self.device.scopes[0].trigrising(1)      # Trigger on rising edge
            self.device.scopes[0].triglevel(0.0)     # Trigger level in V
            self.device.scopes[0].length(65536)      # Set the number of points in the scope (65536 is the maximum number of points)


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
        if parameter == 'Displayed_signal_input':
            self.update_displayed_signal_input(value)
            self.parameter_dict['Displayed_signal_input'] = value
        if parameter == 'Demodulator_trigger_input':
            self.update_Demodulator_trigger_input(value)
            self.parameter_dict['Demodulator_trigger_input'] = value

    def update_sampling_rate(self, sampling_rate):
        self.device.demods[0].rate(sampling_rate)
        print(f'Sampling rate set to {sampling_rate} samples/s')
    
    def update_filter_order(self, filter_order):
        self.device.demods[0].order(filter_order)
        self.device.demods[4].order(filter_order)
        print(f'Filter order is set to {filter_order}')

    def update_time_constant(self, time_constant):
        self.device.demods[0].timeconstant(time_constant)
        self.device.demods[4].timeconstant(time_constant)
        print(f'Time constant set to {time_constant} s')

    def update_displayed_signal_input(self, displayed_signal_input):
        self.device.scopes[0].channel(displayed_signal_input - 1)  
        print(f'Displayed signal input set to channel {displayed_signal_input}')

    def update_Demodulator_trigger_input(self, demodulator_trigger_input):
        self.device.demods[3].adcselect(demodulator_trigger_input + 1)
        self.device.demods[7].adcselect(demodulator_trigger_input + 1)  
        print(f'Demodulator trigger input set to channel {demodulator_trigger_input}')

    def Scope_acquire(self):
        self.device.scopes[0].channels[0].inputselect(self.parameter_dict['Displayed_signal_input'] - 1) 
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
        t_us = 1e6 * np.arange(-self.totalsamples, 0) * self.dt + (self.timestamp - self.triggertimestamp) / float(self.clockbase) # Create the time array
        return t_us, self.wave


class PlotterWorker(QtCore.QThread):
    scan_data = QtCore.pyqtSignal(np.ndarray, np.ndarray)

    def __init__(self, device):
        super().__init__()
        self.is_running = False
        self.device = device.device        # Access the device from the UHF class
        self.session = device.session      # Access the session from the UHF class
        self.clockbase = device.clockbase  # Access the clockbase from the UHF class

    def run(self):
        self.is_running = True
        
        # Function to read data from the DAQ module and to store it in results dictionary
        def read_data(daq_module, results, ts0):
            daq_data = daq_module.read(raw=False, clk_rate=self.clockbase)
            for node in sample_nodes:
                if node in daq_data.keys():
                    for sig_burst in daq_data[node]:
                        results[node].append(sig_burst)
                        if np.any(np.isnan(ts0)):
                            ts0 = sig_burst.header['createdtimestamp'][0] / self.clockbase
            return results, ts0

        # Initialize DAQ module for burst acquisition
        sample_nodes = [self.device.demods[0].sample.r,   # Select Demod 0's R output
                        self.device.demods[4].sample.r]   # Select Demod 4's R output
        burst_duration = 0.2                              # Duration of each data burst in seconds
        num_cols = int(np.ceil(burst_duration * self.device.demods[0].rate()))  # Number of samples per burst
        daq_module = self.session.modules.daq   # Create DAQ module
        daq_module.device(self.device)          # Link the DAQ module to the UHF device
        daq_module.type(0)                      # Set DAQ type to 'burst'
        daq_module.grid.mode(2)                 # Set grid mode
        daq_module.endless(1)                   # Enable endless acquisition
        daq_module.duration(burst_duration)     # Set burst duration
        daq_module.grid.cols(num_cols)          # Set number of columns in the grid based on burst duration and sampling rate
        for node in sample_nodes:
            daq_module.subscribe(node)          # Subscribe to the sample nodes

        # Acquire data in bursts until stopped
        ts0 = np.nan                             # Initialize initial timestamp
        results = {x: [] for x in sample_nodes}  # Initialize results dictionary
        daq_module.execute()                     # Start the DAQ module
        while self.is_running:                   # Loop until stopped (stopped when scan is finished)
            results, ts0 = read_data(daq_module, results, ts0)  # Read data and update results
            time.sleep(burst_duration)                          # Wait for the duration of the burst before next read
        daq_module.finish()                                     # Stop the DAQ module
        results, ts0 = read_data(daq_module, results, ts0)      # Final read to get any remaining data

        # Organize the acquired data
        d0_bursts = results[sample_nodes[0]]                                                                            # Get bursts for Demod 0
        r0 = np.concatenate([b.value.flatten() for b in d0_bursts])                                                     # Concatenate R values for Demod 0
        t0 = np.concatenate([(b.time + (b.header['createdtimestamp'][0] / self.clockbase) - ts0) for b in d0_bursts])   # Concatenate time values for Demod 0
        d4_bursts = results[sample_nodes[1]]                                                                            # Get bursts for Demod 4
        r4 = np.concatenate([b.value.flatten() for b in d4_bursts])                                                     # Concatenate R values for Demod 4
        t4 = np.concatenate([(b.time + (b.header['createdtimestamp'][0] / self.clockbase) - ts0) for b in d4_bursts])   # Concatenate time values for Demod 4

        # Calculate the difference in R values and plot it
        R_diff = r0 - r4
        self.scan_data.emit(t0, R_diff)
        
    def stop(self):
        self.is_running = False