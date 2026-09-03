"""
Measurement classes for different types of measurements. Each measurement creates a new thread that runs until the
measurement has finished or was requested to stop. Measurements can send signals to both the Main script as well to a
separate DataHandling script. At the beginning of each measurements, parameter are read from Main script and remain
until the measurement has finished.
"""

import time
import re
from PyQt5 import QtCore
import numpy as np
from pipython import pitools     # pipython helper used to wait until stage has reached its target position



# Measurement to acquire one spectrum
class AcquireMeasurement(QtCore.QThread):
    # set used signal types, destination is set in main script
    sendSpectrum = QtCore.pyqtSignal(np.ndarray, np.ndarray)
    sendProgress = QtCore.pyqtSignal(float)

    def __init__(self,devices, parameter):
        super(AcquireMeasurement, self).__init__()
        self.spectrometer = devices['spectrometer']
        self.wls = []  # preallocate wls array
        self.spec = []  # preallocate spec array
        self.terminate = False
        self.acquire_measurement = True

    def run(self):
        if not self.terminate:  # check whether stopping measurement is called
            self.sendProgress.emit(50)
            if hasattr(self.spectrometer, 'shutter'):
                self.spectrometer.start_acquisition()
            self.wls = np.array(self.spectrometer.get_wavelength())
            self.take_spectrum()
            print(time.strftime('%H:%M:%S') + ' Finished')
            if hasattr(self.spectrometer, 'shutter'):
                self.spectrometer.stop_acquisition()
            self.sendProgress.emit(100)

    def take_spectrum(self):
        self.spec = np.array(self.spectrometer.get_intensities())
        self.sendSpectrum.emit(self.wls, self.spec)

    def stop(self):
        self.terminate = True
        print(time.strftime('%H:%M:%S') + ' Request Stop')


# Measurement to continuously view spectra
class ViewMeasurement(QtCore.QThread):
    # set used signal types, destination is set in main script
    sendSpectrum = QtCore.pyqtSignal(np.ndarray, np.ndarray)
    sendProgress = QtCore.pyqtSignal(float)
    sendClear = QtCore.pyqtSignal()

    def __init__(self, devices, parameter):
        super(ViewMeasurement, self).__init__()
        self.spectrometer = devices['spectrometer']
        self.wls = []  # preallocate wls array
        self.spec = []  # preallocate spec array
        self.terminate = False

    def run(self):
        if hasattr(self.spectrometer, 'shutter'):
            self.spectrometer.start_acquisition()
        while not self.terminate:  # check whether stopping measurement is called
            t = time.time()
            self.sendProgress.emit(50)
            self.wls = np.array(self.spectrometer.get_wavelength())
            self.spec = np.array(self.spectrometer.get_intensities())
            self.sendClear.emit()
            self.sendSpectrum.emit(self.wls, self.spec)

            # limit too fast acquistion for computation
            if time.time() - t < 0.02:
                time.sleep(0.02)
        if hasattr(self.spectrometer, 'shutter'):
            self.spectrometer.stop_acquisition()
        # Finish measurement when loop is terminated
        print(time.strftime('%H:%M:%S') + ' Finished')
        self.sendProgress.emit(100)

    def stop(self):
        self.terminate = True
        print(time.strftime('%H:%M:%S') + ' Request Stop')


# Measurement to continuously acquire spectra and concatenate in DataHandling
class RunMeasurement(QtCore.QThread):
    # set used signal types, destination is set in main script
    sendSpectrum = QtCore.pyqtSignal(np.ndarray, np.ndarray)
    sendProgress = QtCore.pyqtSignal(float)

    def __init__(self, devices, parameter):
        super(RunMeasurement, self).__init__()
        self.spectrometer = devices['spectrometer']
        self.wls = []  # preallocate wls array
        self.spec = []  # preallocate spec array
        self.terminate = False
        print('emit start time ')

    def run(self):
        if hasattr(self.spectrometer, 'shutter'):
            self.spectrometer.start_acquisition()
        while not self.terminate:  # loop runs until requested stop
            t1 = time.time()
            self.wls = np.array(self.spectrometer.get_wavelength())
            self.spec = np.array(self.spectrometer.get_intensities())

            # send data
            self.sendSpectrum.emit(self.wls, self.spec)
            progress = 50
            self.sendProgress.emit(progress)

            # limit too fast acquistion for computation
            if time.time() - t1 < 0.02:
                time.sleep(0.02)
        if hasattr(self.spectrometer, 'shutter'):
            self.spectrometer.stop_acquisition()
        print(time.strftime('%H:%M:%S') + ' Finished')
        self.sendProgress.emit(100)
        return

    #  initiate controlled stop by enableing terminate statement, that is frequently queried in run code
    def stop(self):
        self.terminate = True
        print(time.strftime('%H:%M:%S') + 'Request Stop')


class BackgroundMeasurement(QtCore.QThread):
    # set used signal types, destination is set in main script
    sendSpectrum = QtCore.pyqtSignal(np.ndarray, np.ndarray)
    sendProgress = QtCore.pyqtSignal(float)
    sendSave = QtCore.pyqtSignal(str, str)

    def __init__(self, devices, parameter, scans, filename, comments):
        super(BackgroundMeasurement, self).__init__()
        self.spectrometer = devices['spectrometer']
        self.wls = []  # preallocate wls array
        self.spec = []  # preallocate spec array
        self.summedspec = []
        self.scans = scans
        self.filename = filename[:filename.rfind('/') + 1] + 'Background'
        print(filename[:filename.rfind('/') + 1] + 'Background')
        self.comments = comments
        self.terminate = False

    def run(self):
        if hasattr(self.spectrometer, 'shutter'):
            self.spectrometer.start_acquisition()
        if not self.terminate:  # check whether stopping measurement is called
            self.summedspec = np.array(self.spectrometer.get_intensities())
            for i in range(self.scans - 1):
                self.sendProgress.emit((i + 1) / self.scans * 100)
                self.wls = np.array(self.spectrometer.get_wavelength())
                self.spec = np.array(self.spectrometer.get_intensities())
                self.summedspec = self.summedspec + self.spec
            self.spec = self.summedspec / self.scans
            if hasattr(self.spectrometer, 'shutter'):
                self.spectrometer.stop_acquisition()
            self.sendSpectrum.emit(self.wls, self.spec)
            self.sendSave.emit(self.filename, self.comments)
            self.sendProgress.emit(100)
            print(time.strftime('%H:%M:%S') + 'Background acquired')

    def stop(self):
        self.terminate = True
        print(time.strftime('%H:%M:%S') + ' Request Stop')

# Measurement to acquire spectra according to a time array defined by the user. Shutter commands are enabled
class KineticMeasurement(QtCore.QThread):
    # set used signal types, destination is set in main script
    sendProgress = QtCore.pyqtSignal(float)
    sendParameter = QtCore.pyqtSignal(str, float)
    sendSpectrum = QtCore.pyqtSignal(np.ndarray, np.ndarray)

    def __init__(self, devices, parameter, kinetic_interval):
        super(KineticMeasurement, self).__init__()
        self.spectrometer = devices['spectrometer']
        #self.orpheus = devices['thorlabs_shutter']
        self.kinetic_interval = kinetic_interval
        self.wls = []
        self.spec = []
        self.terminate = False
        self.t_curr_step = 0
        self.t0 = 0
        try:  # extract max time of measurement series to calculate progress
            self.max_time = float(re.findall('[0-9]+[.]', kinetic_interval[-1])[0])
        except:
            try:
                self.max_time = float(re.findall('[0-9]+[.]', kinetic_interval[-2])[0])
            except:
                self.max_time = float(kinetic_interval[-1][0])

    def run(self):
        print(time.strftime('%H:%M:%S') + 'Run Kinetic Measurement')
        if hasattr(self.spectrometer, 'shutter'):
            self.spectrometer.start_acquisition()
        if not self.terminate:
            # get wls and start time
            self.wls = np.array(self.spectrometer.get_wavelength())
            self.t0 = time.time()

            # get commands from kinetic_interval
            for k in self.kinetic_interval:
                if not self.terminate:
                    # shutter command or waiting time
                    if isinstance(k, str):  # shutter command
                        if k == 'open':
                            print('open shutter')
                            self.sendParameter.emit('fast_shutter', 100)
                            wait = 0.05
                            time.sleep(wait)
                        elif k == 'close':
                            print('close shutter')
                            self.sendParameter.emit('fast_shutter', 0)
                            wait = 0.05
                            time.sleep(wait)

                        # open, acquire, close and wait
                        elif k[0] == 'p':
                            # set spectrometer in probe trigger mode
                            self.spectrometer.probe_trigger = True
                            self.t_curr_step = float(k[1:])
                            # wait
                            wait_time = self.t0 + float(k[1:]) - time.time()
                            if wait_time > 0:
                                time.sleep(wait_time)
                            else:
                                print('Waiting time before probe cycle negative:' + str(wait_time))
                            self.probe_cycle()
                            self.sendProgress.emit(float(k[1:]) / self.max_time * 100)

                    # acquire spectrum and wait
                    elif isinstance(k, np.ndarray):  # waiting command
                        for j in k:
                            if not self.terminate:
                                self.t_curr_step = j
                                self.spec = np.array(self.spectrometer.get_intensities())
                                self.sendSpectrum.emit(self.wls, self.spec)
                                self.sendProgress.emit(j / self.max_time * 100)
                                t3 = time.time()
                                wait_time = self.t0 + self.t_curr_step - t3

                                if wait_time > 0:
                                    time.sleep(wait_time)
                                else:
                                    print('Waiting time negative:' + str(wait_time))

                    else:
                        print('Unknown instance in kinetic interval')
        if hasattr(self.spectrometer, 'shutter'):
            self.spectrometer.stop_acquisition()
        self.sendProgress.emit(100)
        self.spectrometer.probe_trigger = False
        print(time.strftime('%H:%M:%S') + ' Finished')
        return

    # helper functions  self.sendSpectrum.emit(self.wls, self.spec)
    def probe_cycle(self):
        # open shutter
        t1 = time.time()
        self.sendParameter.emit('fast_shutter', 100)
        # acquire
        if not self.terminate:
            self.spec = np.array(self.spectrometer.get_intensities())
            # close shutter
            self.sendParameter.emit('fast_shutter', 0)
            self.sendSpectrum.emit(self.wls, self.spec)
            t2 = time.time()
            print('Open time: ' + str(t2 - t1))

            #  initiate controlled stop by enableing terminate statement, that is frequently queried in run code

    def stop(self):
        self.terminate = True
        print(time.strftime('%H:%M:%S') + ' Request Stop')


class TSeriesMeasurement(QtCore.QThread):
    sendSpectrum = QtCore.pyqtSignal(np.ndarray, np.ndarray)
    sendProgress = QtCore.pyqtSignal(float)
    sendParameter = QtCore.pyqtSignal(str, float)

    def __init__(self, devices, parameter, T_series, T_stab_time, two_sources, ref_power, int_time_WL, int_time_orpheus,
                 spectra_avg, power_dep, filter_pos, int_times):
        super(TSeriesMeasurement, self).__init__()
        self.Spectrometer = devices['spectrometer']
        self.cryostat = devices['cryostat']
        self.T_series = T_series
        self.T_stab_time = T_stab_time
        self.two_sources = two_sources
        self.ref_power = ref_power
        self.int_time_WL = int_time_WL
        self.int_time_orpheus = int_time_orpheus
        self.spectra_avg = spectra_avg
        self.wls = []
        self.spec = []
        self.terminate = False
        self.power_dep = power_dep
        self.filter_ard_pos = []
        self.filter_thor_pos = []
        self.int_times = []
        try:
            for s in re.split(',', filter_pos):
                self.filter_ard_pos = np.append(self.filter_ard_pos, int(s[1:]))
                self.filter_thor_pos = np.append(self.filter_thor_pos, int(s[0]))
            for s in re.split(',', int_times):
                self.int_times = np.append(self.int_times, int(s))
        except ValueError:
            print('WARNING: Assigning filter pos did not work')

    def run(self):
        print(time.strftime('%H:%M:%S') + ' Run T Series Measurement')
        if not self.terminate:
            self.sendProgress.emit(1)
            self.wls = np.array(self.Spectrometer.get_wavelength())
            n = 0
            for temperature in self.T_series:
                n = n + 1
                self.sendParameter.emit('set_T', temperature)

                # wait for temperature
                T_current = self.cryostat.parameter_dict['current_T']
                while not abs(T_current - temperature) < 0.5:
                    if not self.terminate:
                        T_current = self.cryostat.parameter_dict['current_T']
                        print(time.strftime('%H:%M:%S') + ' Waiting for Temperature')
                        time.sleep(5)
                    else:
                        break
                print(time.strftime('%H:%M:%S') + ' Temperature setpoint reached: ' + str(temperature) + ' K')
                print(time.strftime('%H:%M:%S') + ' Let stabilize')
                time.sleep(self.T_stab_time)

                # measure
                if not self.terminate:
                    if not self.two_sources:
                        self.Spectrometer.start_acquisition()
                        for m in range(self.spectra_avg):
                            self.spec = np.array(self.Spectrometer.get_intensities())
                            self.sendSpectrum.emit(self.wls, self.spec)
                            print(time.strftime('%H:%M:%S') + ' Spectrum acquired')
                        self.Spectrometer.stop_acquisition()

                        progress = n / len(self.T_series) * 100
                        self.sendProgress.emit(progress)

                    else:
                        if not self.power_dep:
                            #self.sendParameter.emit('int_time', self.int_time_orpheus)
                            #self.sendParameter.emit('shutter1', 100)  # open Orpheus shutter
                            time.sleep(2)
                            for m in range(self.spectra_avg):
                                self.Spectrometer.start_acquisition()
                                self.spec = np.array(self.Spectrometer.get_intensities())
                                self.sendSpectrum.emit(self.wls, self.spec)
                                self.Spectrometer.stop_acquisition()
                                print(time.strftime('%H:%M:%S') + ' PL Spectrum acquired')

                            #self.sendParameter.emit('int_time', self.int_time_WL)
                            #self.sendParameter.emit('shutter1', 0)  # close Orpheus shutter
                            #time.sleep(2)
                        else:
                            for k in range(len(self.int_times)):
                                if not self.terminate:
                                    #self.sendParameter.emit('int_time', self.int_times[k])
                                    # set intensity filter
                                    #self.sendParameter.emit('filter_wheel', self.filter_ard_pos[k])
                                    #self.sendParameter.emit('filter_pos', self.filter_thor_pos[k])
                                    # trigger spectrometer to settle to new int time
                                    self.Spectrometer.start_acquisition()
                                    if not self.int_time_orpheus == self.int_times[k]:
                                        print(time.strftime('%H:%M:%S') + ' Int time changed, trigger spectrometer and '
                                                                          'wait to stabilize changes')
                                        self.Spectrometer.get_intensities()
                                        time.sleep(2)
                                    self.int_time_orpheus = self.int_times[k]
                                    waittime = 1 + self.int_times[k] / 1000
                                    if waittime < 2:
                                        waittime = 2
                                    time.sleep(waittime)
                                    #self.sendParameter.emit('shutter1', 100)  # open Orpheus shutter
                                    #time.sleep(2)
                                    for m in range(self.spectra_avg):
                                        self.spec = np.array(self.Spectrometer.get_intensities())
                                        self.sendSpectrum.emit(self.wls, self.spec)
                                        print(time.strftime('%H:%M:%S') + ' PL Spectrum acquired')
                                    #self.sendParameter.emit('shutter1', 0)  # close Orpheus shutter
                                    #time.sleep(2)
                                    self.Spectrometer.stop_acquisition()
                            self.sendParameter.emit('int_time', self.int_time_WL)

                        #self.sendParameter.emit('shutter2', 100)  # open WL shutter
                        #time.sleep(2)
                        #self.sendParameter.emit('shutter1', 0)  # close Orpheus shutter again

                        self.Spectrometer.start_acquisition()
                        time.sleep(2)

                        for m in range(self.spectra_avg):
                            self.spec = np.array(self.Spectrometer.get_intensities())
                            self.sendSpectrum.emit(self.wls, self.spec)
                            print(time.strftime('%H:%M:%S') + ' WL Spectrum acquired')
                        self.Spectrometer.stop_acquisition()
                        progress = n / len(self.T_series) * 100
                        self.sendProgress.emit(progress)
                        #self.sendParameter.emit('shutter2', 0)  # close WL shutter
                        time.sleep(2)
                        if self.terminate:
                            self.sendProgress.emit(100)

        print(time.strftime('%H:%M:%S') + ' Finished')
        return

    def stop(self):
        self.terminate = True
        print(time.strftime('%H:%M:%S') + ' Request Stop')

# Measurement of coordinate translation stage scan and UHF data acquisition (like plotter in LabOne) for a back and forth scan of the stage
class THzAcquisition(QtCore.QThread):
    # Define used signals
    sendProgress = QtCore.pyqtSignal(float)
    sendSpectrum = QtCore.pyqtSignal(np.ndarray, np.ndarray)
    plotDataSignal = QtCore.pyqtSignal(np.ndarray, np.ndarray)

    def __init__(self, devices, plot_widget=None, burst_duration = 0.1, scan_type = 'Continuous'):
        super(THzAcquisition, self).__init__()

        # Store parameters
        self.tstage = devices['tstage']
        self.lock_in = devices['lock_in']
        self.initial_pos = self.tstage.parameter_dict['scan_initial_position']
        self.final_pos = self.tstage.parameter_dict['scan_final_position']
        self.scan_speed = self.tstage.parameter_dict['speed']
        self.averageing_nb = int(self.lock_in.parameter_dict['Averageing'])
        self.time_constant = self.lock_in.parameter_dict['time_constant']
        self.scan_resolution = self.tstage.parameter_dict['scan_resolution'] * 1e-3   # Conversion of the resolution from µm to mm
        self.spec_length = np.ceil((self.final_pos - self.initial_pos) / self.scan_resolution).astype(int)
        self.plot_widget = plot_widget
        self.scan_type = scan_type
        if self.scan_type == 'Continuous':
            self.burst_duration = (self.final_pos - self.initial_pos) / self.scan_speed
        if self.scan_type == 'Step':
            self.burst_duration = burst_duration
        
        # Connect the plotting signal to the measurement's plotting method
        self.plotDataSignal.connect(self.plot_data)

    # Function to acquire data from the lock-in while the delay stage is moving
    def Plotter_acquire(self, clockbase, sample_nodes, daq_module):
        self.is_running = True
        self.clockbase = clockbase

        daq_module.execute()
        start_time = time.time()

        while not daq_module.raw_module.finished():
            # Calculate scan progress
            if self.scan_type == 'Continuous':
                elapsed_time = time.time() - start_time
                scan_frac = (self.scan_number - 1) / self.averageing_nb
                progress = 100 * min(self.scan_number / self.averageing_nb, scan_frac + elapsed_time/(self.burst_duration * self.averageing_nb))
            if self.scan_type == 'Step':
                progress = 100 * self.scan_number * (self.acquisition_number+1) / (self.spec_length * self.averageing_nb)
            time.sleep(0.1)

            # Display scan progress
            self.sendProgress.emit(progress)
            
        # Read results and plot them
        data_sets = daq_module.read(raw=False, clk_rate=self.clockbase)    

        # Extract DAQResult objects (taking the first element [0] of the list)
        data_input1 = data_sets[sample_nodes[0]][0].value[0]
        data_input2 = data_sets[sample_nodes[1]][0].value[0]

        if self.scan_type == 'Continuous':
            # Substract the data coming from sample_node[0] from the data coming from sample_node[1] (individual inputs of the lock-in/the balanced detector)
            result = data_input2 # - data_input1  # - mean_1 is comented out because the presubstracted output of the balanced detector is used
        if self.scan_type == 'Step':
            # Avrage the data over the measurement window
            mean_input1 = np.mean(data_input1)
            mean_input2 = np.mean(data_input2)

            # Substract the data coming from sample_node[0] from the data coming from sample_node[1] (individual inputs of the lock-in/the balanced detector)
            result = mean_input2 # - mean_input1  # - mean_1 is comented out because the presubstracted output of the balanced detector is used
        return result

    def single_scan(self):
        # Initialize the scan
        print('Moving to initial position')
        self.tstage.pidevice.VEL(1, 10)                              # Set speed to a fast value (10 mm/s) for moving to the initial position        
        self.tstage.pidevice.MOV(1, self.initial_pos)                # Move the stage to the initial position
        pitools.waitontarget(self.tstage.pidevice, 1, timeout=10000) # Wait until the stage has reached the initial position
        self.tstage.pidevice.VEL(1, self.scan_speed)                 # Set speed to the desired scan value

        # Scanning
        print('Starting position reached, starting scan')
        clockbase, nodes, module = self.lock_in.DAQ_setup(self.burst_duration)  # Configure UHF for burst acquisition with the defined burst duration and sampling rate

        if self.scan_type == 'Continuous':
            self.tstage.pidevice.MOV(1, self.final_pos)        # Move the stage to the final position
            voltages = self.Plotter_acquire(clockbase, nodes, module) # Start UHF data acquisition during the scan
            positions = np.linspace(self.initial_pos, self.final_pos, len(voltages)) # Create a list of positions associated with the voltages

        if self.scan_type == 'Step':
            # Create target scan positions
            self.target_positions = np.linspace(self.initial_pos, self.final_pos, self.spec_length)

            # Initialize lists to store data
            positions = np.zeros(self.spec_length)
            voltages = np.zeros(self.spec_length)
            
            for i in range(self.spec_length):
                self.acquisition_number = i
                self.tstage.pidevice.MOV(1, self.target_positions[i])        # Move the stage to ith target position
                pitools.waitontarget(self.tstage.pidevice, 1, timeout=10000) # Wait until the stage has reached the ith target position
                time.sleep(self.time_constant * 4)                           # Wait for the filter of the lock-in to settle
                positions[i] = self.tstage.pidevice.qPOS(1)[1]     # Measure the exact position of the stage
                voltages[i] = self.Plotter_acquire(clockbase, nodes, module) # Start UHF data acquisition during the scan
        return positions, voltages
    
    def run(self):
        p_sets = []
        v_sets = []
        self.sendProgress.emit(0)
        for i in range(self.averageing_nb):
            self.scan_number = i + 1
            positions, voltages = self.single_scan()
            p_sets.append(positions)
            v_sets.append(voltages)
            print(len(positions))
            print(len(voltages))
        if self.averageing_nb == 1:
            self.plotDataSignal.emit(positions, voltages)
        else:
            t_mean =  np.mean(p_sets, axis=0, keepdims=True)
            X_mean =  np.mean(v_sets, axis=0, keepdims=True)
            self.plotDataSignal.emit(t_mean[0], X_mean[0])
        self.sendProgress.emit(100)

    def plot_data(self, pos, voltages):
        # Conversion of positions to time
        positions_m = pos * 1e-3  # Convert positions from mm to m
        absolute_time_delays = 2.0 * positions_m / 299792458 * 1e12 # Convert positions to time (ps) (factor of 2 accounts for round trip of light)
        time_array = absolute_time_delays - absolute_time_delays[0] # Move the start of the array to 0
        
        # Plot in the provided plot widget
        # self.plot_widget.clear()
        self.plot_widget.plot(time_array, voltages * 1e6, pen='b', linewidth=0.5, label='Vertical')
        self.plot_widget.setLabel('bottom', 'Time (ps)')
        self.plot_widget.setLabel('left', 'Amplitude R (µV)')
        self.plot_widget.addLegend()

        # Send the data to DataHandling for saving
        time_attribute = np.array([0, time_array[-1], len(pos)]) # Create time attribute to be saved in the H5 file. This will prevent overflowing the H5 attribute while allowing to reconstruct the time array from the attribute when loading the data in mdsam
        self.sendSpectrum.emit(time_attribute, voltages * 1e6)   # Send the data to DataHandling for saving
    
    def stop(self):
        self.terminate = True

class ScopeView(QtCore.QThread):
    # Define used signals
    sendProgress = QtCore.pyqtSignal(float)
    sendSpectrum = QtCore.pyqtSignal(np.ndarray, np.ndarray)
    clearPlot = QtCore.pyqtSignal()

    def __init__(self, devices):
        super(ScopeView, self).__init__()
        self.lock_in = devices['lock_in']
        self.terminate = False

    def run(self):
        self.sendProgress.emit(50)
        while not self.terminate:
            t, wave = self.lock_in.Scope_acquire() # Acquire scope data from UHF
            self.clearPlot.emit() # Clear previous plot
            self.sendSpectrum.emit(t, wave) # Send new data to plot
            time.sleep(0.01) # Small buffer time
            
    def stop(self):
        self.terminate = True
        print(time.strftime('%H:%M:%S') + ' Request Stop')
        self.sendProgress.emit(100)

class Autocorrelation(QtCore.QThread):
    """Performs a position scan of the PI863 stage and records averaged power
    readings from the Thorlabs PM400.  At each position a fixed number of power
    measurements are taken (points_per_pos), averaged, and stored.  The resulting average power
    vs. position data are emitted and plotted on the provided plot_widget.
    """

    # Define signals
    sendProgress = QtCore.pyqtSignal(float)
    sendSpectrum = QtCore.pyqtSignal(np.ndarray, np.ndarray)

    def __init__(self, devices, start_pos, stop_pos, interval, points_per_pos = 5, plot_widget=None):
        super(Autocorrelation, self).__init__()
        self.tstage = devices['tstage']
        self.powermeter = devices['powermeter']
        self.start_pos = start_pos
        self.stop_pos = stop_pos
        self.interval = interval
        self.points_per_pos = points_per_pos
        self.plot_widget = plot_widget
        self.terminate = False

    def run(self):
        # Create the position array for the scan
        step = self.interval if self.stop_pos >= self.start_pos else -abs(self.interval)
        positions = np.arange(self.start_pos, self.stop_pos + step / 2, step)
        # Initialize variables
        avg_data = []
        total = len(positions)

        # Measurement loop
        for idx, pos in enumerate(positions):
            if self.terminate:
                break

            # Move translation stage and wait for it to reach the target
            self.tstage.pidevice.MOV(1, pos)
            self._wait_for_target(pos, timeout=10.0)

            # Measure the power at current position multiple times
            samples = []
            for i in range(self.points_per_pos):
                try:
                    val = self.powermeter.pm.measure_power() * 1e9  # nW
                    samples.append(val)
                except Exception as e:
                    print(f"[Autocorrelation] Power meter read error at position {pos}, sample {i+1}: {type(e).__name__}: {e}")
                    # Use last known value (or zero if no samples yet)
                    if samples:
                        val = samples[-1]
                    else:
                        val = self.powermeter.parameter_dict.get('current_power', 0)
                    samples.append(val)
                time.sleep(0.05)

            # Average the power data points for the current position
            avg = np.mean(samples) if samples else 0
            avg_data.append(avg)

            # update progress
            self.sendProgress.emit((idx + 1) / total * 100)

        # Store the positions and averaged data in numpy arrays for plotting
        self.positions = np.array(positions[: len(avg_data)])
        self.data = np.array(avg_data)
        self.data = self.data - np.min(self.data)

        # Convert positions (mm) to relative time delays (ps) using speed of light
        c = 299792458
        positions_m = self.positions * 1e-3
        self.times = 2.0 * positions_m / c * 1e12 # factor of 2 accounts for round trip of light
        # send time array and corresponding averaged data (GUI thread will handle plotting)
        self.sendSpectrum.emit(self.times, self.data)
        self.sendProgress.emit(100)

        # Find indices where signal crosses half max
        try:
            half_max = np.max(self.data) / 2
            above = self.data >= half_max
            crosses = np.where(np.diff(above.astype(int)) != 0)[0]
            up_crossing = crosses[0]
            down_crossing = crosses[-1] + 1
            
            # Interpolate to find accurate crossing points for FWHM calculation and calculate FWHM
            interp_begining_FWHM = self.times[up_crossing] + (half_max - self.data[up_crossing]) * (self.times[up_crossing+1] - self.times[up_crossing]) / (self.data[up_crossing+1] - self.data[up_crossing])
            interp_end_FWHM = self.times[down_crossing-1] + (half_max - self.data[down_crossing-1]) * (self.times[down_crossing] - self.times[down_crossing-1]) / (self.data[down_crossing] - self.data[down_crossing-1])
            FWHM = interp_end_FWHM - interp_begining_FWHM
            print(f"FWHM: {FWHM*1e3:.5g} fs")
        except Exception as e:
            print(f"[Autocorrelation] Error occurred while finding FWHM: {type(e).__name__}: {e}")
            return

    def stop(self):
        """Signal the running scan to terminate gracefully."""
        self.terminate = True
        print(time.strftime('%H:%M:%S') + ' Request Stop')
    
    def _wait_for_target(self, target_pos, timeout=10.0, tolerance=0.01):
        """Wait for the stage to reach the target position within tolerance."""
        import time
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            current_pos = self.tstage.pidevice.qPOS(1)[1]  # Get current position
            if abs(current_pos - target_pos) < tolerance:
                return True  # Target reached
            time.sleep(0.01)  # Small delay to avoid busy waiting
        
        print(f"Warning: Stage did not reach target position {target_pos} within {timeout} seconds")
        return False