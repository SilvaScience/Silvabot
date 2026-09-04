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
import h5py
import os
# from jki_python_bridge_for_labview import labview as lv

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
                 spectra_avg, power_dep, filter_pos, int_times,sequence_check,sequence_text):
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
        try:
            self.sequence = re.split(',', sequence_text)
        except ValueError:
            print('WARNING: Splitting sequence line text did not work')
        self.sequence_check = sequence_check

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
                    if self.sequence_check:
                        for s in self.sequence:
                            if s =='a':
                                if hasattr(self.spectrometer, 'shutter'):
                                    self.spectrometer.start_acquisition()
                                for m in range(self.spectra_avg):  # take several spectra for each acquistion
                                    self.spec = np.array(self.spectrometer.get_intensities())
                                    self.sendSpectrum.emit(self.wls, self.spec)
                                    print(time.strftime('%H:%M:%S') + ' Spectrum acquired')
                                if hasattr(self.spectrometer, 'shutter'):
                                    self.spectrometer.stop_acquisition()
                            elif s[0:3] == 'int':
                                try:
                                    value = float(s[4:])
                                    self.sendParameter.emit('int_time', value)
                                    print(time.strftime('%H:%M:%S') + f' Integration time set to {value}')
                                    time.sleep(3)
                                except ValueError:
                                    print(f'WARNING, unexpected {s} argument')
                            elif s[0] == 'f':
                                filter_number = s[1]
                                try:
                                    value = float(s[3:])
                                    filter_string = 'filter_wheel_' + filter_number
                                    self.sendParameter.emit(filter_string, value)
                                    print(time.strftime('%H:%M:%S') + f' {filter_string} set to {value}')
                                    time.sleep(7)
                                except ValueError:
                                    print(f'WARNING, unexpected {s} argument')
                            elif s[0] == 'l':
                                try:
                                    value = float(s[1:])
                                    self.sendParameter.emit('laser_diode', value)
                                    print(time.strftime('%H:%M:%S') + f' Laser diode set to {value}')
                                    time.sleep(3)
                                except ValueError:
                                    print(f'WARNING, unexpected {s} argument')
                            else:
                                print(f'Unknown sequence string: {s}')
                        progress = n / len(self.T_series) * 100
                        self.sendProgress.emit(progress)
                        if self.terminate:
                            self.sendProgress.emit(100)

                    else:
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

        self.sendProgress.emit(100)
        print(time.strftime('%H:%M:%S') + ' Finished')
        return

    def stop(self):
        self.terminate = True
        print(time.strftime('%H:%M:%S') + ' Request Stop')

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
        self.speclength = (self.spectrometer.spec_length[0], 200 * self.nb_of_spectra)  # Definition of the spec_length of the stitched spectrum that will be sent to DataHandling (200 is the number of points for each individual spectra that is kept when stitching them together)

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

class DelayStageMeasurement(QtCore.QThread):
    sendSpectrum = QtCore.pyqtSignal(np.ndarray, np.ndarray)  # Final averaged image (e.g., A_opt)
    sendProgress = QtCore.pyqtSignal(float)
    sendSave = QtCore.pyqtSignal(str, str)
    sendParameter = QtCore.pyqtSignal(str, float)

    def __init__(self, devices, delay_stage_scan_lineEdit,t_axis_value):
        super(DelayStageMeasurement, self).__init__()
        self.spectrometer = devices['spectrometer']
        self.wls = []  # preallocate wls array
        self.spec = []  # preallocate spec array
        line_components = [float(x) for x in re.split(':', delay_stage_scan_lineEdit)]
        self.delay_stage_scan_array =  np.arange(line_components[0], line_components[2] + line_components[1], line_components[1])
        if t_axis_value ==1:
            self.scan_axis = 'tau'
        elif t_axis_value ==2:
            self.scan_axis = 'T_pop'
        elif t_axis_value ==3:
            self.scan_axis = 't'
        elif t_axis_value ==4:
            self.scan_axis = 'target_position'
        print(f'Measure delay stage scan at axis {self.scan_axis} following delays:', self.delay_stage_scan_array)
        self.terminate = False

    def run(self):
        self.wls = np.array(self.spectrometer.get_wavelength())
        for i,t_value in enumerate(self.delay_stage_scan_array):
            if not self.terminate:  # check whether stopping measurement is called
                self.sendProgress.emit(i/len(self.delay_stage_scan_array)*100)
                self.sendParameter.emit(self.scan_axis, t_value)
                #time.sleep(0.5) # no feedback on when SCMP is set.
                self.spec = np.array(self.spectrometer.get_intensities())
                self.sendSpectrum.emit(self.wls, self.spec)
                print(time.strftime('%H:%M:%S') + f' Spectrum acquired for {self.scan_axis}= {t_value} fs')

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

# Measurement of coordinate translation stage scan and UHF data acquisition (like plotter in LabOne) for a back and forth scan of the stage
class THzAcquisition(QtCore.QThread):
    # Define used signals
    # sendTargetPosition = QtCore.pyqtSignal(float, int)
    # sendSpeed = QtCore.pyqtSignal(float, int)
    sendProgress = QtCore.pyqtSignal(float)
    sendSpectrum = QtCore.pyqtSignal(np.ndarray, np.ndarray)
    sendParameter = QtCore.pyqtSignal(str, float)
    plotDataSignal = QtCore.pyqtSignal(np.ndarray, np.ndarray)    # Internal signal (To make sure Qt widgets is accessed from the GUI thread)

    def __init__(self, devices, plot_widget,line_edit, scan_speed, continuous_checkbox, averaging):
        super(THzAcquisition, self).__init__()

        # Store parameters
        self.tstage = devices['tstage']
        self.lock_in = devices['lock_in']
        self.scan_speed = scan_speed
        self.averageing_nb = averaging
        self.plot_widget = plot_widget
        line_components = [float(x) for x in re.split(':', line_edit)]
        self.initial_pos = line_components[0]
        self.scan_resolution = line_components[1]
        self.final_pos = line_components[2]
        self.THz_scan_array =  np.arange(line_components[0], line_components[2] + line_components[1], line_components[1])
        if continuous_checkbox: # checked means continuous
            self.burst_duration = (self.final_pos - self.initial_pos) / self.scan_speed
            self.scan_type = 'Continuous'
        else:
            self.scan_type = 'Step'
            self.burst_duration = 0.1

        self.plotDataSignal.connect(self.plot_data)

        # calculate spec length
        self.spec_length = np.ceil((self.final_pos - self.initial_pos) / self.scan_resolution).astype(int)


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
        self.sendParameter.emit('speed', 10)                         # Set speed to a fast value (10 mm/s) for moving to the initial position
        self.sendParameter.emit('target_position',self.initial_pos)  # Move the stage to the initial position
        current_position = self.tstage.parameter_dict['position']    # Get current position from parameter dict
        while not current_position == self.initial_pos:                # Wait until initial position is reached
            time.sleep(0.1)
            current_position = self.tstage.parameter_dict['position']
        self.sendParameter.emit('speed', self.scan_speed)

        # Scanning
        print('Starting position reached, starting scan')
        clockbase, nodes, module = self.lock_in.DAQ_setup(self.burst_duration)  # Configure UHF for burst acquisition with the defined burst duration and sampling rate

        if self.scan_type == 'Continuous':
            self.sendParameter.emit('target_position',self.final_pos)           # Move the stage to the final position
            voltages = self.Plotter_acquire(clockbase, nodes, module) # Start UHF data acquisition during the scan
            positions = np.linspace(self.initial_pos, self.final_pos, len(voltages)) # Create a list of positions associated with the voltages

        if self.scan_type == 'Step':

            # Initialize lists to store data
            positions = np.zeros(self.spec_length)
            voltages = np.zeros(self.spec_length)
            
            for i in range(self.spec_length):
                self.acquisition_number = i
                self.sendParameter.emit('target_position',self.THz_scan_array[i])    # Move the stage to ith target position
                # consider placeing wait time/while loop to make sure stage has reached its position
                time.sleep(self.lock_in.time_constant * 4)                           # Wait for the filter of the lock-in to settle
                positions[i] = self.tstage.parameter_dict['position']     # Measure the exact position of the stage
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
        self.plot_widget.clear()
        self.plot_widget.plot(time_array, voltages * 1e6, pen='b', linewidth=0.5, label='Vertical')
        self.plot_widget.setLabel('bottom', 'Time (ps)')
        self.plot_widget.setLabel('left', 'Amplitude R (µV)')
        self.plot_widget.addLegend()

        # Send the data to DataHandling for saving
        time_attribute = np.array([0, time_array[-1], len(pos)]) # Create time attribute to be saved in the H5 file. This will prevent overflowing the H5 attribute while allowing to reconstruct the time array from the attribute when loading the data in mdsam
        self.sendSpectrum.emit(time_attribute, voltages * 1e6)   # Send the data to DataHandling for saving
    
    def stop(self):
        self.terminate = True
