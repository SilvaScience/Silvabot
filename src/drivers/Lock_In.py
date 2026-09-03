from PyQt5 import QtCore
from collections import defaultdict
import time
from zhinst.toolkit import Session
import numpy as np
import matplotlib.pyplot as plt


class Lock_In():

    name = 'Lock-In'
    sendProgress = QtCore.pyqtSignal(float)

    def __init__(self, lock_in_type):
        super(Lock_In, self).__init__()
        # Define the type of lock-in used
        self.lock_in_type = lock_in_type

        # setting up the parameter dict
        self.parameter_dict = defaultdict()
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
        self.parameter_display_dict['Displayed_signal_input']['val'] = 1
        self.parameter_display_dict['Displayed_signal_input']['unit'] = ' '
        self.parameter_display_dict['Displayed_signal_input']['min'] = 1
        self.parameter_display_dict['Displayed_signal_input']['max'] = 2
        self.parameter_display_dict['Displayed_signal_input']['read'] = False
        self.parameter_display_dict['Averageing']['val'] = 1
        self.parameter_display_dict['Averageing']['unit'] = ' '
        self.parameter_display_dict['Averageing']['min'] = 1
        self.parameter_display_dict['Averageing']['max'] = 100
        self.parameter_display_dict['Averageing']['read'] = False

        # set up parameter dict that only contains value
        self.parameter_dict = {}
        for key in self.parameter_display_dict.keys():
            self.parameter_dict[key] = self.parameter_display_dict[key]['val']

        # Connect to the appropriate lock-in device
        if lock_in_type == 'UHF':
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
            self.device.demods[0].enable(True)                                         # Enable the demodulator
            self.device.demods[0].order(self.parameter_dict['filter_order'])           # Set the filter order
            self.device.demods[0].timeconstant(self.parameter_dict['time_constant'])   # Set the time constant
            self.device.demods[0].oscselect(0)                                         # Set the oscillator to use
            self.device.demods[0].sinc(1)                                              # Enable sinc filter
            self.device.demods[0].rate(429.2)                                          # Set the sampling rate to 429.2 samples/s
            self.device.extrefs[0].enable(1)                                           # Enable external reference
            self.device.demods[3].adcselect(2)                                         # Select the input channel to use for the reference

            # Configure the second demodulation
            self.device.demods[4].adcselect(1)                                         # Select the input channel to use
            self.device.demods[4].enable(True)                                         # Enable the demodulator
            self.device.demods[4].order(self.parameter_dict['filter_order'])           # Set the filter order
            self.device.demods[4].timeconstant(self.parameter_dict['time_constant'])   # Set the time constant
            self.device.demods[4].oscselect(1)                                         # Set the oscillator to use
            self.device.demods[4].sinc(1)                                              # Enable sinc filter
            self.device.demods[4].rate(429.2)                                          # Set the sampling rate to 429.2 samples/s
            self.device.extrefs[1].enable(1)                                           # Enable external reference
            self.device.demods[7].adcselect(2)                                         # Select the input channel to use for the reference

            # Configure the scope parameters
            self.scope_module = self.session.modules.scope # Create scope module
            self.scope_module.mode(1)                      # Select the mode of operation (1 = time domain and triggered acquisition)
            self.wave_node = self.device.scopes[0].wave    # Define node to acquire data from
            self.scope_module.subscribe(self.wave_node)    # Subscribe to the scope wave node
            with self.device.set_transaction():
                self.device.scopes[0].channel(self.parameter_dict['Displayed_signal_input']) # Select the input channel to acquire
                self.device.scopes[0].trigenable(True)   # Enable the scope trigger
                self.device.scopes[0].trigchannel(3)     # Selection which input to use for the triger (0 : sig in 1, 1 : sig in 2, 2: ref trigger 1, 3: ref trigger 2)
                self.device.scopes[0].trigrising(1)      # Trigger on rising edge
                self.device.scopes[0].triglevel(0.0)     # Trigger level in V
                self.device.scopes[0].length(65536)      # Set the number of points in the scope (65536 is the maximum number of points)


            # Get the internal clock frequency of the device
            self.clockbase = self.device.clockbase()     # Definition of the internal clock frequency

            print('Configuration of the Lock-In completed')
        
        # Connect to appropriate lock-in device
        if lock_in_type == 'MFLI':
            self.session = Session("localhost")                     # Create a session with the Data Server
            self.device = self.session.connect_device("")           # Connect to the MFLI, ID is to be defined
            print('Connection established with the Lock-In')

            # Configure the signal input
            # Voltage input 1
            self.device.sigins[0].range(1.0)  # Set input range 1.0m (to be determined)
            self.device.sigins[0].scaling(1.0) # Set input scaling to 1.0 V
            self.device.sigins[0].ac(False)     # Set the device to AC or DC coupling, to be determined
            #self.device.sigins[0].imp50()  # Set the input impedance to 50 Ohm, to be determined

            # Current input 1
            self.device.sigins[1].range(10.0)  # Set input range to 10.0m (to be determined)
            self.device.sigins[1].scaling(1.0)     # Set the scaling of current input 1 to 1.0 A

            # Configure the first demodulation (verified the parameters)
            self.device.demods[0].adcselect(0)                                         # Select the input channel to use
            self.device.demods[0].enable(True)                                         # Enable the demodulator
            self.device.demods[0].order(self.parameter_dict['filter_order'])           # Set the filter order
            self.device.demods[0].timeconstant(self.parameter_dict['time_constant'])   # Set the time constant
            self.device.demods[0].oscselect(0)                                         # Set the oscillator to use
            self.device.demods[0].sinc()                                               # Enable sinc filter
            self.device.demods[0].rate()                                               # Set the sampling rate, to be determined
            self.device.extrefs[0].enable(1)                                            # Enable external reference
            self.device.demods[0].adcselect()                                          # Select the input channel (to verified) 

            # Configure the second demodulation (verified the parameters)
            self.device.demods[1].adcselect(1)                                         # Select the input channel to use
            self.device.demods[1].enable(True)                                         # Enable the demodulator
            self.device.demods[1].order(self.parameter_dict['filter_order'])           # Set the filter order
            self.device.demods[1].timeconstant(self.parameter_dict['time_constant'])   # Set the time constant
            self.device.demods[1].oscselect(0)                                         # Set the oscillator to use
            self.device.demods[1].sinc()                                               # Enable sinc filter
            self.device.demods[1].rate()                                               # Set the sampling rate, to be determined
            self.device.extrefs[1].enable(1)                                            # Enable external reference
            self.device.demods[1].adcselect()                                          # Select the input channel (to verified) 

            # Configure the scope parameters
            self.scope_module = self.session.modules.scope # Create scope module
            self.scope_module.mode(1)                      # Select the mode of operation (1 = time domain and triggered acquisition)
            self.wave_node = self.device.scopes[0].wave    # Define node to acquire data from
            self.scope_module.subscribe(self.wave_node)    # Subscribe to the scope wave node
            with self.device.set_transaction():
                self.device.scopes[0].channel(self.parameter_dict['Displayed_signal_input']) # Select the input channel to acquire
                self.device.scopes[0].trigenable(True)   # Enable the scope trigger
                self.device.scopes[0].trigchannel()      # Selection which input to use for the triger (0 : sig in 1, 1 : sig in 2, 2: ref trigger 1, 3: ref trigger 2) (to verified)
                self.device.scopes[0].trigrising(1)      # Trigger on rising edge
                self.device.scopes[0].triglevel()        # Trigger level in V (to be determined)
                self.device.scopes[0].length()           # Set the number of points in the scope (65536 is the maximum number of points) (to be determined)


            # Get the internal clock frequency of the device
            self.clockbase = self.device.clockbase()     # Definition of the internal clock frequency

            print('Configuration of the Lock-In completed')

    def set_parameter(self,parameter,value):
        if parameter == 'filter_order':
            self.update_filter_order(value)
            self.filter_order = value
        if parameter == 'time_constant':
            self.update_time_constant(value)
            self.time_constant = value
        if parameter == 'Displayed_signal_input':
            self.update_displayed_signal_input(value)
            self.parameter_dict['Displayed_signal_input'] = value
        if parameter == 'Averageing':
            self.parameter_dict['Averageing'] = value
    
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

    def Scope_acquire(self):
        self.device.scopes[0].channels[0].inputselect(self.parameter_dict['Displayed_signal_input'] - 1) 
        self.scope_module.execute()         # Start the scope acquisition
        self.device.scopes[0].enable(True)  # Enable the scope
        self.session.sync()                 # Sync the session

        # Wait until at least one record is available
        while self.scope_module.records() == 0:
            time.sleep(0.01) 

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

    def DAQ_setup(self, burst_duration):
        self.is_running = False
        self.burst_duration = burst_duration   # Duration of each data burst in seconds
        sample_nodes = [self.device.demods[0].sample.x,
                        self.device.demods[4].sample.x]

        daq_module = self.session.modules.daq    # Create DAQ module
        daq_module.device(self.device)           # Link the DAQ module to the UHF device
        daq_module.type(0)                       # Set DAQ type to continuous acquisition
        daq_module.grid.mode(2)                  # Set grid mode
        daq_module.count(1)                      # Set the number of measured bursts to 1   
        daq_module.duration(self.burst_duration) # Set burst duration
        daq_module.grid.cols(self.device.demods[0].rate() * self.burst_duration) # Set number of columns in the grid based on burst duration and sampling rate
        for node in sample_nodes:
            daq_module.subscribe(node)           # Subscribe to the sample nodes
        return self.clockbase, sample_nodes, daq_module