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

        # Link the spectrometer to a monochromator when the setup provides both (PixisDecoupled,
        # Stresing). Done after the loop above so it doesn't depend on the order devices are listed
        # in config.yaml. Spectrometers without attach_to_monochromator (ThorlabsCCS200, Heliotis,
        # OceanSpectrometer, the original Pixis) are left untouched.
        spectrometer = self.devices.get('spectrometer')
        monochromator = self.devices.get('monochromator')
        if monochromator and spectrometer is not None and hasattr(spectrometer, 'attach_to_monochromator'):
            spectrometer.attach_to_monochromator(monochromator)
            print(f"spectrometer: attached to monochromator ({monochromator.name})")

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

        """ Grating selector for the monochromator, as a labelled dropdown instead of the bare
        numeric spinbox the generic parameter tree would otherwise show. Only built when a
        monochromator device is present AND exposes grating_densities -- setups without a
        monochromator (most existing experiments) or with a different monochromator driver that
        doesn't expose this attribute get no dropdown and no change in behaviour: the tree below
        falls back to showing 'grating' the same way it shows every other parameter. """
        self.grating_combo = None
        monochromator = self.devices.get('monochromator')
        if monochromator is not None and hasattr(monochromator, 'grating_densities'):
            self.grating_combo = QtWidgets.QComboBox()
            blazes = getattr(monochromator, 'grating_blazes', None)
            for index, density in enumerate(monochromator.grating_densities, start=1):
                # Density alone doesn't always disambiguate: two gratings on the same turret can
                # share a groove density and differ only by blaze wavelength.
                if blazes is not None and len(blazes) >= index:
                    label = f'{index}  ({density:.0f} g/mm, blaze {blazes[index - 1]:.0f} nm)'
                else:
                    label = f'{index}  ({density:.0f} g/mm)'
                self.grating_combo.addItem(label, index)
            current = int(round(getattr(monochromator, 'grating', 1)))
            position = self.grating_combo.findData(current)
            if position >= 0:
                self.grating_combo.setCurrentIndex(position)
            self.grating_combo.currentIndexChanged.connect(self.change_grating)

        # add items to GUI
        self.SpectrometerPlot = SpectrometerPlot()
        vbox = QtWidgets.QVBoxLayout()
        vbox.addWidget(self.SpectrometerPlot)
        self.spectro_tab.setLayout(vbox)
        self.ParameterPlot = ParameterPlot(self.parameter_dic)
        vbox = QtWidgets.QVBoxLayout()
        vbox.addWidget(self.ParameterPlot)
        self.parameter_tab.setLayout(vbox)

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
                # 'grating' gets the labelled dropdown built above instead of a bare spinbox, when
                # that dropdown exists. Placed directly in its normal tree row (under Monochromator)
                # rather than elsewhere in the GUI, so it reads like every other hardware parameter.
                if device == 'monochromator' and param == 'grating' and self.grating_combo is not None:
                    self.parameters_treeWidget.setItemWidget(child, 0, name_widget)
                    self.parameters_treeWidget.setItemWidget(child, 1, self.grating_combo)
                    continue
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
                            # 'grating' has no tree widget when the dropdown owns it (see above) --
                            # skip rather than raise, so restoring the rest of this device's
                            # parameters (e.g. central_wave, mirror) still runs to completion.
                            if param in self.parameter_widgets:
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

            if hasattr(self.measurement, 'spec_length'):
                # DataHandling's buffers were just preallocated (clear_data() above) for the
                # device's default spec_length. A measurement whose output is a different length
                # needs DataHandling resized to match before any data arrives, or
                # concatenate_data's np.c_[self.spec, spec] raises on the shape mismatch. Reset
                # back to the device default in set_progress() once it reaches 100%.
                self.DataHandling.resize_spec_length(self.measurement.spec_length)
                self.DataHandling.clear_data()

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

            """ Safety net: QThread.finished always fires when run() returns, whether it completed
            normally or ended via an uncaught exception (e.g. a driver's TimeoutError). The normal
            path already resets measurement_busy/DataHandling via set_progress(100); this catches
            every case where run() ends without ever reaching that -- which otherwise left
            measurement_busy stuck at True, rejecting every later measurement as "devices are busy"
            until the app was restarted, since a QThread's own exceptions aren't visible to the
            try/except below (that only wraps construction and the non-blocking call to .start()). """
            self.measurement.finished.connect(self.on_measurement_finished)
            self.measurement.start()

        except Exception as e:
            # Without this, a measurement that fails during construction (e.g. a missing driver
            # module) leaves measurement_busy stuck at True forever, since it's normally only
            # cleared by set_progress() reaching 100% -- which a measurement that never started
            # will never send. Every later start_measurement() call would then be rejected with
            # "devices are busy" until the app was restarted.
            self.measurement_busy = False
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

    def change_grating(self, index):
        """ Slot for the grating dropdown built in __init__ (only exists when the monochromator
        exposes grating_densities). Mirrors set_parameter's device lookup / DataHandling update,
        since 'grating' is excluded from the generic parameter tree that set_parameter reads from. """
        value = self.grating_combo.itemData(index)
        if value is None:
            return
        monochromator = self.devices.get('monochromator')
        if monochromator is not None:
            monochromator.set_parameter('grating', value)
            self.parameter['grating'] = value

    def test_button_clicked(self):
        # test function to test anything
        print('I am testing')
        print(self.device_setting_functions["correct_bg"].isChecked())

    def set_progress(self, progress):
        # set progress bar and define whether a measurement is running. When progess ne 100, no new measurement starts
        self.progressBar.setValue(int(progress))
        if progress == 100.:
            self.measurement_busy = False
            # Resets DataHandling's buffer size back to the device default after measurements
            # with large/variable-length spectra (see start_measurement()). This previously
            # assigned DataHandling.spec_length, an attribute DataHandling never reads (it uses
            # .speclength), so the reset was silently a no-op.
            self.DataHandling.resize_spec_length(self.spec_length)

    def on_measurement_finished(self):
        """ Safety-net slot for QThread.finished (see start_measurement()). Redundant with
        set_progress(100) on the normal completion path -- both just end up setting the same two
        things -- but it's the only one of the two that also runs when a measurement's run() raises
        before ever emitting sendProgress(100). """
        self.measurement_busy = False
        self.DataHandling.resize_spec_length(self.spec_length)

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
        # self.measurement is only set once construction in start_measurement() succeeds, so a stop
        # requested when no measurement ever started (or the last one failed) has nothing to stop.
        if hasattr(self, 'measurement'):
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
