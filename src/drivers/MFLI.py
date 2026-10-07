from PyQt5 import QtCore
from collections import defaultdict
import time
from zhinst.toolkit import Session
import numpy as np
import matplotlib.pyplot as plt
from collections import deque


class MFLI():

    name = 'MFLI'
    sendProgress = QtCore.pyqtSignal(float)

    def __init__(self):
        super(MFLI, self).__init__()
        # Define the type of lock-in used
        #self.lock_in_type = lock_in_type
        self.lock_in_type = 'MFLI'

        # setting up the parameter dict
        self.parameter_dict = defaultdict()
        self.parameter_dict['filter_order'] = 0
        self.parameter_dict['time_constant'] = 0
        self.parameter_dict['Displayed_signal_input'] = 0
        self.parameter_display_dict = defaultdict(dict)

        self.parameter_display_dict['filter_order']['val'] = 3
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

        # set up parameter dict that only contains value
        self.parameter_dict = {}
        for key in self.parameter_display_dict.keys():
            self.parameter_dict[key] = self.parameter_display_dict[key]['val']

        # Connect to appropriate lock-in device
        #self.lock_in_type == 'MFLI'
        #self.session = Session("localhost")   # Create a session with the Data Server
        self.session = Session("192.168.1.116") # 192.168.1.116  127.0.0.1
        self.device = self.session.connect_device("DEV7797", interface="1GbE")  # Connect to the MFLI

        print('Connection established with the Lock-In')

        # Configure the first demodulation (verified the parameters)
        self.device.demods[0].enable(True)                                         # Enable the demodulator
        self.device.demods[0].order(self.parameter_dict['filter_order'])           # Set the filter order
        self.device.demods[0].timeconstant(self.parameter_dict['time_constant'])   # Set the time constant
        print('Configuration of the Lock-In completed')

        # set up R fi-fo
        self.r_history = deque(maxlen=4000)
        self.t_history = deque(maxlen=4000)

        # set up and start Worker
        self.worker = UpdateWorker(self.session,self.device)
        self.worker.sendPoll.connect(self.update_demodulator_values) # connect where signals of worker go to.
        self.worker.start()


    def set_parameter(self,parameter,value):
        if parameter == 'filter_order':
            self.update_filter_order(value)
            self.filter_order = value
        if parameter == 'time_constant':
            self.update_time_constant(value)
            self.time_constant = value
    
    def update_filter_order(self, filter_order):
        self.device.demods[0].order(filter_order)
        self.device.demods[4].order(filter_order)
        print(f'Filter order is set to {filter_order}')

    def update_time_constant(self, time_constant):
        self.device.demods[0].timeconstant(time_constant)
        print(f'Time constant set to {time_constant} s')


    def get_demodulator_values(self):
        return np.array(self.t_history), np.array(self.r_history)

    def update_demodulator_values(self,time_array,r_values):
        self.r_history.extend(r_values.tolist())
        self.t_history.extend(time_array.tolist())
        #print(f'The demodulator values are {r_values}')


class UpdateWorker(QtCore.QThread):
    """ This is a UpdateWorker for the MFLI.
    It continuously polls the last values of the demodulator and sends it to the driver.
     """
    # These are signals that allow to send data from a child thread to the parent hierarchy.
    sendPoll = QtCore.pyqtSignal(np.ndarray,np.ndarray)


    def __init__(self,Session, device):
        super(UpdateWorker, self).__init__() # Elevates this thread to be independent.

        # set up subscription of data poll
        self.Session = Session
        self.device = device
        self.demodulator = self.device.demods[0]
        self.sample_node = self.demodulator.sample
        self.sample_node.subscribe()
        self.poll_interval = 0.1
        self.terminate = False
        self.t0 = time.time()


    def run(self):
        """" Continuous tasks of the Worker are defined here.
        If loops check for requested changes in settings prior each acquisition. """
        while not self.terminate: #infinite loop
            self.t0 = time.time()
            data = self.Session.poll(recording_time=self.poll_interval)
            samples = data.get(self.sample_node)
            time.sleep(self.poll_interval/2)
            x_values = np.asarray(samples["x"]).ravel()
            y_values = np.asarray(samples["y"]).ravel()
            sample_count = min(len(x_values), len(y_values))
            r_values = np.sqrt(x_values[:sample_count] ** 2 + y_values[:sample_count] ** 2)
            time_array = np.linspace(self.t0, time.time(), sample_count)
            self.sendPoll.emit(time_array,r_values)
        print('Worker closes')
        return

