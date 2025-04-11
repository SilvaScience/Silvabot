# -*- coding: utf-8 -*-
"""
Created on Thu Apr 10 21:31:30 2025

@author: David Tiede
"""

from thorlabs_PM import ThorlabsPM100D



power_meter = ThorlabsPM100D(debug=False)
print(power_meter.get_wavelength())
power_meter.get_average_count()
print(power_meter.measure_power())