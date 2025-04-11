"""
Main Data Handling script. Should receive Data from Measurement and/or Hardware Interface classes. Used to order,
arrange and store data. Saves Data in a temp file during data acquirement to prevent memory storage to crash.
Sends Data to Data and Live Viewers. It can be handled as an object of measurement classes, such that measurement can
easily interact with predefined storage function. For now, measurements can send spectra and add attributes,
functionalities might have to be extended depending on the exact needs of the measurements.
Although passing through DataHandling when manupilation data is a bit complex, it helps to have hardware parameters
always assigned to the corresponding measurements.
"""
import time
from PyQt5 import QtCore, QtWidgets
import h5py
import numpy as np
import os.path
from collections import deque
import shutil
"""TO DOs: 
- check if more specific functions for dataset creation are needed. 
- think of a more clever way to store hardware parameters. Do we want it on command, a life-long storage, etc... 
"""


class DataHandling(QtCore.QThread):

    sendSpectrum = QtCore.pyqtSignal(np.ndarray, np.ndarray)
    sendMaximum = QtCore.pyqtSignal(np.ndarray) # not used for now, to be implemented for direct measurment control
    sendParameterarray = QtCore.pyqtSignal(np.ndarray, np.ndarray)
    sendBeams = QtCore.pyqtSignal(object)

    def __init__(self, parameter, speclength):
        super(DataHandling, self).__init__()
        self.parameter = parameter
        self.starttime = time.time()

        # initialize data arrays, their uses are explained in the corresponding functions
        self.speclength = speclength
        self.parameter_queue = {} # initialize FIFO queues for parameter storage
        self.parameter_queue['time'] = deque(maxlen=100000)
        self.parameter_queue['absolute_time'] = deque(maxlen=100000)
        for param in self.parameter:
            self.parameter_queue[param] = deque(maxlen=100000)
        self.param_from_deque = np.zeros([len(self.parameter) + 2, 1])
        self.parameter_measured = np.zeros([len(self.parameter) + 2, 0])
        self.spec = np.empty([self.speclength, 0])
        self.background = np.empty([self.speclength, 1])
        self.wavelength_axis = np.empty([self.speclength, 1])
        self.center_wavelength = 500
        self.maximum = np.zeros([3])
        self.correct_background = False
        self.send_x_idx = 'time'
        self.send_y_idx = 'absolute_time'
        # initialize parameter array
        self.parameter_matrix_full = False
        self.data_in_flash = 0
        self.firstbuffer = True
        self.temp_filename = r"C:\Data\temp.h5"
        self.filename = 'test'

        # initialize Calibration dict
        self.calibration = {}
        # initialize beams dict
        self.beams={}

    # main update device parameter function
    def update_parameter(self, parameter):
        """ This is an important part of hardware parameter control. We use "deque" as efficient First-In-First-Out
        Queues that allow to have a continuous acces to the last 100.000 hardware parameters. Each parameter has their
        on deque object. Each time the update parameter function is called by the updater, the most updated value of the
        hardware parameter is added to the deque"""
        self.parameter_queue['time'].append(time.time() - self.starttime)
        self.parameter_queue['absolute_time'].append(time.time())
        for idx, param in enumerate(self.parameter):
            self.parameter_queue[param].append(parameter[idx])
        self.sendParameterarray.emit(np.array(self.parameter_queue[self.send_x_idx]), np.array(self.parameter_queue[self.send_y_idx]))

    def clear_data(self):
        """Each time a new measurement is started, DataHandling is reset."""
        self.starttime = time.time()
        self.spec = np.empty([self.speclength, 0])
        self.firstbuffer = 1
        self.parameter_measured = np.zeros([len(self.parameter) + 2, 0])
        try:
            os.remove(self.temp_filename)
        except:
            pass

    def concatenate_data(self, wls, spec):
        """ This function concatenates all received spectra. it keeps the last 100 spectra directly accessible. If
        more than 100 spectra are acquired, they are buffersaved in a .h5 file, to prevent memory overload and allow
        acquisiton of infinite spectra. """
        # add data to data array, not used for now
        curr_time = time.time() - self.starttime
        self.wavelength_axis = wls
        self.spec = np.c_[self.spec, spec]
        for idx, param in enumerate(self.parameter_queue.keys()):
            self.param_from_deque[idx] = self.parameter_queue[param][-1]
        self.parameter_measured = np.c_[self.parameter_measured, self.param_from_deque]
        self.parameter_measured[0, -1] = curr_time
        self.parameter_measured[1, -1] = time.time()
        self.sendSpectrum.emit(wls, spec)
        # to prevent memory overload, save to temp file every 100th spectrum
        self.data_in_flash =self.data_in_flash + 1
        if self.data_in_flash > 99:
            self.save_buffer()
            self.data_in_flash = 0

        # Extract maxima of data to display them in SpectrumViewer
        self.maximum[1] = np.amax(spec)
        self.maximum[2] = wls[np.argmax(spec)]
        self.maximum[0] = curr_time
        self.sendMaximum.emit(self.maximum)

    # save data to temp file and clear data in memory
    def save_buffer(self):
        """ Saves data to a temporary file and populates it each time more than 100 spectra have been acquired.
        If the file is created, some attributes such as yaxis and parameter keys are added."""
        # check for first buffer saving to initialize data array
        if self.firstbuffer:
            spectrum_w_param = np.vstack([self.parameter_measured, self.spec])
            print(np.shape(spectrum_w_param))
            with h5py.File(self.temp_filename, 'w') as hf:
                hf.create_dataset("spectra", data=spectrum_w_param, compression="gzip", chunks=True, maxshape=(np.shape(spectrum_w_param)[0],None))
                hf["spectra"].attrs["yaxis"] = self.wavelength_axis
                hf["spectra"].attrs["parameter_keys"] = list(self.parameter_queue.keys())
            print('First buffer saved')
            self.firstbuffer = False
        else:
            spectrum_w_param = np.vstack([self.parameter_measured, self.spec])
            with h5py.File(self.temp_filename, 'a') as hf:
                hf["spectra"].resize((hf["spectra"].shape[1] + spectrum_w_param.shape[1]), axis=1)
                hf["spectra"][:,-spectrum_w_param.shape[1]:] = spectrum_w_param

        # clear arrays in memory
        self.spec = np.empty([self.speclength, 0])
        self.parameter_measured = np.zeros([len(self.parameter) + 2, 0])

    def save_parameter(self, filename):
        """ Saves parameters to an independent .h5 file. We still might want to adapt how this is handled."""
        save_length = len(self.parameter_queue['time'])
        save_array = np.empty((len(self.parameter_queue), save_length))
        for idx, param in enumerate(self.parameter_queue.keys()):
            save_array[idx, :] = np.array(self.parameter_queue[param])[0:save_length]
        ty_res = time.localtime(time.time())
        timestamp = time.strftime("%H_%M_%S", ty_res)
        with h5py.File( filename + '_' + timestamp + '_parameters.h5', 'w') as hf:
            hf.create_dataset("Parameter", data=save_array, compression="gzip", chunks=True)
            hf['Parameter'].attrs["parameter_keys"] = list(self.parameter_queue.keys())
        np.savetxt(filename, save_array)
        print('Parameter saved as: ' + filename)

    @QtCore.pyqtSlot(str, str)
    def save_data(self, filename, comments):
        """saves data. Each time data is saved, parameters are saved as well. """
        self.save_buffer()
        with h5py.File(self.temp_filename, 'a') as hf:
            hf.attrs["comments"] = comments
        ty_res = time.localtime(time.time())
        timestamp = time.strftime("%H_%M_%S", ty_res)
        shutil.copyfile(self.temp_filename, filename + '_' + timestamp + '.h5')
        self.save_parameter(filename)
        print('Data saved ')

        # For now adding a worker for saving appears not be needed, if at some point DataHandling gets too busy, we
        # might want to outsource it to an independent worker.
        #self.save_worker_thread = SaveWorker(filename, comments, self.parameter, self.spectrumlength, self.temp_filename)
        #self.save_worker_thread.start()


    #@QtCore.pyqtSlot
    def add_calibration(self,calibration):
        # to be used from calibration scripts. Each calibration should consist of a tuple of name and content
        calibration_name, calibration_value = calibration
        self.calibration[calibration_name] = calibration_value
    
    def set_beam(self, name_and_beam):
        '''
            Adds or updates the beam at the provided index
            input:
                - tuple: (name,Beam) First argument of tuple is beam name and second is Beam object to set
        '''
        beam_name,beam=name_and_beam
        self.beams[beam_name]=beam

    def get_beams(self):
        '''
            Triggers emission of beams to connected slots when called
        '''
        self.sendBeams.emit(self.beams)
        return self.beams

    def add_attribute(self,attribute):
        # to be used from measurment each attribute should consist of a tuple of name and content
        attribute_name, attribute_value = attribute
        with h5py.File(self.temp_filename, 'a') as hf:
            hf["spectra"].attrs[attribute_name] = attribute_value

    def change_send_idx(self, x_idx, y_idx):
        # this function changes the parameter that are sent to parameter display.
        self.send_x_idx = list(self.parameter_queue)[x_idx]
        self.send_y_idx = list(self.parameter_queue)[y_idx]

    def overwrite_popup(self):
        # not used currently, as time stamp prevents to have overwrite scenarios.
        msgBox = QtWidgets.QMessageBox()
        msgBox.setIcon(QtWidgets.QMessageBox.Information)
        msgBox.setText("Data File already exists. Overwrite?")
        msgBox.setWindowTitle("Warning")
        msgBox.setStandardButtons(QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel)
        returnValue = msgBox.exec()
        if returnValue == QtWidgets.QMessageBox.Ok:
            print('Yes, Overwrite!')
            return True
        else:
            print('Cancel')
            return False

    def load_data(self):
        pass
"""
class SaveWorker(QtCore.QThread):

    def __init__(self, filename, comments, parameter, spectrumlength, temp_filename):
        super(SaveWorker, self).__init__()
        self.filename = filename
        self.comments = comments
        self.parameter = parameter
        self.spectrumlength = spectrumlength
        self.temp_filename = temp_filename
        print('SAVE started')

    def run(self):
        # get time for timestamp
        ty_res = time.localtime(time.time())
        timestamp = time.strftime("%H_%M_%S", ty_res)
        from_file = self.temp_filename

        # save comments
        comments_file = self.filename + '_metadata_' + timestamp + '.dat'
        with open(comments_file, 'w') as file:
            file.write(self.comments)
            file.write('\n \n \n###### Measurement parameters ###### \n')
            for param in self.parameter.keys():
                file.write(param + ': ' + str(self.parameter[param]) + '\n')

        # transpose data from temp file to final file. Saving in rows is faster than in columns
        # convert CSV with rows to columns using batches (required for large files)
        NCOLS = self.spectrumlength[0]  # The exact number of columns
        batch_size = 50
        to_file = self.filename + '_' + timestamp + '.csv'
        for batch in range(NCOLS // batch_size + bool(NCOLS % batch_size)):
            lcol = batch * batch_size
            rcol = min(NCOLS, lcol + batch_size)
            data = pd.read_csv(from_file, usecols=range(lcol, rcol), header=None)
            with open(to_file, 'a') as _f:
                data.T.to_csv(_f, header=None, index=None, line_terminator='\n')
        print('Data saved as: ' + to_file)
        return
"""