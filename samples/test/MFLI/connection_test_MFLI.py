import csv

import urllib.request
import zhinst
import zhinst.utils
import time
url = "http://127.0.0.1:8006/netlink?id=c0p1t6p1cfm0p1&ziSessionId=0"

webpage = urllib.request.urlopen(url)

datareader = csv.reader(webpage.read().decode().splitlines())

data = []

for row in datareader:
    data.append(row)

#####
#import csv
#import urllib
#url = "http://127.0.0.1:8006/netlink?id=c0p5t6p1cfplotmath&ziSessionId=0"
#webpage = urllib.urlopen(url)
#datareader = csv.reader(webpage)
#data = []
#for row in datareader:
#    data.append(row)

#print(data)

device_id = 'dev7797'#, #: str =
server_host: str = '127.0.0.1'#"localhost"
server_port: int = 8004
plot: bool = True
apilevel_example = 5
(daq, device, _) = zhinst.utils.create_api_session(
    device_id, apilevel_example, server_host=server_host, server_port=server_port
)

data_rate = 210  # [Sa/s]
daq.set(
    [
        # Adjust the data rate of demodulator 1
        (f"/{device}/demods/0/rate", data_rate),
        # Enable the data transfer from demodulator 1 to data server
        (f"/{device}/demods/0/enable", 1),
        # Enable the continuous acquisition of demodulator 1 data
        #(f"/{device}/demods/0/trigger/triggeracq", 0),
    ]
)

# Time difference (s) between two consecutive timestamp ticks
dt_device = daq.getDouble(f"/{device}/system/properties/timebase")

# Current timestamp of the instrument
start_timestamp = daq.getInt(f"/{device}/status/time")

# Subscribe to the signal path of demodulator 1 for acquisition
path = f"/{device}/demods/0/sample"
daq.subscribe(path)

# Poll the subscribed data from the data server. Poll will block and record
# for poll_duration seconds.
t1 = time.time()
print(t1)
for i in range(5):
    poll_duration = 0.5  # [s]
    poll_timeout = 500  # [ms]
    data = daq.poll(poll_duration, poll_timeout, flat=True)

print(time.time()-t1)
# Unsubscribe from all paths.
daq.unsubscribe("*")
print(data)
print('I am here')
print(daq)
print(device)
