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
        self.session = Session("localhost")
        self.device = self.session.connect_device("DEV2037")
        print('Connection established with the Lock-In')

        # Configure the signal input
        self.device.sigins[0].range(1.5)
        self.device.sigins[0].ac(False)
        self.device.sigins[0].imp50(True)

        # Configure the demodulation
        self.device.demods[0].rate(self.parameter_dict['sampling_rate'])
        self.device.demods[0].enable(True)
        self.device.demods[0].order(self.parameter_dict['filter_order'])
        self.device.demods[0].timeconstant(self.parameter_dict['time_constant'])
        self.device.demods[3].adcselect(3)

        # Configure the scope parameters
        self.scope_module = self.session.modules.scope
        self.scope_module.mode(1)                    # Time-domain, triggered
        self.scope_module.historylength(5)

        self.wave_node = self.device.scopes[0].wave
        self.scope_module.subscribe(self.wave_node)
        with self.device.set_transaction():
            self.device.scopes[0].trigenable(True)
            self.device.scopes[0].trigchannel(3)     # Selection which input to use for the triger (0 : sig in 1, 1 : sig in 2, 1: ref trigger 1, 2: ref trigger 2)
            self.device.scopes[0].trigrising(1)
            self.device.scopes[0].trigfalling(0)
            self.device.scopes[0].triglevel(0.0)
            self.device.scopes[0].trighysteresis.mode(1)
            self.device.scopes[0].trighysteresis.relative(0.1)
            self.device.scopes[0].trigholdoffmode(0)
            self.device.scopes[0].trigholdoff(0.050)
            self.device.scopes[0].trigreference(0.25)
            self.device.scopes[0].trigdelay(0.0)
            self.device.scopes[0].triggate.enable(0)

        # Get the internal clock frequency of the device
        self.clockbase = self.device.clockbase()

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
            self.scope_module.execute()
            self.device.scopes[0].enable(True)
            self.session.sync()

            # Wait until at least one record is available
            while self.scope_module.records() == 0:
                time.sleep(0.05)

            data = self.scope_module.read()
            self.device.scopes[0].enable(False)
            self.scope_module.finish()

            self.records = data[self.wave_node]

            # Use the most recent record
            self.record = self.records[-1][0]

            self.wave = self.record["wave"][0, :]
            self.totalsamples = self.record["totalsamples"]
            self.dt = self.record["dt"]
            self.timestamp = self.record["timestamp"]
            self.triggertimestamp = self.record["triggertimestamp"]

            t = np.arange(-self.totalsamples, 0) * self.dt + (self.timestamp - self.triggertimestamp) / float(self.clockbase)
            t_us = 1e6 * t

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
            # poll() returns all data received since the last call (0.05 = timeout in [ms])
            data = self.session.poll(0.05)
            
            if sample_node in data:
                samples = data[sample_node]
                x = samples["x"]
                y = samples["y"]
                R = np.sqrt(x**2 + y**2)
                
                # Convert timestamps to seconds
                ts = (samples["timestamp"] - samples["timestamp"][0]) / self.clockbase
                
                # Append the data to the storage arrays
                R_array.extend(R)
                time_array.extend(ts + (last_time - start_time))
                last_time = time.time()

            time.sleep(0.1) # buffer
        
        sample_node.unsubscribe() # Unsubscribe from the node when done
        self.scan_data.emit(np.array(time_array), np.array(R_array)) # Emit the collected scan data

    def stop(self):
        self.is_running = False
