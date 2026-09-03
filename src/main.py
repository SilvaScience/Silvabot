# -*- coding: utf-8 -*-
"""
Created on Tue Jan  1 14:34:11 2025
@author: David Tiede
"""

import sys
import time
import re
import os
from collections import defaultdict
from pathlib import Path
import numpy as np
from PyQt5 import QtCore, QtWidgets, uic
from functools import partial
from GUI.ParameterPlot import ParameterPlot
from GUI.SpectrometerPlot import SpectrometerPlot
from drivers.CryoDemo import CryoDemo
from drivers.SpectrometerDemo_advanced import SpectrometerDemo
from drivers.SLMDemo import SLMDemo
from drivers.StresingDemo import StresingDemo
from drivers.MonochromDemo import MonochromDemo
from drivers.PixisDemo import PixisDemo
#from drivers.Pixis import Pixis
from drivers.Cryocore import Cryocore
from drivers.ThorlabsPM100D import ThorlabsPM100D
from drivers.ThorlabsPM100DDemo import ThorlabsPM100DDemo
from DataHandling.DataHandling import DataHandling
from measurements.MeasurementClasses import AcquireMeasurement,RunMeasurement,BackgroundMeasurement, \
    ViewMeasurement, KineticMeasurement, TSeriesMeasurement, THzAcquisition, ScopeView, Autocorrelation

from drivers.PI863 import PI863
from drivers.PI863Demo import PI863Demo
from drivers.Lock_InDemo import Lock_InDemo
from drivers.Lock_In import Lock_In


class MainInterface(QtWidgets.QMainWindow):

    def __init__(self):
        super(MainInterface, self).__init__()
        project_folder = Path(__file__).parent.resolve()
        uic.loadUi(Path(project_folder,r'GUI/main_GUI.ui'), self)

        # fancy name
        self.setWindowTitle('Silvabot')

        # set devices dict
        self.devices = defaultdict(dict)

        # initialize spectrometer
        self.spectrometer = SpectrometerDemo()
        self.spec_length = self.spectrometer.spec_length
        self.devices['spectrometer'] = self.spectrometer

        # initialize delay stage
        try:
            self.tstage = PI863()
        except:
            self.tstage = PI863Demo()
            print('WARNING you are using a DEMO version of the translation stage')
        self.devices['tstage'] = self.tstage

        # initialize lock-in
        try:
            lock_in_type = 'UHF' # can be changed to other types if implemented
            self.lock_in = Lock_In(lock_in_type=lock_in_type)
        except:
            self.lock_in = Lock_InDemo()
            print('WARNING you are using a DEMO version of the lock in')
        self.devices['lock_in'] = self.lock_in

        # initialize Powermeter
        try:
            self.powermeter = ThorlabsPM100D()
            print('Thorlabs powermeter connected')
        except:
            self.powermeter = ThorlabsPM100DDemo()
            print('WARNING you are using a DEMO version of the powermeter')
        self.devices['powermeter'] = self.powermeter

        # initialize SLMDemo
        #self.SLM = SLMDemo()
        #self.devices['SLM'] = self.SLM
        #print('SLMDemo connected')

        # initialize StresingDemo
        #self.Stresing = StresingDemo()
        #self.devices['Stresing'] = self.Stresing
        #print('Stresing connected')

        # initialize MonochromDemo
        #self.Monochrom = MonochromDemo()
        #self.devices['Monochrom'] = self.Monochrom
        #print('Monochrom DEMO connected')

        # initialize cryostat
        # always try to include communication on important events.
        # This is extremely useful for debugging and troubleshooting.
        # try:
        #     self.cryostat = CryoDemo() # launch cryostat interface
        #     print('Connected to Montana CryoCore')
        # except:
        #     self.cryostat = CryoDemo()
        #     print('WARNING you are using a DEMO version of the cryostat')
        # self.devices['cryostat'] = self.cryostat

        # initialize Spectrometer
        # try:
        #     self.spectrometer = Pixis()
        #     print('Pixis camera connected')
        # except:
        #     self.spectrometer = PixisDemo()
        #     print('Pixis connection failed, use DEMO')

        # find items to complement in GUI
        self.parameter_tree = self.findChild(QtWidgets.QTreeWidget, 'parameters_treeWidget')
        self.spectro_tab = self.findChild(QtWidgets.QWidget, 'spectro_tab')
        self.parameter_tab = self.findChild(QtWidgets.QWidget, 'parameter_tab')
        self.thz_tab = self.findChild(QtWidgets.QWidget, 'thz_tab')
        self.thz_acquisition = self.findChild(QtWidgets.QPushButton, 'thz_acquisition')
        self.autocorrelation = self.findChild(QtWidgets.QPushButton, 'autocorrelation')
        self.thz_clear = self.findChild(QtWidgets.QPushButton, 'thz_clear')
        self.thz_plot_group = self.findChild(QtWidgets.QGroupBox, 'thz_plot_group')
        self.acquire_button = self.findChild(QtWidgets.QPushButton, 'acquire_pushButton')
        self.view_button = self.findChild(QtWidgets.QPushButton, 'view_pushButton')
        self.run_button = self.findChild(QtWidgets.QPushButton, 'run_pushButton')
        self.stop_button = self.findChild(QtWidgets.QPushButton, 'stop_pushButton')
        self.Scope_view_button = self.findChild(QtWidgets.QPushButton, 'Scope_view_pushButton')
        self.save_folder_button = self.findChild(QtWidgets.QPushButton, 'folder_pushButton')
        self.save_button = self.findChild(QtWidgets.QPushButton, 'save_pushButton')
        self.comments_edit = self.findChild(QtWidgets.QTextEdit, 'comments_textEdit')
        self.filename_edit = self.findChild(QtWidgets.QLineEdit, 'filename_lineEdit')
        self.progress_bar = self.findChild(QtWidgets.QProgressBar, 'progressBar')
        self.bg_button = self.findChild(QtWidgets.QPushButton, 'Acquire_bg_pushButton')
        self.bg_check_box = self.findChild(QtWidgets.QCheckBox, 'bg_checkBox')
        self.bg_file_indicator = self.findChild(QtWidgets.QLineEdit, 'bg_file_lineEdit')
        self.bg_scans_box = self.findChild(QtWidgets.QSpinBox, 'bg_scans_spinBox')
        self.bg_select_box = self.findChild(QtWidgets.QPushButton, 'select_bg_pushButton')
        self.kinetic_lineEdit = self.findChild(QtWidgets.QLineEdit, 'kinetic_lineEdit')
        self.kinetic_run_button = self.findChild(QtWidgets.QPushButton, 'kinetic_run_pushButton')
        self.SLM_tab = self.findChild(QtWidgets.QWidget, 'SLM_tab')
        self.Tseries_lineEdit = self.findChild(QtWidgets.QLineEdit, 'Tseries_lineEdit')
        self.Tseries_stab_time_box = self.findChild(QtWidgets.QSpinBox, 'Tseries_stab_time_spinBox')
        self.Tseries_run_button = self.findChild(QtWidgets.QPushButton, 'Tseries_run_pushButton')
        self.Tseries_ref_power_box = self.findChild(QtWidgets.QDoubleSpinBox, 'Tseries_ref_power_doubleSpinBox')
        self.Tseries_int_time_WL_box = self.findChild(QtWidgets.QDoubleSpinBox, 'Tseries_int_time_WL_doubleSpinBox')
        self.Tseries_int_time_orpheus_box = self.findChild(QtWidgets.QDoubleSpinBox, 'Tseries_int_time_orpheus_doubleSpinBox')
        self.Tseries_power_dep_checkBox = self.findChild(QtWidgets.QCheckBox, 'Tseries_power_dep_checkBox')
        self.Tseries_two_sources_checkBox = self.findChild(QtWidgets.QCheckBox, 'Tseries_two_sources_checkBox')
        self.Tseries_spectra_avg_box = self.findChild(QtWidgets.QSpinBox, 'Tseries_spectra_avg_spinBox')
        self.Tseries_lineEdit = self.findChild(QtWidgets.QLineEdit, 'Tseries_lineEdit')
        self.Tseries_int_time_lineEdit = self.findChild(QtWidgets.QLineEdit, 'Tseries_int_time_lineEdit')
        self.Tseries_filter_pos_lineEdit = self.findChild(QtWidgets.QLineEdit, 'Tseries_filter_pos_lineEdit')

        # initial parameter values, retrieved from devices
        self.parameter_dic = defaultdict(lambda: defaultdict(dict))
        for device in self.devices.keys():
            self.parameter_dic[device] = self.devices[device].parameter_display_dict

        # create parameter array for easy access
        self.create_parameter_array()

        # add items to GUI
        self.SpectrometerPlot = SpectrometerPlot()
        vbox = QtWidgets.QVBoxLayout()
        vbox.addWidget(self.SpectrometerPlot)
        self.spectro_tab.setLayout(vbox)
        self.ParameterPlot = ParameterPlot(self.parameter_dic)
        vbox = QtWidgets.QVBoxLayout()
        vbox.addWidget(self.ParameterPlot)
        self.parameter_tab.setLayout(vbox)

        vbox = QtWidgets.QVBoxLayout()
        if hasattr(self, 'SLM'):
            vbox.addWidget(self.SLM)
        self.SLM_tab.setLayout(vbox)

        # Initialize the THz tab with plot widget
        import pyqtgraph as pg
        self.thz_plot_widget = pg.PlotWidget(title="THz Plot")
        self.thz_plot_widget.setLabel('left', 'Intensity')
        self.thz_plot_widget.setLabel('bottom', 'Frequency')
        thz_plot_layout = self.thz_plot_group.layout()
        if thz_plot_layout is None:
            thz_plot_layout = QtWidgets.QVBoxLayout()
            self.thz_plot_group.setLayout(thz_plot_layout)
        thz_plot_layout.addWidget(self.thz_plot_widget)

        """ This initializes the parameter tree. It is constructed based on the device dict, 
        that includes parameter information of each device """
        self.parameter_tree.setColumnCount(2)
        self.parameter_tree.setHeaderLabels(["Name", "Value"])
        self.parameter_widgets = {}
        self.readonly_parameter = []
        self.writeonly_parameter = []
        for device in self.parameter_dic.keys():
            item = QtWidgets.QTreeWidgetItem([device.capitalize()])
            self.parameter_tree.addTopLevelItem(item)
            for param in self.parameter_dic[device].keys():
                child =QtWidgets.QTreeWidgetItem()
                item.addChild(child)
                name_widget = QtWidgets.QLabel(param)
                self.parameter_widgets[param] = QtWidgets.QDoubleSpinBox()
                #self.parameter_widgets[param].setFixedSize(self.parameter_widgets[param].__sizeof__(), 16)
                self.parameter_widgets[param].setReadOnly(self.parameter_dic[device][param]['read'])
                try:
                    self.parameter_widgets[param].setSuffix(self.parameter_dic[device][param]['unit'])
                    self.parameter_widgets[param].setMaximum(self.parameter_dic[device][param]['max'])
                except:
                    pass
                try:
                    self.parameter_widgets[param].setMinimum(self.parameter_dic[device][param]['min'])
                except:
                    pass
                if self.parameter_dic[device][param]['read']:
                    self.readonly_parameter.append(param)
                else:
                    self.parameter_widgets[param].setValue(self.parameter_dic[device][param]['val'])
                    self.parameter_widgets[param].editingFinished.connect(partial(self.set_parameter,param))
                    self.writeonly_parameter.append(param)
                self.parameter_tree.setItemWidget(child, 0, name_widget)
                self.parameter_tree.setItemWidget(child, 1, self.parameter_widgets[param])

        # start DataHandling
        self.DataHandling = DataHandling(self.parameter, self.spec_length)
        self.DataHandling.sendParameterarray.connect(self.ParameterPlot.set_data)
        self.DataHandling.sendSpectrum.connect(self.SpectrometerPlot.set_data)
        self.DataHandling.sendMaximum.connect(self.SpectrometerPlot.update_datareader)

        # start Updater to update device read parameters
        self.Updater = UpdateWorker(self.devices, self.readonly_parameter)
        self.Updater.new_parameter.connect(self.update_read_parameter)
        self.Updater.start()

        # set variables
        self.measurement_busy = False
        self.save_folder_path = r'C:/TEMP'
        #a default data folder is always required and it would be good to keep it seperated from the code.
        #can everyone simply create a C:/Data/test' path on their device? # Not sure how to handle different OS here.
        self.filename = r'C:/TEMP/test'
        self.power_calib_array = []

        # set connect events
        self.acquire_button.clicked.connect(self.acquire_measurement)
        self.view_button.clicked.connect(self.view_measurement)
        self.run_button.clicked.connect(self.run_measurement)
        self.stop_button.clicked.connect(self.stop_measurement)
        self.Scope_view_button.clicked.connect(self.Scope_view)
        self.filename_edit.editingFinished.connect(self.change_filename)
        self.save_button.clicked.connect(self.save_data)
        self.save_folder_button.clicked.connect(self.change_folder)
        self.bg_button.clicked.connect(self.background_measurement)
        self.bg_select_box.clicked.connect(self.load_bg)
        self.bg_check_box.stateChanged.connect(self.update_check_bg)
        self.ParameterPlot.send_idx_change.connect(self.DataHandling.change_send_idx)
        self.ParameterPlot.send_parameter_filename.connect(self.DataHandling.save_parameter)
        self.kinetic_lineEdit.editingFinished.connect(self.change_kinetic_interval)
        self.kinetic_run_button.clicked.connect(self.kinetic_measurement)
        self.Tseries_lineEdit.editingFinished.connect(self.change_Tseries)
        self.Tseries_run_button.clicked.connect(self.Tseries_measurement)
        
        # THz tab button connections
        self.thz_acquisition.clicked.connect(self.thz_acquisition_measurement)
        self.autocorrelation.clicked.connect(self.Autocorrelation_measurement)
        self.thz_clear.clicked.connect(self.THz_clear)

        # run some functions once to define default values
        self.change_filename()

        # show GUI, to be executed at the end of init.
        self.show()

    ##### General functions #####

    def create_parameter_array(self):
        # initialization function to store all parameters in one array
        self.parameter = {}
        for devices in self.devices.keys():
            for param in self.devices[devices].parameter_dict.keys():
                self.parameter[param] = self.devices[devices].parameter_dict[param]

    def update_read_parameter(self, new_parameter):
        # update all read parameters
        for param in new_parameter.keys():
            self.parameter_widgets[param].setValue(new_parameter[param])
            self.parameter[param] = new_parameter[param]
        # send parameters to DataViewer
        self.DataHandling.update_parameter(list(self.parameter.values()))

    def change_parameter(self, parameter, value):
        # change parameter when called from another script
        self.parameter_widgets[parameter].setValue(value)
        self.set_parameter(parameter)

    def set_parameter(self, new_parameter):
        # set parameter when Spinbox is changed and send it to devices and DataHandling
        for device in self.devices.keys():
            if new_parameter in self.devices[device].parameter_dict.keys():
                # get parameter from widget
                value = self.parameter_widgets[new_parameter].value()
                self.devices[device].set_parameter(new_parameter, value)
                # change parameter in DataHandling
                self.parameter[new_parameter] = value

    def test(self):
        # test function to test anything
        print('I am testing')

    def set_progress(self, progress):
        # set progress bar and define whether a measurement is running. When progess ne 100, no new measurement starts
        self.progress_bar.setValue(int(progress))
        if progress == 100.:
            self.measurement_busy = False

    def change_folder(self):
        # select folder to save data
        self.save_folder_path = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select data saving folder')
        print('Data folder: ' + str(self.save_folder_path))
        self.change_filename()

    def change_filename(self):
        # change filename to string of LineEdit
        self.filename = str(self.save_folder_path) + "/" + str(self.filename_edit.text().strip('\n'))
        print('filename changed to: ' + str(self.filename))

    def save_data(self):
        # save data
        self.DataHandling.save_data(self.filename, self.comments_edit.toPlainText())

    def load_bg(self):
        # open background file and set as background
        BackgroundFile = QtWidgets.QFileDialog.getOpenFileName(self, 'Select background data')
        bg_path = BackgroundFile[0]
        bg = np.loadtxt(bg_path, delimiter=',')
        self.DataHandling.background = bg[-self.spec_length:, 1]
        # print(np.shape(bg[1:,1]))

        # display background filename
        idx = bg_path.rfind('/')
        self.bg_file_indicator.setText(bg_path[idx+1:])

    def update_check_bg(self):
        self.DataHandling.correct_background = self.bg_check_box.isChecked()

    def change_kinetic_interval(self):
        # generate timing array for time resolved measurement
        try:
            self.kinetic_interval = []
            txt = self.kinetic_lineEdit.text()
            for s in re.split(' ', txt):
                if s == "o":
                    self.kinetic_interval.append('open')
                elif s == "c":
                    self.kinetic_interval.append('close')
                elif s == "":
                    pass
                    pass
                elif s[0] == "p":
                    numbers = re.split(":", s[1:])
                    probint = np.linspace(float(numbers[0]), float(numbers[2]), int(numbers[1]))
                    for i in range(len(probint)):
                        self.kinetic_interval.append('p'+str(probint[i]))
                else:
                    numbers = re.split(':', s)
                    self.kinetic_interval.append(np.linspace(float(numbers[0]), float(numbers[2]), int(numbers[1])))
            print('Kinetic Interval: ' + str(self.kinetic_interval))
        except:
            print('Lecture of kinetic interval failed')

    def change_Tseries(self):
        # generate temperature array for T dep measurement
        try:
            self.Tseries =[]
            txt = self.Tseries_lineEdit.text()
            i = 0
            digits = {}
            for s in re.split(':| ', txt):
                if s.replace(".", "", 1).isdigit():
                    digits[i] = s
                    i = i+1.
            for j in range(int(i/3)):
                self.Tseries = np.append(self.Tseries, np.linspace(float(digits[3*j]), float(digits[3*j+2]), int(digits[3*j+1])))
            print('T series : ' + str(self.Tseries))
        except:
            print('Lecture of T series failed')

    ##### Measurements #####

    def acquire_measurement(self):
        # take one spectrum with spectrometer
        if self.measurement_busy:
            try:
                self.measurement.take_spectrum()
            except AttributeError:
                print('Measurement not started, devices are busy')
        else:
            self.measurement_busy = True
            self.DataHandling.clear_data()
            self.measurement = AcquireMeasurement(self.devices, self.parameter)
            self.measurement.sendProgress.connect(self.set_progress)
            self.measurement.sendSpectrum.connect(self.DataHandling.concatenate_data)
            self.measurement.start()

    def view_measurement(self):
        # take one spectrum with spectrometer
        if not self.measurement_busy:
            self.measurement_busy = True
            self.DataHandling.clear_data()
            self.measurement = ViewMeasurement(self.devices, self.parameter)
            self.measurement.sendProgress.connect(self.set_progress)
            self.measurement.sendSpectrum.connect(self.DataHandling.concatenate_data)
            self.measurement.sendClear.connect(self.SpectrometerPlot.clear_plot)
            self.measurement.start()
        else:
            print('Measurement not started, devices are busy')

    def run_measurement(self):
        # continuously taking spectra with spectrometer
        if not self.measurement_busy:
            self.measurement_busy = True
            self.DataHandling.clear_data()
            self.measurement = RunMeasurement(self.devices, self.parameter)
            self.measurement.sendProgress.connect(self.set_progress)
            self.measurement.sendSpectrum.connect(self.DataHandling.concatenate_data)
            self.measurement.start()
        else:
            print('Measurement not started, devices are busy')

    def background_measurement(self):
        # acquire background to subtract from spectra. May average over several spectra
        if not self.measurement_busy:
            self.measurement_busy = True
            self.DataHandling.clear_data()
            self.measurement = BackgroundMeasurement(self.devices, self.parameter, self.bg_scans_box.value(),
                                                     self.filename, self.comments_edit.toPlainText())
            self.measurement.sendProgress.connect(self.set_progress)
            self.measurement.sendSpectrum.connect(self.DataHandling.concatenate_data)
            self.measurement.sendSave.connect(self.DataHandling.save_data)
            self.measurement.start()
        else:
            print('Measurement not started, devices are busy')

    def kinetic_measurement(self):
        # take time resolved measurements as defined in automation GUI section
        if not self.measurement_busy:
            self.measurement_busy = True
            #self.DataPlot.clear_data()
            self.DataHandling.clear_data()
            self.change_kinetic_interval()
            self.measurement =KineticMeasurement(self.devices, self.parameter, self.kinetic_interval)
            self.measurement.sendProgress.connect(self.set_progress)
            self.measurement.sendSpectrum.connect(self.DataHandling.concatenate_data)
            self.measurement.sendParameter.connect(self.change_parameter)
            self.measurement.start()
        else:
            print('Measurement not started, devices are busy')

    def Tseries_measurement(self):
        # take temperature dependent measurements as defined in automation GUI section
        if not self.measurement_busy:
            print('Start T-Dependent Measurement ')
            self.measurement_busy = True
            self.DataHandling.clear_data()
            self.measurement = TSeriesMeasurement(self.devices, self.parameter, self.Tseries,
                                                  self.Tseries_stab_time_box.value(),self.Tseries_two_sources_checkBox.isChecked(),
                                                  self.Tseries_ref_power_box.value(),self.Tseries_int_time_WL_box.value(),
                                                  self.Tseries_int_time_orpheus_box.value(),
                                                  self.Tseries_spectra_avg_box.value(),
                                                  self.Tseries_power_dep_checkBox.isChecked(),
                                                  self.Tseries_filter_pos_lineEdit.text(),
                                                  self.Tseries_int_time_lineEdit.text())
            self.measurement.sendProgress.connect(self.set_progress)
            self.measurement.sendSpectrum.connect(self.DataHandling.concatenate_data)
            self.measurement.sendParameter.connect(self.change_parameter)
            self.measurement.start()

    def stop_measurement(self):
        # stop measurement
        self.measurement.stop()
        self.measurement_busy = False

    def thz_acquisition_measurement(self):
        # Conducts a THz measurement using the translation stage and the lock in.
        if not self.measurement_busy:
            self.measurement_busy = True
            self.measurement = THzAcquisition(self.devices, self.thz_plot_widget)
            self.measurement.sendProgress.connect(self.set_progress)
            self.measurement.sendSpectrum.connect(self.DataHandling.concatenate_data)
            self.DataHandling.spec_length = self.measurement.spec_length
            self.DataHandling.clear_data()
            self.measurement.start()
        else:
            print('Measurement not started, devices are busy')
    
    def Scope_view(self):
        # This function plots scope data from the UHF lock-in amplifier and plots it (acts like the Scope in LabOne)
        if not self.measurement_busy:
            self.measurement_busy = True
            self.DataHandling.clear_data()
            self.measurement = ScopeView(self.devices)
            self.measurement.sendProgress.connect(self.set_progress)
            self.measurement.sendSpectrum.connect(self.DataHandling.concatenate_data)
            self.measurement.clearPlot.connect(self.SpectrometerPlot.clear_plot)
            self.measurement.start()
        else:
            print('Measurement not started, devices are busy')
    
    def Autocorrelation_measurement(self):
        # start an autocorrelation scan using parameters from Tstage dropdown menu
        if not self.measurement_busy:
            self.measurement_busy = True
            self.DataHandling.clear_data()

            # Get parameters for autocorrelation from the GUI
            initial_pos = self.tstage.parameter_dict['scan_initial_position']
            final_pos = self.tstage.parameter_dict['scan_final_position']
            interval = self.tstage.parameter_dict.get('autocorrelation_interval',
                                                        self.tstage.parameter_dict.get('autocorrelation_step'))

            # Run the autocorrelation measurement
            self.measurement = Autocorrelation(self.devices, initial_pos, final_pos, interval, plot_widget=self.thz_plot_widget)
            
            # Connect the different signals
            self.measurement.sendProgress.connect(self.set_progress)
            self.measurement.sendSpectrum.connect(self.DataHandling.concatenate_data)
            self.measurement.sendSpectrum.connect(self.plot_autocorrelation)
            self.measurement.start()
        else:
            print('Measurement not started, devices are busy')
    
    def plot_autocorrelation(self, times_in_ps, power_in_nW):
        """Plot autocorrelation data vs time on the THz plot widget"""
        if self.thz_plot_widget is not None:
            self.thz_plot_widget.clear()
            self.thz_plot_widget.plot(times_in_ps, power_in_nW * 1e-3, pen='b')
            self.thz_plot_widget.setLabel('bottom', 'Time (ps)')
            self.thz_plot_widget.setLabel('left', 'Power (µW)')
    
    def THz_clear(self):
        self.thz_plot_widget.clear()

    def closeEvent(self, event):
        # Function that executes when the GUI is closed to appropriately disconect the translation stage (Other disconections may be added)
        self.tstage.pidevice.CloseConnection()
        print("Translation stage disconnected")
        event.accept()

class UpdateWorker(QtCore.QThread):

    new_parameter = QtCore.pyqtSignal(dict)

    def __init__(self, devices_dic, read_only):
        super(UpdateWorker, self).__init__()
        self.devices = devices_dic
        self.read_only = read_only
        self.stop = False
        self.updated_param = {}
        self.update_interval = 0.5

    def run(self):
        while not self.stop:
            i = 0
            for devices in self.devices.keys():
                for param in self.devices[devices].parameter_dict.keys():
                    if param in self.read_only:
                        self.updated_param[param] = self.devices[devices].parameter_dict[param]
                self.new_parameter.emit(self.updated_param)
            time.sleep(self.update_interval)


app = QtWidgets.QApplication(sys.argv)
window = MainInterface()
app.exec_()
