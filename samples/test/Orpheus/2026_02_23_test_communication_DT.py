# -*- coding: utf-8 -*-
"""
Created on Thu Oct  6 10:44:11 2022

@author: NanoUltrafast2
"""


import socket
import sys
import json
import time

import requests
import random
from Topas4Locator import Topas4Locator


def put(baseAddress, url, data):
    #print('putting')
    print(requests.put(baseAddress + url, json = data).content)
    return requests.put(baseAddress + url, json = data)

def get(baseAddress, url):
    r = requests.get(baseAddress + url)
    #print(r.text)
    return requests.get(baseAddress + url)

serialNumber = "P24909"
locator = Topas4Locator()
availableDevices = locator.locate()
print(availableDevices)
match = next((obj for obj in availableDevices if obj['SerialNumber']==serialNumber), None)
if match is None:
    print ('Device with serial number %s not found' % serialNumber)
else:
    baseAddress = match['PublicApiRestUrl_Version0']

baseAddress = "http://192.168.1.120:8000/P24909/v0/PublicAPI"
#shutter = False
#put(baseAddress, '/ShutterInterlock/OpenCloseShutter', shutter)
#time.sleep(0.5)
#shutter = True
#put(baseAddress, '/ShutterInterlock/OpenCloseShutter', shutter)
#time.sleep(0.5)
#shutter = False
#put(baseAddress, '/ShutterInterlock/OpenCloseShutter', shutter)

# test motor connection
motors = get(baseAddress, '/Motors/AllProperties').json()
props =motors['Motors']
for motor in props:
    motor_id = motor['Index']
    motor_title =motor['Title']
    motor_position = motor['ActualPosition']
    motor_position_min = motor['MinimalPositionInUnits']
    motor_position_max = motor['MaximalPositionInUnits']
    
    print(motor_id,motor_title,motor_position, 'min:',motor_position_min ,'max:',motor_position_max)


# set SCMP to a specific position in Units (mm)
value =2.263
put(baseAddress,'/Motors/TargetPositionInUnits?id=10',json.dumps(value))
time.sleep(1)
#interactions = get(baseAddress, '/Motors?id=10').json()
#print(interactions)
position = get(baseAddress, '/Motors/ActualPositionInUnits?id=10').json()
print(position)
"""
interactions = get(baseAddress, '/Optical/WavelengthControl/ExpandedInteractions').json()
print("Available interactions:")
print(interactions)
for item in interactions:
   print(item['Type'] + " %d - %d nm" % (item['OutputRange']['From'], item['OutputRange']['To']))
if len(interactions) > 0:
  interaction = interactions[random.randint(0,len(interactions) - 1)] #set wavelength using random interaction
  #wavelength is selected randomly too, to be in valid range for that
wavelengthToSet = interaction['OutputRange']['From'] + (interaction['OutputRange']['To'] - interaction['OutputRange']['From']) * random.uniform(0,1)
print("setting wavelength %.4f nm using interaction %s" % (wavelengthToSet, interaction['Type']))
print('/Optical/WavelengthControl/SetWavelength', { 'Interaction':interaction['Type'], 'Wavelength':wavelengthToSet })
#response = put(baseAddress,'/Optical/WavelengthControl/SetWavelengthUsingAnyInteraction', json.dumps(float(800)))
r = requests.get(baseAddress + '/Optical/WavelengthControl/Output/Wavelength')
print(get(baseAddress,'/Optical/WavelengthControl/Output/Wavelength').content)
"""