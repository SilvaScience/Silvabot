"""
Created on Mon Oct 10 17:43:53 2022

@author: DT
Hardware class to control cryostat. All hardware classes require a definition of
parameter_dict (set write and read parameter)
parameter_display_dict (set Spinbox options)
set_parameter function (assign set functions)

"""

from PyQt5 import QtCore, QtWidgets
import time
from collections import defaultdict
import socket
import sys
import json
import requests
import random
from drivers.Topas4Locator import Topas4Locator
import numpy as np


class Orpheus(QtCore.QObject):
    name = 'Orpheus'

    def __init__(self):
        super(Orpheus, self).__init__()

        # initialize connection to ORPHEUS
        serialNumber = "P24909"
        locator = Topas4Locator()
        availableDevices = locator.locate()
        self.match = next((obj for obj in availableDevices if obj['SerialNumber'] == serialNumber), None)
        self.match = None
        if self.match is None:
            print('Device with serial number %s not found. Try connect with base address' % serialNumber)
            self.baseAddress =  "http://192.168.1.132:8000/P24909/v0/PublicAPI"
        else:
            self.baseAddress = self.match['PublicApiRestUrl_Version0']

        # set parameter dict
        self.parameter_dict = defaultdict()

        # setting up variables, open array
        self.stop = False
        self.parameter_dict['set_wl'] = 10
        self.parameter_dict['current_wl'] = 1
        self.parameter_dict['shutter'] = 0
        self.parameter_dict['scmp'] = float(self.get('/Motors/ActualPositionInUnits?id=10').text)*1E3
        self.parameter_display_dict = defaultdict(dict)
        self.parameter_display_dict['shutter']['read'] = False
        self.parameter_display_dict['shutter']['val'] = 0
        self.parameter_display_dict['shutter']['unit'] = ' per'
        self.parameter_display_dict['shutter']['max'] = 100
        self.parameter_display_dict['set_wl']['val'] = float(self.get('/Optical/WavelengthControl/Output/Wavelength').text)
        self.parameter_display_dict['set_wl']['unit'] = ' nm'
        self.parameter_display_dict['set_wl']['max'] = 2600
        self.parameter_display_dict['set_wl']['read'] = False
        self.parameter_display_dict['current_wl']['val'] = 5
        self.parameter_display_dict['current_wl']['unit'] = ' nm'
        self.parameter_display_dict['current_wl']['max'] = 2600
        self.parameter_display_dict['current_wl']['read'] = True
        self.parameter_display_dict['scmp']['val'] = self.parameter_dict['scmp']
        self.parameter_display_dict['scmp']['unit'] = ' um'
        self.parameter_display_dict['scmp']['max'] = 11700 # max permitted value for this motor as readout through HTML commands
        self.parameter_display_dict['scmp']['read'] = False

        # defining waitTime
        self.waitTime = 0.1

        # start updating temp
        self.thread = QtCore.QThread()
        self.worker = UpdateWorker(self.baseAddress)

        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.new_wl.connect(self.update_wl)

        self.thread.start()

        # set ignore wavelength separator variable
        self.ignore_user_actions = False



    def put(self, url, data):
        r = requests.put(self.baseAddress + url, json=data)


    def get(self, url):
        return requests.get(self.baseAddress + url)

    def set_parameter(self, parameter, value):
        if parameter == 'set_wl':
            self.parameter_dict['set_wl'] = value
            self.put('/Optical/WavelengthControl/SetWavelengthUsingAnyInteraction', json.dumps(value))
            self.wait_till_wl_is_set()
        if parameter == "shutter":
            self.parameter_dict['shutter']  = value
            if value < 100:
                self.put('/ShutterInterlock/OpenCloseShutter', False)
            else:
                self.put('/ShutterInterlock/OpenCloseShutter', True)
        if parameter == "scmp":
            self.put('/Motors/TargetPositionInUnits?id=10', json.dumps(value*1E-3))
            time.sleep(0.2)
            self.parameter_dict['scmp'] = self.get('/Motors/ActualPositionInUnits?id=10').json()

    def update_wl(self, new_wl):
        self.parameter_dict['current_wl'] = new_wl

    def wait_till_wl_is_set(self):
        # Waits till wavelength setting is finished.  If user needs to do any manual
        # operations (e.g.  change wavelength separator), inform him/her and wait for confirmation.
        while True:
            s = self.get('/Optical/WavelengthControl/Output').json()
            sys.stdout.write("\r %d %% done" % (s['WavelengthSettingCompletionPart'] * 100.0))
            if s['IsWavelengthSettingInProgress'] == False or s['IsWaitingForUserAction']:
                break
        state = self.get('/Optical/WavelengthControl/Output').json()
        if state['IsWaitingForUserAction']:
            print("\nOrpheus user actions required.")
            # inform user what needs to be done
            user_action_string = ''
            for item in state['Messages']:
                user_action_string = user_action_string + item['Text'] + '\n'
            if self.ignore_user_actions:
                print('Warning! User actions are ignored. Open Shutter.')
                self.put('/ShutterInterlock/OpenCloseShutter', True)
            else:
                resp = self.separator_popup(user_action_string)
            # tell the device that required actions have been performed.
            # If shutter was open before setting wavelength it will be opened again
            self.put('/Optical/WavelengthControl/FinishWavelengthSettingAfterUserActions', {'RestoreShutter': True})

    def separator_popup(self, user_action_string):
        # popup if user action is required
        msgBox = QtWidgets.QMessageBox()
        msgBox.setIcon(QtWidgets.QMessageBox.Information)
        msgBox.setText(user_action_string)
        msgBox.setWindowTitle("Warning")
        msgBox.setStandardButtons(QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel)
        return_value = msgBox.exec()
        if return_value == QtWidgets.QMessageBox.Ok:
            return True
        else:
            return False

    def stop_worker(self):
        # TO BE IMPLEMENTED
        self.worker.stop = True
        self.thread.quit()
        self.thread.wait()


class UpdateWorker(QtCore.QObject):
    new_wl = QtCore.pyqtSignal(float)

    def __init__(self, base_address):
        super(UpdateWorker, self).__init__()
        self.baseAddress = base_address #"http://192.168.1.120:8000/P24909/v0/PublicAPI"
        self.current_wl = []
        self.stop = False
        self.waitTime = 0.1

    def run(self):
        while not self.stop:
            # calling the read wavelength function
            self.current_wl = self.read_wl()

            # waiting to remeasure the wavelength
            time.sleep(self.waitTime)
            self.new_wl.emit(self.current_wl)

    def get(self, url):
        response = requests.get(self.baseAddress + url)
        return float(response.text)

    def read_wl(self):
        # read the current wavelength
        current_wl = self.get('/Optical/WavelengthControl/Output/Wavelength')
        return current_wl
