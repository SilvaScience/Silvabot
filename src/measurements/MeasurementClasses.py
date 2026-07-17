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

import h5py
import os
from jki_python_bridge_for_labview import labview as lv


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
        print(time.strftime('%H:%M:%S') + 'Run started')

    def run(self):
        self.sendProgress.emit(0)
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
        self.spectrometer = devices['spectrometer']
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

            # initialize T dependent measurement
            self.sendProgress.emit(1)
            self.wls = np.array(self.spectrometer.get_wavelength())
            n = 0

            # loop over temperatures
            for temperature in self.T_series:
                n = n + 1
                self.sendParameter.emit('set_T', temperature)

                # wait to reach temperature
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
                    if not self.two_sources: # case of one single source
                        if hasattr(self.spectrometer, 'shutter'):
                            self.spectrometer.start_acquisition()
                        for m in range(self.spectra_avg): # take several spectra for each acquistion
                            self.spec = np.array(self.spectrometer.get_intensities())
                            self.sendSpectrum.emit(self.wls, self.spec)
                            print(time.strftime('%H:%M:%S') + ' Spectrum acquired')
                        if hasattr(self.spectrometer, 'shutter'):
                            self.spectrometer.stop_acquisition()

                        progress = n / len(self.T_series) * 100
                        self.sendProgress.emit(progress)

                    else: # case of two sources (Orpheus and WL)
                        if not self.power_dep: # power INdependent case
                            self.sendParameter.emit('int_time', self.int_time_orpheus)
                            self.sendParameter.emit('shutter', 100)  # open Orpheus shutter
                            time.sleep(2)
                            for m in range(self.spectra_avg):
                                if hasattr(self.spectrometer, 'shutter'):
                                    self.spectrometer.start_acquisition()
                                self.spec = np.array(self.spectrometer.get_intensities())
                                self.sendSpectrum.emit(self.wls, self.spec)
                                if hasattr(self.spectrometer, 'shutter'):
                                    self.spectrometer.stop_acquisition()
                                print(time.strftime('%H:%M:%S') + ' PL Spectrum acquired')

                            self.sendParameter.emit('int_time', self.int_time_WL)
                            self.sendParameter.emit('shutter', 0)  # close Orpheus shutter
                            time.sleep(2)
                        else: # power dependent case, currently NOT IMPLEMENTED (filter wheel missing)
                            for k in range(len(self.int_times)):
                                if not self.terminate:
                                    #self.sendParameter.emit('int_time', self.int_times[k])
                                    # set intensity filter
                                    #self.sendParameter.emit('filter_wheel', self.filter_ard_pos[k])
                                    #self.sendParameter.emit('filter_pos', self.filter_thor_pos[k])
                                    # trigger spectrometer to settle to new int time
                                    if hasattr(self.spectrometer, 'shutter'):
                                        self.spectrometer.start_acquisition()
                                    if not self.int_time_orpheus == self.int_times[k]:
                                        print(time.strftime('%H:%M:%S') + ' Int time changed, trigger spectrometer and '
                                                                          'wait to stabilize changes')
                                        self.spectrometer.get_intensities()
                                        time.sleep(2)
                                    self.int_time_orpheus = self.int_times[k]
                                    waittime = 1 + self.int_times[k] / 1000
                                    if waittime < 2:
                                        waittime = 2
                                    time.sleep(waittime)
                                    #self.sendParameter.emit('shutter1', 100)  # open Orpheus shutter
                                    #time.sleep(2)
                                    for m in range(self.spectra_avg):
                                        self.spec = np.array(self.spectrometer.get_intensities())
                                        self.sendSpectrum.emit(self.wls, self.spec)
                                        print(time.strftime('%H:%M:%S') + ' PL Spectrum acquired')
                                    #self.sendParameter.emit('shutter1', 0)  # close Orpheus shutter
                                    #time.sleep(2)
                                    if hasattr(self.spectrometer, 'shutter'):
                                        self.spectrometer.stop_acquisition()
                            self.sendParameter.emit('int_time', self.int_time_WL)

                        # take WL measurements
                        self.sendParameter.emit('filter_wheel_1', 0)  # open WL shutter
                        time.sleep(2)
                        self.sendParameter.emit('shutter', 0)  # close Orpheus shutter again

                        if hasattr(self.spectrometer, 'shutter'):
                            self.spectrometer.start_acquisition()
                        for m in range(self.spectra_avg): # take several WL measurements
                            self.spec = np.array(self.spectrometer.get_intensities())
                            self.sendSpectrum.emit(self.wls, self.spec)
                            print(time.strftime('%H:%M:%S') + ' WL Spectrum acquired')
                        if hasattr(self.spectrometer, 'shutter'):
                            self.spectrometer.stop_acquisition()
                        progress = n / len(self.T_series) * 100
                        self.sendProgress.emit(progress)
                        self.sendParameter.emit('filter_wheel_1', 100)  # close WL shutter
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

    def __init__(self, devices, plot_widget=None, burst_duration=0.1):
        super(THzAcquisition, self).__init__()

        # Store parameters
        self.tstage = devices['tstage']
        self.lock_in = devices['lock_in']
        self.initial_pos = self.tstage.parameter_dict['scan_initial_position']
        self.final_pos = self.tstage.parameter_dict['scan_final_position']
        self.scan_speed = self.tstage.parameter_dict['speed']
        self.burst_duration = burst_duration
        self.plot_widget = plot_widget
        
        # Calculate number of samples in a scan = spec_length
        self.total_time = abs(self.final_pos - self.initial_pos) / self.scan_speed # Calculated total scan time
        # self.samp_rate = devices['lock_in'].parameter_dict['sampling_rate']        # Get sampling rate from UHF parameters
        self.samp_rate = self.lock_in.device.demods[0].rate()                           # Get sampling rate from the UHF
        self.num_bursts = int(np.ceil(self.total_time / self.burst_duration) + 1)       # Calculated number of bursts to cover the scan time
        self.num_samp_per_burst = int(np.ceil(self.burst_duration * self.samp_rate))    # Calculate number of samples per burst
        self.spec_length = self.num_bursts * self.num_samp_per_burst                    # Calculate the total number of samples in a scan
        
        # Connect the plotting signal to the measurement's plotting method
        self.plotDataSignal.connect(self.plot_data)

    # Function to acquire data from the lock-in while the delay stage is moving
    def Plotter_acquire(self, clockbase, sample_nodes, daq_module):
        self.is_running = True
        self.clockbase = clockbase
        
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

        # Start data acquisition in bursts until stopped
        ts0 = np.nan                             # Initialize initial timestamp
        results = {x: [] for x in sample_nodes}  # Initialize results dictionary
        daq_module.execute()                     # Start the DAQ module
        
        # While loop to continuously read data until the stop condition is met (scan time exceeded or stop requested)
        scan_start_time = None
        burst_counter = 0
        while True:
            burst_counter += 1                                  # Increment burst counter
            results, ts0 = read_data(daq_module, results, ts0)  # Read data and update results
            if scan_start_time is None and len(results[sample_nodes[1]]) > 0:  # Set the scan start time based on the timestamp of the first burst received from Demod 4
                # Set start time from first burst timestamp
                first_burst = results[sample_nodes[1]][0]                      
                scan_start_time = first_burst.header['createdtimestamp'][0] / self.clockbase
            
            progress = min(burst_counter / self.num_bursts, 1.0) * 100
            self.sendProgress.emit(progress)
            
            if scan_start_time is not None:
                elapsed_time = (results[sample_nodes[1]][-1].header['createdtimestamp'][0] / self.clockbase) - scan_start_time
                if elapsed_time >= self.total_time:
                    break

            time.sleep(self.burst_duration)
        
        # Stop the DAQ module and do a final read to get any remaining data
        daq_module.finish()                                     # Stop the DAQ module
        results, ts0 = read_data(daq_module, results, ts0)      # Final read to get any remaining data

        # Organize the acquired data and calculate the difference between the two demodulators
        d0_bursts = results[sample_nodes[0]]                                                                            # Get bursts for Demod 0
        r0 = np.concatenate([b.value.flatten() for b in d0_bursts])                                                     # Concatenate R values for Demod 0
        t0 = np.concatenate([(b.time + (b.header['createdtimestamp'][0] / self.clockbase) - ts0) for b in d0_bursts])   # Concatenate time values for Demod 0
        d4_bursts = results[sample_nodes[1]]                                                                            # Get bursts for Demod 4
        r4 = np.concatenate([b.value.flatten() for b in d4_bursts])                                                     # Concatenate R values for Demod 4
        t4 = np.concatenate([(b.time + (b.header['createdtimestamp'][0] / self.clockbase) - ts0) for b in d4_bursts])   # Concatenate time values for Demod 4
        R_diff = r4 #- r0

        return t0, R_diff
    
    def run(self):
        self.tstage.pidevice.VEL(1, 10)                              # Set speed to a fast value (10 mm/s) for moving to the initial position
        self.tstage.pidevice.VEL(1, 10)                              # Set speed to a fast value (10 mm/s) for moving to the initial position        
        self.tstage.pidevice.MOV(1, self.initial_pos)                # Moves the stage to the initial position
        pitools.waitontarget(self.tstage.pidevice, 1, timeout=10000) # Wait until the stage has reached the initial position
        self.tstage.pidevice.VEL(1, self.scan_speed)                 # Set the speed for scanning to the value from the parameter dict
        clockbase, nodes, module = self.lock_in.DAQ_setup(self.total_time, self.burst_duration, self.num_bursts)  # Configure UHF for burst acquisition with the defined burst duration and sampling rate
        self.tstage.pidevice.MOV(1, self.final_pos)                  # Start the stage moving to its maximum position
        t, X = self.Plotter_acquire(clockbase, nodes, module)        # Start UHF data acquisition during the scan
        self.plotDataSignal.emit(t, X)                               # Plot the data
        self.sendProgress.emit(100)                                  # Emit 100% progress when done
    
    def plot_data(self, t, X):
        # Convert scan time to delay time between the pulses
        dist_traveled = abs(self.final_pos - self.initial_pos) * 1e-3
        dist_to_time = 2 * dist_traveled / 299792458 * 1e12
        time_array = np.linspace(0, dist_to_time, len(t))
        
        # Plot in the provided plot widget
        self.plot_widget.clear()
        self.plot_widget.plot(time_array, X * 1e6, pen='b', linewidth=0.5, label='Vertical')
        self.plot_widget.setLabel('bottom', 'Time (ps)')
        self.plot_widget.setLabel('left', 'Amplitude R (µV)')
        self.plot_widget.addLegend()

        # Send the data to DataHandling for saving
        time_attribute = np.array([0, dist_to_time, len(t)])  # Create time attribute to be saved in the H5 file. This will prevent overflowing the H5 attribute while allowing to reconstruct the time array from the attribute when loading the data in mdsam
        self.sendSpectrum.emit(time_attribute, X * 1e6)       # Send the data to DataHandling for saving
    
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

        
class AcquireSpectrum(QtCore.QThread):
    # set used signal types, destination is set in main script
    sendSpectrum = QtCore.pyqtSignal(np.ndarray, np.ndarray)
    sendProgress = QtCore.pyqtSignal(float)
    sendParameter = QtCore.pyqtSignal(str, float)

    def __init__(self, devices, parameter, start_wl, stop_wl):
        super(AcquireSpectrum, self).__init__()
        self.spectrometer = devices['spectrometer']
        self.wls = np.array([])  # preallocate wls array
        self.spec = np.empty((252, 0)) # preallocate spec array
        self.terminate = False
        self.acquire_measurement = True
        self.start_wl = start_wl
        self.end_wl = stop_wl
        self.nb_of_spectra = int(np.ceil((self.end_wl - self.start_wl) / 50) + 1)       # Overestimates the number of individual spectra needed to cover the desired wl range (the 50 comes from the fact that 50 nm is around 200 points and the from each spectra 200 points are kept for the stitching / the + 1 ensures that the full wl range is included in the measurement)
        self.spec_length = (self.spectrometer.spec_length[0], 200 * self.nb_of_spectra) # Definition of the spec_length of the stitched spectrum that will be sent to DataHandling (200 is the number of points for each individual spectra that is kept when stitching them together)

    def run(self):
        print(self.spectrometer.parameter_dict['start_wl'])
        if not self.terminate:
            self.sendProgress.emit(50)
            nb_iter = 0
            while nb_iter < self.nb_of_spectra:
                # move grating to select wavelength range
                if nb_iter == 0:                         # First iteration of the while loop
                    center_wl = self.start_wl + 25       # Adjust the center wl 25 nm after the starting wavelength position
                else:                                    # Subsequent iterations of the while loop
                    center_wl = self.wls[-1] + 25        # Adjust the center wl 25 nm after the starting wavelength position

                self.sendParameter.emit('center_wl', center_wl)    # Send signal to move the grating
                time.sleep(5)                                      # Wait to ensure the grating is in position before taking the next spectra

                # acquire spectrum
                if hasattr(self.spectrometer, 'shutter'):
                    self.spectrometer.start_acquisition()
                new_wls = np.array(self.spectrometer.get_wavelength())    # Get wavelength range of the spectrometer for the new grating position
                new_spec = np.array(self.spectrometer.get_intensities())  # Get the spectrum for the new grating position
                mid_idx = len(new_wls) // 2 # Find the index of the middle of the wavelength range
                self.wls = np.concatenate((self.wls, new_wls[mid_idx-100:mid_idx+100]), axis=0)   # Concatenate the center 200 points of the new wavelengths to the self.wls array
                self.spec = np.concatenate((self.spec, new_spec[:, mid_idx-100:mid_idx+100]), axis = 1)  # Concatenate the center 200 points of the new spectrum to the self.spec array
                if hasattr(self.spectrometer, 'shutter'):
                    self.spectrometer.stop_acquisition()

                # Add 1 to the iteration counter
                nb_iter += 1

            # Send signals to DataHandling
            self.sendSpectrum.emit(np.array(self.wls), np.array(self.spec))
            self.sendProgress.emit(100)

class PowerSeriesMeasurement(QtCore.QThread):
    sendSpectrum = QtCore.pyqtSignal(np.ndarray, np.ndarray)
    sendProgress = QtCore.pyqtSignal(float)
    sendParameter = QtCore.pyqtSignal(str, float)

    def __init__(self, devices, parameter, filter_select,spectra_avg, filter_pos):
        super(PowerSeriesMeasurement, self).__init__()
        self.spectrometer = devices['spectrometer']
        self.cryostat = devices['cryostat']
        self.terminate = False
        self.spectra_avg = spectra_avg
        if filter_select == 1:
            self.filter_wheel = 'filter_wheel_1'
        elif filter_select == 2:
            self.filter_wheel = 'filter_wheel_2'
        elif filter_select == 3:
            self.filter_wheel = 'filter_wheel_3'
        else:
            print('WARNING. Filter wheel selection not valid')
        self.filter_ard_pos = []
        try:
            for s in re.split(',', filter_pos):
                self.filter_ard_pos = np.append(self.filter_ard_pos, int(s))
        except ValueError:
            print('WARNING: Assigning filter pos did not work')

    def run(self):
        print(time.strftime('%H:%M:%S') + ' Run Power Series Measurement')
        if not self.terminate:

            # initialize power dependent measurement
            self.sendProgress.emit(1)
            self.wls = np.array(self.spectrometer.get_wavelength())
            n = 0

            # loop over filter positions
            for filter_pos in self.filter_ard_pos:
                n = n + 1
                if not self.terminate:
                    self.sendParameter.emit(self.filter_wheel, filter_pos)
                    print(time.strftime('%H:%M:%S') + f' Filter set to {filter_pos} degrees')
                    time.sleep(2)

                    # measure
                    if hasattr(self.spectrometer, 'shutter'):
                        self.spectrometer.start_acquisition()
                    for m in range(self.spectra_avg):  # take several spectra for each acquistion
                        if not self.terminate:
                            spec = np.array(self.spectrometer.get_intensities())
                            self.sendSpectrum.emit(self.wls, spec)
                    if hasattr(self.spectrometer, 'shutter'):
                        self.spectrometer.stop_acquisition()

                    # send progress
                    progress = n / len(self.filter_ard_pos) * 100
                    self.sendProgress.emit(progress)

             # Return to initial filter pos
            self.sendParameter.emit(self.filter_wheel, self.filter_ard_pos[0])

            # Indicate that measurement is finished
            self.sendProgress.emit(100)
            print(time.strftime('%H:%M:%S') + ' Finished')
        return

    def stop(self):
        self.terminate = True
        print(time.strftime('%H:%M:%S') + ' Request Stop')


class TwoDMeasurement(QtCore.QThread):
    sendSpectrum = QtCore.pyqtSignal(np.ndarray, np.ndarray)  # Final averaged image (e.g., A_opt)
    sendProgress = QtCore.pyqtSignal(float)
    sendSave = QtCore.pyqtSignal(str, str)
    sendParameter = QtCore.pyqtSignal(str, float)

    def __init__(self, devices, tau_max_value, tau_step_value,twoD_step_start_value,avg_value):
        super(TwoDMeasurement, self).__init__()
        self.spectrometer = devices['spectrometer']
        self.Bigfoot = devices['bigfoot']
        self.wls = []  # preallocate wls array
        self.spec = []  # preallocate spec array
        lv.connect()
        step = tau_step_value #lv.LV_Control.read_scan_params()[1] #### can be changed if needed, or added with a button in the interface
        self.tau_array =  np.arange(twoD_step_start_value, tau_max_value + step, step)
        self.avg_value = avg_value
        print('Measure 2D map with following tau array:', self.tau_array)
        self.terminate = False

    def run(self):
        self.wls = np.array(self.spectrometer.get_wavelength())
        for i,tau_value in enumerate(self.tau_array):
            if not self.terminate:  # check whether stopping measurement is called
                self.sendProgress.emit(i/len(self.tau_array)*100)
                print(time.strftime('%H:%M:%S') + f' Move tau stage to tau= {tau_value} fs')
                self.sendParameter.emit('tau', tau_value)
                bigfoot_busy = True
                time.sleep(0.1)
                while bigfoot_busy: # check for movement of tau stage.
                    bigfoot_busy = self.Bigfoot.check_stage()
                    print(time.strftime('%H:%M:%S') + f' tau stage moving. Status: {bigfoot_busy}')
                    time.sleep(0.1)
                for j in range(self.avg_value):
                    self.spec = np.array(self.spectrometer.get_intensities())
                    self.sendSpectrum.emit(self.wls, self.spec)
                    print(time.strftime('%H:%M:%S') + f' Spectrum acquired for tau= {tau_value} fs')

        self.sendProgress.emit(100)
        print(time.strftime('%H:%M:%S') + ' Finished')
        return

    def stop(self):
        self.terminate = True
        print(time.strftime('%H:%M:%S') + ' Request Stop')


class ChirpMeasurement(QtCore.QThread):
    sendSpectrum = QtCore.pyqtSignal(np.ndarray, np.ndarray)  # Final averaged image (e.g., A_opt)
    sendProgress = QtCore.pyqtSignal(float)
    sendSave = QtCore.pyqtSignal(str, str)
    sendParameter = QtCore.pyqtSignal(str, float)

    def __init__(self, devices, chirp_scan_lineEdit,avg_value):
        super(ChirpMeasurement, self).__init__()
        self.spectrometer = devices['spectrometer']
        self.Bigfoot = devices['bigfoot']
        self.wls = []  # preallocate wls array
        self.spec = []  # preallocate spec array
        line_components = [float(x) for x in re.split(':', chirp_scan_lineEdit)]
        self.scmp_array =  np.arange(line_components[0], line_components[2] + line_components[1], line_components[1])
        self.avg_value = avg_value
        print('Measure chirp scan with following SCMP positions:', self.scmp_array)
        self.terminate = False

    def run(self):
        self.wls = np.array(self.spectrometer.get_wavelength())
        for i,scmp_value in enumerate(self.scmp_array):
            if not self.terminate:  # check whether stopping measurement is called
                self.sendProgress.emit(i/len(self.scmp_array)*100)
                print(time.strftime('%H:%M:%S') + f' Move SCMP to {scmp_value} um')
                self.sendParameter.emit('scmp', scmp_value)
                time.sleep(0.5) # no feedback on when SCMP is set.
                for j in range(self.avg_value):
                    self.spec = np.array(self.spectrometer.get_intensities())
                    self.sendSpectrum.emit(self.wls, self.spec)
                    print(time.strftime('%H:%M:%S') + f' Spectrum acquired for scmp= {scmp_value} um')

        self.sendProgress.emit(100)
        print(time.strftime('%H:%M:%S') + ' Finished')
        return

    def stop(self):
        self.terminate = True
        print(time.strftime('%H:%M:%S') + ' Request Stop')


class CompressorMeasurement(QtCore.QThread):
    sendSpectrum = QtCore.pyqtSignal(np.ndarray, np.ndarray)  # Final averaged image (e.g., A_opt)
    sendProgress = QtCore.pyqtSignal(float)
    sendSave = QtCore.pyqtSignal(str, str)
    sendParameter = QtCore.pyqtSignal(str, float)

    def __init__(self, devices, compr_scan_lineEdit,avg_value):
        super(CompressorMeasurement, self).__init__()
        self.spectrometer = devices['spectrometer']
        self.wls = []  # preallocate wls array
        self.spec = []  # preallocate spec array
        line_components = [float(x) for x in re.split(':', compr_scan_lineEdit)]
        self.compr_array =  np.arange(line_components[0], line_components[2] + line_components[1], line_components[1])
        self.avg_value = avg_value
        print('Measure chirp scan with following compressor positions:', self.compr_array)
        self.terminate = False

    def run(self):
        self.wls = np.array(self.spectrometer.get_wavelength())
        for i,compr_value in enumerate(self.compr_array):
            if not self.terminate:  # check whether stopping measurement is called
                self.sendProgress.emit(i/len(self.compr_array)*100)
                print(time.strftime('%H:%M:%S') + f' Move compressor to {compr_value} um')
                self.sendParameter.emit('Motor_1', compr_value/1E3) # transform to mm
                time.sleep(2) # no feedback on when Motor is set.
                for j in range(self.avg_value):
                    self.spec = np.array(self.spectrometer.get_intensities())
                    self.sendSpectrum.emit(self.wls, self.spec)
                    print(time.strftime('%H:%M:%S') + f' Spectrum acquired for compressor= {compr_value} um')

        self.sendProgress.emit(100)
        print(time.strftime('%H:%M:%S') + ' Finished')
        return

    def stop(self):
        self.terminate = True
        print(time.strftime('%H:%M:%S') + ' Request Stop')




class HelicamBackgroundMeasurement(QtCore.QThread):
    sendSpectrum = QtCore.pyqtSignal(np.ndarray)  # Final averaged image (e.g., A_opt)
    #sendSave = QtCore.pyqtSignal(str, str)
    #sendParameter = QtCore.pyqtSignal(str, float)

    def __init__(self, devices):
        super(HelicamBackgroundMeasurement, self).__init__()
        self.spectrometer = devices['spectrometer']
        self.wls = []  # preallocate wls array
        self.spec = []  # preallocate spec array
        self.terminate = False
        #self.acquiring = True

    def run(self):
        print(time.strftime('%H:%M:%S') + "HelicamBackgroundMeasurement started")

        #Stopping the CameraWorker
        self.spectrometer.worker.pause()
        while self.spectrometer.worker.processing:
            time.sleep(0.1)

        #Acquiring data
        self.wls = np.array(self.spectrometer.get_wavelength())
        if not self.terminate:
            rawI, rawQ = self.spectrometer.worker.acquire()
            twoD_avgI = np.mean(rawI, axis=0)
            twoD_avgQ = np.mean(rawQ, axis=0)
            twoD_IdivQ = twoD_avgI / twoD_avgQ
            self.sendSpectrum.emit(twoD_avgI)
            print(time.strftime('%H:%M:%S'), ': Acquisition complete')
            time.sleep(0.5)
        print(time.strftime('%H:%M:%S') + 'HelicamBackgroundMeasurement done')

        #Downloading the data
        ty_res = time.localtime(time.time())
        timestamp = time.strftime("%H_%M_%S", ty_res)
        folder = r"C:\DATA\BIGFOOT\2025-07-23"
        filename = os.path.join(folder, "bg_wo_light" + timestamp + '.h5')
        with h5py.File(filename, 'w') as f:
            f.create_dataset('averaged_rawI', data=twoD_avgI)
            f.create_dataset('averaged_rawQ', data=twoD_avgQ)
        print(time.strftime('%H:%M:%S') + 'HelicamBackgroundMeasurement saved')

        #Restarting the CameraWorker
        self.spectrometer.worker.resume()

        return

    def stop(self):
        self.terminate = True
        print(time.strftime('%H:%M:%S') + ' Request Stop')
