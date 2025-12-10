# -*- coding: utf-8 -*-
"""
Created on Thu Apr 10 21:29:46 2025

@author: David Tiede
"""

#from __future__ import division, print_function
import pyvisa
import time
import logging
#from ThorlabsPM100 import ThorlabsPM100, USBTMC
TRIES_BEFORE_FAILURE = 10
RETRY_SLEEP_TIME = 0.010  # in seconds

logger = logging.getLogger(__name__)


class ThorlabsPM100D(object):
    """
    Thorlabs PM100D power meter
    
    uses the PyVISA 1.5 library to communicate over USB.
    """

    
    def __init__(self, port="USB0::0x1313::0x8075::P5002302::INSTR", debug=False):
        self.name = 'PM100D'
        self.port = port
        self.debug = debug

        self.visa_resource_manager = pyvisa.ResourceManager()
    
        if debug: 
            print('List of resources')
            print(self.visa_resource_manager.list_resources(query='?*'))
    
        self.pm = self.visa_resource_manager.open_resource(port)
    
        self.idn = self.query("*IDN?")
        
        self.sensor_idn = self.query("SYST:SENS:IDN?")
        if debug: 
            print('Device name:'+self.sensor_idn)
        
        self.write("CONF:POW") # set to power meaurement

        self.wavelength_min = float(self.query("SENS:CORR:WAV? MIN"))
        self.wavelength_max = float(self.query("SENS:CORR:WAV? MAX"))
        self.get_wavelength()
        
        self.get_attenuation_dB() # does not exist
        
        self.write("SENS:POW:UNIT W") # set to Watts
        self.power_unit = self.query("SENS:POW:UNIT?")


        self.get_auto_range()
                
        self.get_average_count() # does not exist
        
        self.get_power_range()        
        self.measure_power()
        self.measure_frequency() # does not exist
        
        
    
    def query(self, cmd):
        if self.debug: logger.debug( "PM100D query " + repr(cmd) )
        resp = self.pm.query(cmd)
        if self.debug: logger.debug( "PM100D resp ---> " + repr(resp) )
        return resp
    
    def write(self, cmd):
        if self.debug: logger.debug( "PM100D write" + repr(cmd) )
        resp = self.pm.write(cmd)
        if self.debug: logger.debug( "PM100D written --->" + repr(resp))
        
    def get_wavelength(self):
        try_count = 0
        while True:
            try:
                self.wl = float(self.query("SENS:CORR:WAV?"))
                if self.debug: logger.debug( "wl:" + repr(self.wl) )
                break
            except:
                if try_count > 9:
                    logger.warning( "Failed to get wavelength." )
                    break
                else:
                    time.sleep(RETRY_SLEEP_TIME)  #take a rest..
                    try_count = try_count + 1
                    logger.debug( "trying to get the wavelength again.." )
        return self.wl
    
    def set_wavelength(self, wl):
        try_count = 0
        while True:
            try:
                self.write("SENS:CORR:WAV %f" % wl)
                time.sleep(0.005) # Sleep for 5 ms before rereading the wl.
                break
            except:
                if try_count > 9:
                    logger.warning( "Failed to set wavelength." )
                    time.sleep(0.005) # Sleep for 5 ms before rereading the wl.
                    break
                else:
                    time.sleep(RETRY_SLEEP_TIME)  #take a rest..
                    try_count = try_count + 1
                    logger.warning( "trying to set wavelength again.." )

        return self.get_wavelength()
    
    def get_attenuation_dB(self):
        # in dB (range for 60db to -60db) gain or attenuation, default 0 dB
        self.attenuation_dB = float( self.query("SENS:CORR:LOSS:INP:MAGN?") )
        if self.debug: logger.debug( "attenuation_dB " + repr(self.attenuation_dB))
        return self.attenuation_dB

    def get_average_count(self):
        """each measurement is approximately 3 ms.
        returns the number of measurements
        the result is averaged over"""
        self.average_count = int( self.query("SENS:AVER:COUNt?") )
        if self.debug: logger.debug( "average count:" +  repr(self.average_count))
        return self.average_count
    
    def set_average_count(self, cnt):
        """each measurement is approximately 3 ms.
        sets the number of measurements
        the result is averaged over"""
        self.write("SENS:AVER:COUNT %i" % cnt)
        return self.get_average_count()
            
    def measure_power(self):
        self.power = float(self.query("MEAS:POW?"))
        if self.debug: logger.debug( "power: " + repr( self.power))
        return self.power
        
    def get_power_range(self):
        #un tested
        self.power_range = self.query("SENS:POW:RANG:UPP?") # CHECK RANGE
        if self.debug: logger.debug( "power_range " + repr( self.power_range ))
        return self.power_range

    def set_power_range(self, range):
        #un tested
        self.write("SENS:POW:RANG:UPP {}".format(range))

    def get_auto_range(self):
        resp = self.query("SENS:POW:RANG:AUTO?")
        if True:
            logger.debug( 'get_auto_range ' + repr(resp) )
        self.auto_range = bool(int(resp))
        return self.auto_range
    
    def set_auto_range(self, auto = True):
        logger.debug( "set_auto_range " + repr( auto))
        if auto:
            self.write("SENS:POW:RANG:AUTO ON") # turn on auto range
        else:
            self.write("SENS:POW:RANG:AUTO OFF") # turn off auto range
    
    
    def measure_frequency(self):
        self.frequency = self.query("MEAS:FREQ?")
        if self.debug: logger.debug( "frequency " + repr( self.frequency))
        return self.frequency


    def get_zero_magnitude(self):
        resp = self.query("SENS:CORR:COLL:ZERO:MAGN?")
        if self.debug:
            logger.debug( "zero_magnitude " + repr(resp) )
        self.zero_magnitude = float(resp)
        return self.zero_magnitude
        
    def get_zero_state(self): 
        resp = self.query("SENS:CORR:COLL:ZERO:STAT?")
        if self.debug:
            logger.debug( "zero_state" + repr(resp))
        self.zero_state = bool(int(resp))
        if self.debug:
            logger.debug( "zero_state" + repr(resp) + '--> ' + repr(self.zero_state))
        return self.zero_state
    
    def run_zero(self):
        self.write("SENS:CORR:COLL:ZERO:INIT")
        #resp = self.query("SENS:CORR:COLL:ZERO:INIT")
        #return resp
    
    def get_photodiode_response(self):
        resp = self.query("SENS:CORR:POW:PDIOde:RESP?")
        #resp = self.query("SENS:CORR:VOLT:RANG?")
        #resp = self.query("SENS:CURR:RANG?")
        if self.debug:
            logger.debug( "photodiode_response (A/W)" + repr(resp) )
        
        self.photodiode_response = float(resp) # A/W
        return self.photodiode_response 
    
    def measure_current(self):
        resp = self.query("MEAS:CURR?")
        if self.debug:
            logger.debug( "measure_current " + repr(resp))
        self.current = float(resp)
        return self.current
    
    def get_current_range(self):
        resp = self.query("SENS:CURR:RANG:UPP?")
        if self.debug:
            logger.debug( "current_range (A)" + repr(resp))
        self.current_range = float(resp)
        return self.current_range
        
    def close(self):
        return self.pm.close()