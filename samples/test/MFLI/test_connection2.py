

from zhinst.toolkit import Session

session = Session("localhost")
device = session.connect_device("DEV7797", interface="1GbE")

print(device)
print(device.root)

from pprint import pprint

pprint(session.daq_server.listNodes("/DEV7797/sigins", 0))