import yaml
import importlib
import sys
import time
import numpy as np
import re
from collections import defaultdict
from pathlib import Path
from PyQt5 import QtCore, QtWidgets, uic
from functools import partial
from GUI.ParameterPlot import ParameterPlot
from GUI.SpectrometerPlot import SpectrometerPlot
from DataHandling.DataHandling import DataHandling


def load_class(path):
    # loads a class from a project-defined path. Returns the class
    module_name, class_name = path.rsplit(".", 1)
    return getattr(importlib.import_module(module_name), class_name)


def create_device(path, init_args=None):
    # Initializes a class from project-defined path. Returns the called class
    cls = load_class(path)
    return cls(**(init_args or {}))


class MainInterface(QtWidgets.QMainWindow):

    def __init__(self):
        super().__init__()

        self.project_folder = Path(__file__).parent.resolve()
        uic.loadUi(self.project_folder / 'GUI/main_GUI.ui', self)

        self.setWindowTitle('Silvabot')
        self.devices = defaultdict(dict)

        # load devices from config file
        self.config_path = self.project_folder / "config.yaml"
        try:
            self.config = yaml.safe_load(open(self.config_path))
        except FileNotFoundError as e:
            print(f'Config file not found. {e}. \n Consider renaming config_default in src folder.')

        # load each devices indicated in config file with a centralized loading routine
        for name, cfg in self.config["devices"].items():
            if not cfg.get("enabled", False): # check if device should be loaded
                continue
            init_args = cfg.get("init_args", {})
            driver = cfg["driver"]
            fallback = cfg.get("fallback")
            #initialize device
            try:
                device = create_device(driver, init_args)
                print(f"{name}: {driver.split('.')[-1]} connected")
            except Exception as e: # catch if loading device failed
                print(f"{name}: {driver.split('.')[-1]} failed ({e})")
                if not fallback: # continue, if no fallback driver is defined
                    continue
                device = create_device(fallback, init_args)
                print(f"{name}: {fallback.split('.')[-1]} (fallback) connected")

            # Additional device-specific attributes.
            if hasattr(device, "request_file"):
                device.request_file.connect(self.open_file_dialog)
            if hasattr(device, "spec_length"):
                self.spec_length = device.spec_length
            # Add device to device dictionary
            self.devices[name] = device

        # initial parameter values, retrieved from devices
        self.parameter_dic = defaultdict(lambda: defaultdict(dict))
        for device in self.devices.keys():
            self.parameter_dic[device] = self.devices[device].parameter_display_dict

        # construct device settings menu
        self.device_settings_menu = dict()
        self.device_setting_functions = dict()
        for device in self.devices.keys():
            qmenu = QtWidgets.QMenu(device)
            self.menu_device_settings.addMenu(qmenu)
            self.device_settings_menu[device] = qmenu
            if hasattr(self.devices[device], "device_setting_function"):
                for function in self.devices[device].device_setting_function.keys():
                    button_type = self.devices[device].device_setting_function[function][0]
                    if button_type == 'Action':
                        button = QtWidgets.QAction(function)
                        qmenu.addAction(button)
                        button.triggered.connect(self.devices[device].device_setting_function[function][1])
                        self.device_setting_functions[function] = button
                    elif button_type == 'Checkbox':
                        button = QtWidgets.QAction(function)
                        button.setCheckable(True)
                        button.setChecked(False)
                        qmenu.addAction(button)
                        self.device_setting_functions[function] = button
                        self.device_setting_functions[function].toggled.connect(partial(self.devices[device].device_setting_function[function][1], self.device_setting_functions[function].isChecked()))
                        # ATTENTION the toggle of checkboxes currently dont work properly.
                    else:
                        raise NotImplementedError

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
        self.parameters_treeWidget.setColumnCount(2)
        self.parameters_treeWidget.setHeaderLabels(["Name", "Value"])
        self.parameter_widgets = {}
        self.readonly_parameter = []
        self.writeonly_parameter = []
        for device in self.parameter_dic.keys():
            item = QtWidgets.QTreeWidgetItem([device.capitalize()])
            self.parameters_treeWidget.addTopLevelItem(item)
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
                self.parameters_treeWidget.setItemWidget(child, 0, name_widget)
                self.parameters_treeWidget.setItemWidget(child, 1, self.parameter_widgets[param])

        # load write parameters from previous session into devices
        for device in self.devices.keys():
            try:
                if device in self.config["session_parameters"]:
                    for param in self.devices[device].parameter_dict.keys():
                        if not param in self.readonly_parameter:
                            previous_value = self.config["session_parameters"][device][param]
                            self.devices[device].parameter_dict[param] = previous_value
                            self.parameter_widgets[param].setValue(previous_value)
            except:
                pass


        # start DataHandling
        self.DataHandling = DataHandling(self.parameter, self.spec_length)
        self.DataHandling.sendParameterarray.connect(self.ParameterPlot.set_data)
        self.DataHandling.sendSpectrum.connect(self.SpectrometerPlot.set_data)
        self.DataHandling.sendMaximum.connect(self.SpectrometerPlot.update_datareader)

        # start Updater to update device read parameters
        self.Updater = UpdateWorker(self.devices,self.readonly_parameter)
        self.Updater.new_parameter.connect(self.update_read_parameter)
        self.Updater.start()

        # set variables
        self.measurement_busy = False
        self.save_folder_path = r'C:/TEMP'
        #a default data folder is always required and it would be good to keep it seperated from the code.
        #can everyone simply create a C:/Data/test' path on their device? # Not sure how to handle different OS here.
        self.filename = r'C:/TEMP/test'
        self.ref_filename = r'C:/TEMP/ref'
        self.power_calib_array = []

        # set connect events
        self.test_pushButton.clicked.connect(self.test_button_clicked)
        self.acquire_pushButton.clicked.connect(self.acquire_measurement)
        self.view_pushButton.clicked.connect(self.view_measurement)
        self.run_pushButton.clicked.connect(self.run_measurement)
        self.stop_pushButton.clicked.connect(self.stop_measurement)
        self.filename_lineEdit.editingFinished.connect(self.change_filename)
        self.save_pushButton.clicked.connect(self.save_data)
        self.folder_pushButton.clicked.connect(self.change_folder)
        self.acquire_bg_pushButton.clicked.connect(self.background_measurement)
        self.select_bg_pushButton.clicked.connect(self.load_bg)
        self.bg_checkBox.stateChanged.connect(self.update_check_bg)
        self.ParameterPlot.send_idx_change.connect(self.DataHandling.change_send_idx)
        self.ParameterPlot.send_parameter_filename.connect(self.DataHandling.save_parameter)
        self.kinetic_lineEdit.editingFinished.connect(self.change_kinetic_interval)
        self.kinetic_run_pushButton.clicked.connect(self.kinetic_measurement)
        self.Tseries_lineEdit.editingFinished.connect(self.change_Tseries)
        self.Tseries_run_pushButton.clicked.connect(self.Tseries_measurement)
        self.Powerseries_run_pushButton.clicked.connect(self.Powerseries_measurement)
        self.chirp_scan_run_pushButton.clicked.connect(self.chirp_scan_measurement)
        self.compressor_scan_run_pushButton.clicked.connect(self.compressor_scan_measurement)
        self.BF_scan_run_pushButton.clicked.connect(self.BF_measurement)
        self.Tseries_run_button.clicked.connect(self.Tseries_measurement)
        
        # THz tab button connections
        self.thz_acquisition.clicked.connect(self.thz_acquisition_measurement)
        self.autocorrelation.clicked.connect(self.Autocorrelation_measurement)
        self.thz_clear.clicked.connect(self.THz_clear)
        self.THz_StartPos_DoubleSpinBox.valueChanged.connect(self.update_THzStartPos)
        self.THz_EndPos_DoubleSpinBox.valueChanged.connect(self.update_THzEndPos)
        self.THz_ScanSpeed_DoubleSpinBox.valueChanged.connect(self.update_THzScanSpeed)
        self.THz_ScanResolution_DoubleSpinBox.valueChanged.connect(self.update_THzScanResolution)
        self.THz_averaging_DoubleSpinBox.valueChanged.connect(self.update_THzAveraging)
        self.ContinuousScan_checkBox.stateChanged.connect(self.update_continuous_scan)
        self.THz_TimeConstant_DoubleSpinBox.valueChanged.connect(self.update_THzTimeConstant)
        self.THz_FilterOrder_DoubleSpinBox.valueChanged.connect(self.update_THzFilterOrder)

        # run some functions once to define default values
        self.change_filename()

        # set last User Input in comments section
        self.comments_textEdit.setPlainText(self.config["comment"])

        # show GUI, to be executed at the end of init.
        self.show()

    ##### General functions #####

    # Generic replacement to start any measurement defined in MeasurementClasses through a GUI button 
    # initialized in the "measurements" section below
    def start_measurement(self, cls, *args, extra_connections=None):
        """
        Starts a measurement, clears DataHandling and connects signals to slots
        - cls: Name of class stored in MeasurementClasses (str)
        - *args: Arguments to be passed to Measurement
        - extra_connections: Dictionary of connections
        """
        if self.measurement_busy: # check if measurement is in progress.
            # Some measurements (e.g. Acquire) can be executed even if busy
            print('Measurement not started, devices are busy')
            return
        else:
            self.measurement_busy = True
            self.DataHandling.clear_data()

        try:
            cls = load_class(f"{'measurements.MeasurementClasses'}.{cls}")
            self.measurement = cls(*args)

            # standard connections
            if hasattr(self.measurement, "sendProgress"):
                self.measurement.sendProgress.connect(self.set_progress)
            if hasattr(self.measurement, "sendSpectrum"):
                self.measurement.sendSpectrum.connect(self.DataHandling.concatenate_data)
            if hasattr(self.measurement, "sendParameter"):
                self.measurement.sendParameter.connect(self.change_parameter)

            # optional extra connections
            if extra_connections:
                for signal_name, slot in extra_connections.items():
                    if hasattr(self.measurement, signal_name):
                        getattr(self.measurement, signal_name).connect(slot)
            self.measurement.start()

        except Exception as e:
            print(f'Measurement not started, Exception: {e}')

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

    def test_button_clicked(self):
        # test function to test anything
        print('I am testing')
        print(self.device_setting_functions["correct_bg"].isChecked())

    def set_progress(self, progress):
        # set progress bar and define whether a measurement is running. When progess ne 100, no new measurement starts
        self.progressBar.setValue(int(progress))
        if progress == 100.:
            self.measurement_busy = False
            self.DataHandling.spec_length = self.spec_length #needed to reset DataHandling preallocation after measurements with large spectra

    def change_folder(self):
        # select folder to save data
        self.save_folder_path = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select data saving folder')
        print('Data folder: ' + str(self.save_folder_path))
        self.change_filename()

    def change_filename(self):
        # change filename to string of LineEdit
        self.filename = str(self.save_folder_path) + "/" + str(self.filename_lineEdit.text().strip('\n'))
        print('filename changed to: ' + str(self.filename))

    def save_data(self):
        # save data
        self.DataHandling.save_data(self.filename, self.comments_textEdit.toPlainText())

    def load_bg(self):
        # open background file and set as background
        BackgroundFile = QtWidgets.QFileDialog.getOpenFileName(self, 'Select background data')
        bg_path = BackgroundFile[0]
        bg = np.loadtxt(bg_path, delimiter=',')
        self.DataHandling.background = bg[-self.spec_length:, 1]
        # print(np.shape(bg[1:,1]))

        # display background filename
        idx = bg_path.rfind('/')
        self.bg_file_lineEdit.setText(bg_path[idx + 1:])

    def update_check_bg(self):
        self.DataHandling.correct_background = self.bg_checkBox.isChecked()

    def open_file_dialog(self):
        '''
        File dialog to pass filename to spectrometer
        Returns ref_filename to spectrometer worker.
        '''
        self.ref_filename, _ = QtWidgets.QFileDialog.getOpenFileName(self,"Select data")
        if hasattr(self.devices['spectrometer'], 'ref_filename'):
            self.devices['spectrometer'].ref_filename = self.ref_filename

    def get_ref_filename(self):
        return self.ref_filename

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
        # Single measurement
        # TO DO implement allow_when_busy condition
        self.start_measurement('AcquireMeasurement', self.devices, self.parameter)

    def view_measurement(self):
        # Continuous measurement
        self.start_measurement('ViewMeasurement', self.devices, self.parameter,
            extra_connections={"sendClear": self.SpectrometerPlot.clear_plot})

    def run_measurement(self):
        # Continous measurement with accumulation
        self.start_measurement('RunMeasurement', self.devices, self.parameter)

    def background_measurement(self):
        # Take background measurement, as needed for some spectrometers
        self.start_measurement('BackgroundMeasurement',self.devices, self.parameter,
            self.bg_scans_spinBox.value(), self.filename, self.comments_textEdit.toPlainText(),
            extra_connections={"sendSave": self.DataHandling.save_data})

    def BF_measurement(self):
        # performs 2D scan by moving the tau stage and acquiring a heliotis image (A_opt) for each tau
        self.start_measurement('BFMeasurement', self.devices, self.BF_scan_lineEdit.text(),
                               self.BF_axis_spinBox.value())

    def chirp_scan_measurement(self):
        # performs 2D scan by moving the tau stage and acquiring a heliotis image (A_opt) for each tau
        self.start_measurement('ChirpMeasurement',self.devices,self.chirp_scan_lineEdit.text(),
                               self.twoD_avg_spinBox.value())

    def compressor_scan_measurement(self):
        # performs 2D scan by moving the tau stage and acquiring a heliotis image (A_opt) for each tau
        self.start_measurement('CompressorMeasurement',self.devices,self.compressor_scan_lineEdit.text(),
                               self.twoD_avg_spinBox.value())

    def kinetic_measurement(self):
        # take time dependent measurement as defined in autmoation GUI section
        self.change_kinetic_interval()
        self.start_measurement('KineticMeasurement',self.devices, self.parameter, self.kinetic_interval)

    def Tseries_measurement(self):
        # take temperature dependent measurements as defined in automation GUI section
        self.start_measurement('TSeriesMeasurement',self.devices, self.parameter, self.Tseries,
            self.Tseries_stab_time_spinBox.value(), self.Tseries_two_sources_checkBox.isChecked(),
            self.Tseries_ref_power_doubleSpinBox.value(), self.Tseries_int_time_WL_doubleSpinBox.value(),
            self.Tseries_int_time_orpheus_doubleSpinBox.value(), self.Tseries_spectra_avg_spinBox.value(),
            self.Tseries_power_dep_checkBox.isChecked(), self.Tseries_filter_pos_lineEdit.text(),
            self.Tseries_int_time_lineEdit.text(),self.Tseries_sequence_checkBox.isChecked(),self.Tseries_sequence_lineEdit.text())

    def Powerseries_measurement(self):
        # take power dependent measurements as defined in automation GUI section
        self.start_measurement('PowerSeriesMeasurement',self.devices, self.parameter,
            self.Powerseries_filter_selection_spinBox.value(), self.Tseries_spectra_avg_spinBox.value(),
            self.Tseries_filter_pos_lineEdit.text())

    ### stopping functions ###
    def stop_measurement(self):
        # stop measurement
        self.measurement.stop()
        self.measurement_busy = False

    def closeEvent(self, event):
        for device in self.devices:
            if hasattr(self.devices[device], 'close_device'):
                self.devices[device].close_device()
            # store device write parameters for next restart
            self.config["session_parameters"] = {}
            for device in self.devices.keys(): #loop through all write parameters
                self.config["session_parameters"][device] = {}
                for param in self.devices[device].parameter_dict.keys():
                    if not param in self.readonly_parameter:
                        self.config["session_parameters"][device][param] = self.devices[device].parameter_dict[param]

        # Add/update the comment field
        self.config["comment"] = (self.comments_textEdit.toPlainText())
        # Write back to file
        with open(self.config_path, "w") as f:
            yaml.dump(self.config, f, sort_keys=False)

        # close Qt
        event.accept()

    def thz_acquisition_measurement(self):
        # Conducts a THz measurement using the translation stage and the lock in.
        if not self.measurement_busy:
            self.measurement_busy = True
            self.measurement = THzAcquisition(self.devices, self.thz_plot_widget)
            self.measurement.sendProgress.connect(self.set_progress)
            self.measurement.sendSpectrum.connect(self.DataHandling.concatenate_data)
            self.measurement.sendTargetPosition.connect(self.tstage.update_target_position)
            self.measurement.sendSpeed.connect(self.tstage.update_speed)
            self.measurement.sendWaitOnTarget.connect(self.tstage.wait_on_target)
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

    def update_THzStartPos(self, value):
        self.tstage.update_scan_initial_position(value)
        print('Placeholder for updating THz start position to:', value)

    def update_THzEndPos(self, value):
        self.tstage.update_scan_final_position(value)
        print('Placeholder for updating THz end position to:', value)

    def update_THzScanSpeed(self, value):
        self.tstage.update_speed(value)
        print('Placeholder for updating THz scan speed to:', value)

    def update_THzScanResolution(self, value):
        self.tstage.update_scan_resolution(value)
        print('Placeholder for updating THz scan resolution to:', value)

    def update_THzAveraging(self, value):
        self.lock_in.update_averaging(value)
        print('Placeholder for updating THz averaging to:', value)

    def update_continuous_scan(self, state):
        """Update the continuous scan state based on the checkbox state."""
        if state == QtCore.Qt.Checked:
            self.tstage.update_continuous_scan(True)
            print("Continuous scan enabled.")
        else:
            self.tstage.update_continuous_scan(False)
            print("Continuous scan disabled.")

    def update_THzTimeConstant(self, value):
        self.lock_in.update_time_constant(value)
        print('Placeholder for updating THz time constant to:', value)

    def update_THzFilterOrder(self, value):
        self.lock_in.update_filter_order(value)
        print('Placeholder for updating THz filter order to:', value)

    def THz_clear(self):
        self.thz_plot_widget.clear()

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

# Execute app
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainInterface()
    app.exec()
