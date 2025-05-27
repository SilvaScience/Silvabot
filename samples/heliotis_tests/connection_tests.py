# -*- coding: utf-8 -*-
"""
Created on Tue May 27 15:58:25 2025

@author: bviscogliosi
"""

import sys
print(sys.prefix)

from jki_python_bridge_for_labview import labview as lv


unit_map = {
    'nm': 0,
    'meV': 1,
    'THz': 2,
    'cm-1': 3
}

def units(string):
    try:
        return unit_map[string]
    except KeyError:
        raise ValueError(f"Unknown unit: {string}")
        


lv.connect()
serv_connect = lv.isConnected
print(serv_connect)