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
- consider implementing data storage for several data acquiring devices (e.g. 2 spectrometer simultaneously) 
"""


class DataHandling(QtCore.QThread):

    sendSpectrum = QtCore.pyqtSignal(np.ndarray, np.ndarray)
    sendMaximum = QtCore.pyqtSignal(np.ndarray) # not used for now, to be implemented for direct measurement control
    sendParameterarray = QtCore.pyqtSignal(np.ndarray, np.ndarray)
    bufferSaveSignal = QtCore.pyqtSignal(object, object, object, object)

    def __init__(self, parameter, speclength):
        super(DataHandling, self).__init__()
        self.parameter = parameter
        self.starttime = time.time()

        # initialize data arrays, their uses are explained in the corresponding functions
        self.speclength = speclength
        self.data_dim = np.size(speclength) #dimension of data
        self.parameter_queue = {} # initialize FIFO queues for parameter storage
        self.parameter_queue['time'] = deque(maxlen=100000)
        self.parameter_queue['absolute_time'] = deque(maxlen=100000)
        for param in self.parameter:
            self.parameter_queue[param] = deque(maxlen=100000)
        self.param_from_deque = np.zeros([len(self.parameter) + 2, 1])
        self.parameter_measured = np.zeros([len(self.parameter) + 2, 0])

        # preallocate data arrays depending on data dimension (1D or 2D).
        if self.data_dim  == 1:
            self.spec = np.empty([self.speclength, 0])
            self.background = np.empty([self.speclength, 1])
            self.wls = np.empty([self.speclength, 1])
        else:
            self.spec = np.empty([0,self.speclength[0],self.speclength[1]])
            self.background = np.empty([0,self.speclength[0],self.speclength[1]])
            self.wls = np.empty([self.speclength[1], 1])

        # set initial values
        self.maximum = np.zeros([3])
        self.correct_background = False
        self.send_x_idx = 'time'
        self.send_y_idx = 'absolute_time'

        # initialize parameter array
        self.parameter_matrix_full = False
        self.data_in_flash = 0
        self.firstbuffer = True
        self.temp_filename = r"C:\TEMP\temp.h5"
        self.filename = 'test'

        # initialize Calibration dict
        self.calibration = {}

        # initialize BufferWorker
        self.thread = QtCore.QThread()
        self.BufferWorker = BufferWorker(self.temp_filename,self.data_dim)
        self.BufferWorker.moveToThread(self.thread)
        self.thread.start()
        self.bufferSaveSignal.connect(self.BufferWorker.save_buffer)

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
        if self.data_dim == 1: # clear data arrays depending on dimension
            self.spec = np.empty([self.speclength, 0])
        else:
            self.spec = np.empty([1,self.speclength[0],self.speclength[1]])
        self.BufferWorker.firstbuffer = True
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
        self.wls = wls
        if self.data_dim == 1:
            self.spec = np.c_[self.spec, spec]
        else:
            self.spec = np.concatenate([self.spec, spec[np.newaxis,...]])
        for idx, param in enumerate(self.parameter_queue.keys()):
            self.param_from_deque[idx] = self.parameter_queue[param][-1]
        self.parameter_measured = np.c_[self.parameter_measured, self.param_from_deque]
        self.parameter_measured[0, -1] = curr_time
        self.parameter_measured[1, -1] = time.time()
        self.sendSpectrum.emit(wls, spec)
        # to prevent memory overload, save to temp file every 100th spectrum
        self.data_in_flash =self.data_in_flash + 1
        if self.data_in_flash > 49:
            self.save_buffer()
            self.data_in_flash = 0

        # Extract maxima of data to display them in SpectrumViewer
        self.maximum[1] = np.amax(spec)
        if self.data_dim == 1:
            self.maximum[2] = wls[np.argmax(spec)]
        else:
            self.maximum[2] = wls[np.unravel_index(spec.argmax(), spec.shape)[1]]
        self.maximum[0] = curr_time
        self.sendMaximum.emit(self.maximum)

    # save data to temp file and clear data in memory
    def save_buffer(self):
        """ Saves data to a temporary file and populates it each time more than 100 spectra have been acquired.
        If the file is created, some attributes such as yaxis and parameter keys are added."""
        t1 = time.time()
        self.bufferSaveSignal.emit(self.spec, self.wls, self.parameter_queue, self.parameter_measured)
        #print(time.time()-t1)
        # clear arrays in memory
        if self.data_dim == 1:
            self.spec = np.empty([self.speclength, 0])
        else:
            self.spec = np.empty([0,self.speclength[0],self.speclength[1]])
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
            hf.create_dataset("parameter", data=save_array, compression="gzip", chunks=True)
            hf['parameter'].attrs["parameter_keys"] = list(self.parameter_queue.keys())
        np.savetxt(filename, save_array)
        print('Parameter saved as: ' + filename)

    @QtCore.pyqtSlot(str, str)
    def save_data(self, filename, comments):
        """saves data. Each time data is saved, parameters are saved aswell. """
        self.save_buffer()
        time.sleep(0.5) # allow for BufferWorker to create temp file
        with h5py.File(self.temp_filename, 'a') as hf:
            hf.attrs["comments"] = comments
        ty_res = time.localtime(time.time())
        timestamp = time.strftime("%H_%M_%S", ty_res)
        savename = filename + '_' + timestamp + '.h5'
        shutil.copyfile(self.temp_filename, savename)
        print('Data saved as: ' + savename )

    #@QtCore.pyqtSlot
    def add_calibration(self,calibration):
        # to be used from calibration scripts. Each calibration should consist of a tuple of name and content
        calibration_name, calibration_value = calibration
        self.calibration[calibration_name] = calibration_value

    def add_attribute(self,attribute):
        # to be used from measurement each attribute should consist of a tuple of name and content
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
        # not used currently, to be implemented to continue aborted measurements/ after software crash
        pass

class BufferWorker(QtCore.QObject):
    """ Buffer worker saves data to a temp file.
    It is started every time a given amount of data has been acquired and receives signals with the corresponding data"""

    def __init__(self,temp_filename, data_dim):
        super(BufferWorker, self).__init__()
        self.temp_filename = temp_filename
        self.data_dim = data_dim
        self.firstbuffer = True
        print('BufferWorker started')
        self.terminate = False

        # check if folder for buffer exists
        temp_folder = os.path.dirname(temp_filename)
        if not os.path.isdir(temp_folder):
            print(f'No {temp_folder} folder, create folder')
            os.makedirs(temp_folder)
        else:
            pass

    @QtCore.pyqtSlot(object, object, object, object)
    def save_buffer(self,spec,wls,parameter_queue,parameter_measured):
        # check for first buffer saving to initialize data array
        t1 = time.time()
        if self.firstbuffer:
            try:
                os.remove(self.temp_filename) # clear temp file
            except FileNotFoundError:
                pass # no file to delete
            with h5py.File(self.temp_filename, 'w') as hf:
                if self.data_dim == 1:
                    hf.create_dataset("spectra", data=spec, compression="gzip", chunks=True,
                                      maxshape=(np.shape(spec)[0], None))
                else:
                    # float16 is used for camera pixels, as max values is 65504.
                    hf.create_dataset("spectra", data=spec, compression="gzip", chunks=True, maxshape=(None,np.shape(spec)[1],np.shape(spec)[2]),dtype='float16')
                hf["spectra"].attrs["xaxis"] = wls
                hf.create_dataset("parameter", data=parameter_measured, compression="gzip", chunks=True, maxshape=(np.shape(parameter_measured)[0],None))
                hf["parameter"].attrs["parameter_keys"] = list(parameter_queue.keys())
            print('First buffer saved')
            self.firstbuffer = False
        else:
            try:
                with h5py.File(self.temp_filename, 'a') as hf:
                    if self.data_dim == 1:
                        hf["spectra"].resize((hf["spectra"].shape[1] + spec.shape[1]), axis=1)
                        hf["spectra"][:, -spec.shape[1]:] = spec
                    else:
                        hf["spectra"].resize((hf["spectra"].shape[0] + spec.shape[0]), axis=0)
                        hf["spectra"][-spec.shape[0]:] = spec
                    hf["parameter"].resize((hf["parameter"].shape[1] + parameter_measured.shape[1]), axis=1)
                    hf["parameter"][:, -parameter_measured.shape[1]:] = parameter_measured
            except TypeError:
                print('Saving failed. Did you already save?')
