# USB ID for screen powermeter is: USB0::0x1313::0x8075::P5002302::INSTR
# USB ID for economy powermeter: USB0::0x1313::0x807B::250825519::INSTR


import pyvisa
import platform
print(platform.architecture())
print(pyvisa.__version__)
print(pyvisa.ResourceManager())


port="USB0::0x1313::0x8075::P5002302::INSTR"#"ASRL4::INSTR"#  #
port = "ASRL4::INSTR"
rm = pyvisa.ResourceManager()

print(rm.list_resources(query='?*'))



pm = rm.open_resource(port)
pm.query("*IDN?")
'''

def __init__(self, port="USB0::0x1313::0x807B::250825519::INSTR", debug=True):
    self.name = 'PM100D'
    self.port = port
    self.debug = debug
    self.tries_before_failure = 10
    self.reading_sleep_time = 0.010  # in seconds

    self.visa_resource_manager = pyvisa.ResourceManager()

    if debug:
        print('List of resources')
        print(self.visa_resource_manager.list_resources(query='?*'))

    try:
        self.pm = self.visa_resource_manager.open_resource(port)
        print('Economy Powermeter connected')
    except:
        port = 'USB0::0x1313::0x8075::P5002302::INSTR'
'''