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

    def __init__(self, devices, tau_max_value, tau_step_value,avg_value):
        super(TwoDMeasurement, self).__init__()
        self.spectrometer = devices['spectrometer']
        self.Bigfoot = devices['bigfoot']
        self.wls = []  # preallocate wls array
        self.spec = []  # preallocate spec array
        lv.connect()
        step = tau_step_value #lv.LV_Control.read_scan_params()[1] #### can be changed if needed, or added with a button in the interface
        self.tau_array =  np.arange(0, tau_max_value + step, step)
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
