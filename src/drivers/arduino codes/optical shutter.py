#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Sep 20 16:31:25 2022

@author: katiekoch
"""

import serial
import numpy as np
from serial.tools import list_ports
import time

port = 'COM5'

ser = serial.Serial(port,28800)
ser.reset_input_buffer()
time.sleep(1.75)

command = 'SRV1=25'
print('hello')
command = "ID?"
ser.write(command.encode())
time.sleep(0.2)
print('hello')

# Serial read section
msg = ser.readline()  # read all characters in buffer
print(msg)
#print(type(msg))
#print(msg)
print(msg.decode())
print('hello')










        
