# -*- coding: utf-8 -*-
"""
Created on Tue Apr 15 14:57:19 2025

@author: David Tiede
"""

import pyvisa as pv
import time
import serial
import re

 
#rm = pv.ResourceManager()
#res = rm.list_resources()impo
#print(res)

def write_command(ser,cmd):
    cmd_bytes = (cmd).encode('ASCII')
    ser.write(cmd_bytes+b"\r")
    out = bytearray()
    char = b""
    missed_char_count = 0
    while char != b"k":
        char = ser.read()
        if char == b"": #handles a timeout here
            missed_char_count += 1
            print('no response')
            time.sleep(1)
        out += char
    return out

#ports = serial.tools.list_ports.comports()
#print(ports)
port = 'COM6'
ser = serial.Serial(port=port, baudrate = 9600, bytesize=8, parity='N',
                                    stopbits=1, xonxoff=0, rtscts=0, timeout=0.02)
#model = ser.write_command("MODEL")
"""
cmd = "MODEL"
model = write_command(ser, cmd)
print(model)
cmd = "MODEL"
ans = write_command(ser, cmd)
print(ans)
cmd = "?GRATING"
ans = write_command(ser, cmd)
print(ans)
cmd = "?NM"
ans = write_command(ser, cmd)
print(ans)
wl = 700.0
wl = float(wl)
cmd = f'{wl:0.3f} GOTO'
ans = write_command(ser, cmd)
print(ans)
time.sleep(1)
cmd = "?NM"
ans = write_command(ser, cmd)
print(ans)
cmd = "?GRATINGS"
ans = write_command(ser, cmd)
print(ans)
cmd = "2 GRATING"
ans = write_command(ser, cmd)
print(ans)
for i in range(4):
    time.sleep(2)
    cmd = "?GRATING"
    ans = write_command(ser, cmd)
    print(ans)
"""
cmd = "?GRATINGS"
ans = write_command(ser, cmd)
print(ans)
print(ans.decode().strip())
test = ans.decode().strip()


#cmd_bytes = (cmd).encode('ASCII')
#ser.write(cmd_bytes+b"\r")
#model = ser.read(10)

ser.close()
