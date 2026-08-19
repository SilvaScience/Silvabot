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


# Measurement to acquire one raw 2D sensor frame
class AcquireImage(QtCore.QThread):
    """
        Acquires one frame exactly as the camera currently reads it, rather than the 1D spectrum
        AcquireMeasurement expects. Used while the sensor view holds the camera at full frame, so
        the image on screen can be saved instead of only looked at.

        Nothing here is specific to a camera: any spectrometer reporting frame_shape() gets this.
        Declaring spec_length is what makes it work -- start_measurement() resizes DataHandling to
        match before any data arrives, and from there the frame travels the same path a Heliotis
        image does: stored by concatenate_data's 2D branch, saved in the same format, and displayed
        by set_data's 2D branch, where the math ROIs and 'Sum mode' already apply to it.
    """
    # set used signal types, destination is set in main script
    sendSpectrum = QtCore.pyqtSignal(np.ndarray, np.ndarray)
    sendProgress = QtCore.pyqtSignal(float)

    def __init__(self, devices, parameter):
        super(AcquireImage, self).__init__()
        self.spectrometer = devices['spectrometer']
        if not hasattr(self.spectrometer, 'frame_shape'):
            """ Refuse here rather than emitting a frame DataHandling was never sized for: without
            spec_length, start_measurement leaves the buffers at the device's 1D default and
            concatenate_data fails on the shape mismatch, well away from the cause. """
            raise RuntimeError(
                f"{type(self.spectrometer).__name__} does not report frame_shape(), "
                "so the size of its frames isn't known ahead of the acquisition.")
        self.spec_length = self.spectrometer.frame_shape()
        self.wls = []  # preallocate wls array
        self.spec = []  # preallocate spec array
        self.terminate = False

    def run(self):
        if not self.terminate:  # check whether stopping measurement is called
            self.sendProgress.emit(50)
            self.wls = np.array(self.spectrometer.get_wavelength())
            # Averaging over avg_scan, if set, is done by the driver inside get_intensities().
            self.spec = np.array(self.spectrometer.get_intensities())
            self.sendSpectrum.emit(self.wls, self.spec)
            print(time.strftime('%H:%M:%S') + f' Image acquired {self.spec.shape}')
            self.sendProgress.emit(100)

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
    """
        Stitches spectra taken at successive monochromator positions into one spectrum covering a
        wavelength range wider than a single grating position's window: move the grating, take a
        spectrum, keep the ~flat central region of it, advance, repeat, concatenate.

        Works with any spectrometer exposing get_wavelength()/get_intensities() and attached to a
        monochromator (currently Pixis, Stresing) -- nothing here is specific to either camera.
    """
    # set used signal types, destination is set in main script
    sendSpectrum = QtCore.pyqtSignal(np.ndarray, np.ndarray)
    sendProgress = QtCore.pyqtSignal(float)
    sendParameter = QtCore.pyqtSignal(str, float)
    """ Emits the spectrum stitched so far after every grating position, for a live preview overlay
    (SpectrometerPlot.set_data_preview) -- separate from sendSpectrum, which only fires once at the
    end with the complete result and is what actually reaches DataHandling/gets saved. Without this,
    a stitch covering a wide range gives no visible feedback for the 1-2+ minutes it can take (each
    position needs a 5s settle plus an exposure), which reads as the button having done nothing. """
    sendPreview = QtCore.pyqtSignal(np.ndarray, np.ndarray)

    """ Fraction of each individual spectrum's pixels kept, centered on the middle of the window.
    Points near the edges of a grating position's window are more prone to optical aberrations and
    lower signal, so only the flatter central region is kept before moving to the next position.
    Matches the ~20% (200/1024) a fixed-points version of this class originally used. This is about
    how much of each *raw acquisition* is kept, not the overlap between consecutive *kept* segments
    in the final stitched output -- that's OVERLAP_FRACTION, below. """
    KEEP_FRACTION = 200 / 1024

    """ Fraction of each kept segment's width shared with the next one, blended rather than cut.
    Two independently-acquired segments (different exposure, 5s+ apart) rarely sit at exactly the
    same intensity level -- concatenating them edge-to-edge with no overlap, as this class used to,
    produced a visible step at every seam, and a real line straddling a seam got asymmetrically
    split between the two segments. This is what every stitching approach found across
    spectroscopy actually does instead -- echelle order merging (ESO-MIDAS MERGE/ECHELLE), XAS scan
    merging (Athena), Raman grating-position stitching (Edinburgh Instruments' Extended Scan) all
    keep a real overlap and blend it with a weight that ramps linearly from one segment to the next,
    rather than a hard cut. """
    OVERLAP_FRACTION = 0.2

    def __init__(self, devices, parameter, start_wl, stop_wl):
        super(AcquireSpectrum, self).__init__()
        self.spectrometer = devices['spectrometer']
        self.wls = np.array([])  # preallocate wls array
        self.spec = np.array([])  # preallocate spec array (1D: spectrometers already bin to 1D)
        self.terminate = False
        self.acquire_measurement = True
        self.start_wl = start_wl
        self.end_wl = stop_wl

        """ Stitching only makes sense with a monochromator to move between positions -- the whole
        point is spectra taken at different grating positions. Without this check, a spectrometer
        with no monochromator concept at all (ThorlabsCCS200, Heliotis, ...) would fail confusingly
        later: sendParameter.emit('central_wave', ...) in run() reaches main.py's change_parameter(),
        which raises KeyError since no 'central_wave' widget exists for it. A spectrometer that does
        support a monochromator but isn't attached to one yet (Pixis/Stresing without the separate
        'monochromator' device enabled) fails inside the get_wavelength() probe call right below with
        a clear RuntimeError instead -- this check catches the case that wouldn't. """
        if getattr(self.spectrometer, 'monochromator', None) is None:
            raise RuntimeError(
                "AcquireSpectrum requires a monochromator attached to the spectrometer to move "
                "between grating positions. Enable the 'monochromator' device in config.yaml.")

        """ Points kept per spectrum, and how far (in nm) the center wavelength advances between
        positions, are derived from this spectrometer's actual dispersion (nm covered per pixel at
        its current grating position) rather than a fixed nm value. A fixed step tuned for one
        spectrometer doesn't transfer to another with a different dispersion: assuming ~0.25 nm/px
        (50nm / 200 points, right for a wide-range fiber spectrometer covering ~800nm over
        thousands of pixels) against Pixis+SP2300i's actual ~0.06 nm/px (a ~60nm window over 1024
        pixels) advanced the grating faster than the kept region actually covered, and a 400-700nm
        request stitched only up to ~615nm before running out of positions. """
        probe_wls = np.array(self.spectrometer.get_wavelength())
        window_width_nm = float(np.max(probe_wls) - np.min(probe_wls))
        self.points_kept = max(int(round(len(probe_wls) * self.KEEP_FRACTION)), 2)
        self.overlap_points = max(int(round(self.points_kept * self.OVERLAP_FRACTION)), 0)
        self.kept_width_nm = window_width_nm * self.KEEP_FRACTION
        # How far the center wavelength advances between positions: the kept segment's width minus
        # the portion reserved for blending into the next one.
        self.step_nm = self.kept_width_nm * (1 - self.OVERLAP_FRACTION)

        # Overestimates the number of positions needed to cover [start_wl, end_wl]; the +1 ensures
        # the full requested range is covered even when it doesn't divide evenly by step_nm.
        self.nb_of_spectra = int(np.ceil((self.end_wl - self.start_wl) / self.step_nm) + 1)
        # Length of the stitched spectrum this measurement will hand to DataHandling, which
        # preallocates its buffers to match before this measurement runs (see main.py). The first
        # position contributes points_kept points; every later one blends over overlap_points of
        # them (replacing, not adding to, the existing tail) and appends only the rest.
        self.spec_length = self.points_kept + (self.nb_of_spectra - 1) * (self.points_kept - self.overlap_points)

    """ Widest correction a single seam is allowed to apply, as a factor. Grating efficiency changes
    gently between adjacent positions, so a genuine correction sits near 1.0; anything far outside
    that range means the ratio was measured against noise or a near-empty overlap rather than real
    signal, and applying it would rescale the rest of the sweep by a meaningless number. Clamping
    keeps a bad seam a bad seam instead of letting it corrupt everything stitched after it -- the
    scale factors compound, since each segment is matched to the already-scaled one before it. """
    MAX_OVERLAP_SCALE = 2.0

    """ How much signal a point must carry, as a fraction of the brightest point in the segment it
    came from, before its ratio is allowed to contribute. Ratios taken where neither segment
    recorded any real light are noise divided by noise, and the median of a set of those is still
    noise -- it just looks like a number. """
    OVERLAP_SIGNAL_FLOOR = 1e-3

    def _overlap_scale(self, reference, new, full_scale=None):
        """
            Factor to multiply the new segment by so its level matches the already-stitched spectrum
            across the overlap. This is the standard way overlapping spectra are merged: take the
            ratio between the two in the shared region and scale one onto the other (echelle order
            merging in the ELODIE and MIKE pipelines, module scaling for Spitzer IRS, Astrocook's
            equalize, and the NIST array-spectrometer splicing note, which ties the mismatch
            specifically to grating efficiency varying with grating angle).

            The median of the pointwise ratios, rather than the mean or the ratio of the sums, is
            what makes this usable on our data: a calibration lamp's emission line falling inside the
            overlap dominates a mean, and any pixel near zero sends its individual ratio to infinity.
            The median ignores both. ELODIE iterates a sigma-clipped mean to the same end; the median
            gets there in one step and needs no tuning.
            input:
                - reference (np.ndarray): the overlap as it currently stands in the stitched spectrum
                - new (np.ndarray): the new segment's overlap, already on the reference's wavelength grid
                - full_scale (float): brightest value in the segments these overlaps came from, used
                  to judge which overlap points carry real signal. Falls back to the overlaps' own
                  peak, which is only meaningful when the overlap itself contains the bright part.
            output:
                - float: the factor to apply, 1.0 when the overlap carries too little signal to measure
        """
        reference = np.asarray(reference, dtype=float)
        new = np.asarray(new, dtype=float)
        if full_scale is None:
            full_scale = max(np.max(np.abs(reference)), np.max(np.abs(new)))
        """ Judging "has signal" against the whole segment's peak rather than against zero is what
        makes this hold up once a background is subtracted. Testing > 0 alone happens to be safe
        only while the camera's dark pedestal (~840 counts) sits under every pixel and drags every
        ratio to ~1.0; subtract that pedestal and the same test starts accepting the empty gaps
        between a lamp's emission lines, where the ratio is pure numerical noise. """
        floor = self.OVERLAP_SIGNAL_FLOOR * float(full_scale)
        valid = (np.isfinite(reference) & np.isfinite(new)
                 & (new > floor) & (reference > floor))
        if np.count_nonzero(valid) < 3:
            return 1.0
        scale = float(np.median(reference[valid] / new[valid]))
        if not np.isfinite(scale) or scale <= 0:
            return 1.0
        return float(np.clip(scale, 1.0 / self.MAX_OVERLAP_SCALE, self.MAX_OVERLAP_SCALE))

    def _shutter_mode(self):
        """ Shutter timing mode this measurement needs while it runs, applied once at the start of
        run() below. 'Normal' here, overridden to 'Always Closed' by AcquireBackgroundSpectrum.
        Forcing this explicitly (rather than trusting whatever mode the camera happened to already
        be in) matters because nothing else guarantees the shutter is back in 'Normal' before a real
        measurement starts -- a background sweep restores it in `finally`, but the manual
        'Shutter open' checkbox in SpectrometerPlot can also leave the camera in 'Always Closed',
        and a real Acquire Spectrum run must not silently inherit that and record a blank sweep. """
        return 'Normal'

    def run(self):
        if self.terminate:
            return
        if hasattr(self.spectrometer, 'set_shutter_mode'):
            self.spectrometer.set_shutter_mode(self._shutter_mode())
        self.sendProgress.emit(0)
        half = self.points_kept // 2
        nb_iter = 0
        # Tracked explicitly rather than derived from self.wls[-1]: with overlap, the last stitched
        # wavelength is no longer a fixed distance from the grating's actual center, since the tail
        # gets overwritten by the blend below.
        center_wl = None
        while nb_iter < self.nb_of_spectra and not self.terminate:
            # move grating to select wavelength range
            if nb_iter == 0:                                        # First iteration of the while loop
                center_wl = self.start_wl + self.kept_width_nm / 2  # Center the first window just past start_wl
            else:                                                    # Subsequent iterations of the while loop
                center_wl = center_wl + self.step_nm                # Advance by (kept width - overlap)

            self.sendParameter.emit('central_wave', center_wl)  # Send signal to move the grating
            time.sleep(5)                                       # Wait to ensure the grating is in position before taking the next spectra

            # acquire spectrum
            if hasattr(self.spectrometer, 'shutter'):
                self.spectrometer.start_acquisition()
            new_wls = np.array(self.spectrometer.get_wavelength())    # Get wavelength range of the spectrometer for the new grating position
            new_spec = np.array(self.spectrometer.get_intensities())  # Get the spectrum for the new grating position
            if hasattr(self.spectrometer, 'shutter'):
                self.spectrometer.stop_acquisition()

            """ mid_idx - half : mid_idx - half + points_kept, not mid_idx - half : mid_idx + half --
            the latter is only points_kept elements wide when points_kept is even (2*half ==
            points_kept). When points_kept is odd, 2*half == points_kept - 1, one element short. """
            mid_idx = len(new_wls) // 2 # Find the index of the middle of the wavelength range
            start_idx = mid_idx - half
            segment_wls = new_wls[start_idx:start_idx + self.points_kept]
            segment_spec = new_spec[start_idx:start_idx + self.points_kept]

            if self.overlap_points == 0 or len(self.wls) == 0:
                # Nothing to blend against yet (first position), or blending was configured off.
                self.wls = np.concatenate((self.wls, segment_wls))
                self.spec = np.concatenate((self.spec, segment_spec))
            else:
                """ Blends the shared region instead of cutting: a hard concatenation left a visible
                step at every seam (two independent acquisitions, 5s+ apart, rarely land at exactly
                the same intensity level) and split any line straddling a seam asymmetrically between
                the two segments. Matches how spectra are stitched elsewhere -- echelle order merging,
                XAS scan merging, Raman grating-position stitching all keep an overlap and blend it
                with a ramp rather than cutting. The new segment's overlap is interpolated onto the
                *existing* array's wavelength grid first: the two segments come from different center
                wavelengths, so their pixel-to-wavelength mappings aren't quite identical even though
                both cover roughly the same range here. """
                prev_wls_tail = self.wls[-self.overlap_points:]
                prev_spec_tail = self.spec[-self.overlap_points:]
                new_spec_on_prev_grid = np.interp(
                    prev_wls_tail, segment_wls[:self.overlap_points], segment_spec[:self.overlap_points])

                """ Rescale the new segment onto the level of the one already stitched, using the
                overlap to measure the mismatch. A ramp alone can only hide a step it blends across;
                it cannot remove one, because it assumes both segments already sit at the same level.
                They don't: the grating's diffraction efficiency depends on the grating *angle*, which
                is exactly what changes between positions, so the same wavelength is recorded with a
                different throughput in each segment. That error is multiplicative, which is why the
                seams stayed small on a faint calibration lamp but became large steps under bright
                broadband light -- the size of a multiplicative error scales with the signal. """
                full_scale = max(np.max(np.abs(segment_spec)), np.max(np.abs(self.spec)))
                scale = self._overlap_scale(prev_spec_tail, new_spec_on_prev_grid, full_scale)
                segment_spec = segment_spec * scale
                new_spec_on_prev_grid = new_spec_on_prev_grid * scale

                # Weight for the earlier segment ramps 1 -> 0 across the overlap; the new segment's
                # weight is the complement, ramping 0 -> 1. With the levels now matched by `scale`,
                # this only has to smooth away the residual noise difference, which is what a ramp
                # can actually do.
                ramp = np.linspace(1, 0, self.overlap_points)
                self.spec[-self.overlap_points:] = ramp * prev_spec_tail + (1 - ramp) * new_spec_on_prev_grid

                # The blended region keeps the existing wavelength grid (prev_wls_tail, unchanged);
                # only the non-overlapping remainder of the new segment is appended as new points.
                self.wls = np.concatenate((self.wls, segment_wls[self.overlap_points:]))
                self.spec = np.concatenate((self.spec, segment_spec[self.overlap_points:]))

            # Add 1 to the iteration counter
            nb_iter += 1
            """ Capped below 100: on the last iteration nb_iter == nb_of_spectra, so the uncapped
            value would be exactly 100.0 here -- before sendSpectrum below has actually handed the
            stitched result to DataHandling. main.py's set_progress() treats progress==100 as "this
            measurement is done" and immediately resets DataHandling's buffer size back to the
            device default, which happened here before the real data was ever added: anything that
            called clear_data() afterwards (starting another measurement, even by mistake, before
            saving) silently wiped the stitched spectrum still sitting unsaved in memory. """
            self.sendProgress.emit(min(99.0, 100 * nb_iter / self.nb_of_spectra))
            self.sendPreview.emit(np.array(self.wls), np.array(self.spec))

        # A stop() requested mid-stitch skips the final emit -- what's collected so far is a
        # partial, unevenly-spaced spectrum, not something DataHandling/a saved file should receive
        # as if it were the complete requested range.
        if not self.terminate:
            self.sendSpectrum.emit(np.array(self.wls), np.array(self.spec))
        self.sendProgress.emit(100)

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

class BFMeasurement(QtCore.QThread):
    sendSpectrum = QtCore.pyqtSignal(np.ndarray, np.ndarray)  # Final averaged image (e.g., A_opt)
    sendProgress = QtCore.pyqtSignal(float)
    sendSave = QtCore.pyqtSignal(str, str)
    sendParameter = QtCore.pyqtSignal(str, float)

    def __init__(self, devices, BF_scan_lineEdit,t_axis_value):
        super(BFMeasurement, self).__init__()
        self.spectrometer = devices['spectrometer']
        self.Bigfoot = devices['bigfoot']
        self.wls = []  # preallocate wls array
        self.spec = []  # preallocate spec array
        line_components = [float(x) for x in re.split(':', BF_scan_lineEdit)]
        self.BF_scan_array =  np.arange(line_components[0], line_components[2] + line_components[1], line_components[1])
        if t_axis_value ==1:
            self.scan_axis = 'tau'
        elif t_axis_value ==2:
            self.scan_axis = 'T_pop'
        elif t_axis_value ==3:
            self.scan_axis = 't'
        print(f'Measure BF scan at axis {self.scan_axis} following delays:', self.BF_scan_array)
        self.terminate = False

    def run(self):
        self.wls = np.array(self.spectrometer.get_wavelength())
        for i,t_value in enumerate(self.BF_scan_array):
            if not self.terminate:  # check whether stopping measurement is called
                self.sendProgress.emit(i/len(self.BF_scan_array)*100)
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
