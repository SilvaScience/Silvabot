""""
import zhinst.utils as utils
import zhinst.core
import time


# Parameters
device_id = 'dev7797'  # Replace with your actual device ID
interface = '1GbE'     # or 'USB'
host = '127.0.0.1'     # or IP of the LabOne server

# Create and connect to the device
daq = zhinst.core.ziDAQServer(host, 8004, 6)  # port 8004, API Level 6
daq.connectDevice(device_id, interface)

# Subscribe to a demodulator output
path = f'/{device_id}/demods/0/sample'
daq.subscribe(path)

daq.setInt(f'/{device_id}/demods/0/enable', 1)
daq.sync()

# Read data continuously (e.g., in a loop)

daq.flush()  # Clear old data
start_time = time.time()
duration = 10  # Stream for 10 seconds

while time.time() - start_time < duration:
    data = daq.read()
    if path in data:
        samples = data[path]['x'] + 1j * data[path]['y']
        timestamps = data[path]['timestamp']
        # Do something with samples
        print(samples)
    time.sleep(0.1)  # Adjust sleep to your sampling needs

"""
import zhinst.core
import time
import numpy as np

# Setup parameters
device_id = 'dev7797'  # Replace with your device ID
host = 'localhost'  # or instrument IP
port = 8004  # default LabOne port
interface = '1GbE'  # or 'USB'

# Connect to the device
daq = zhinst.core.ziDAQServer(host, port, 6)
daq.connectDevice(device_id, interface)

# Subscribe to demodulator signal (x + iy)
path = f'/{device_id}/demods/0/sample'
daq.subscribe(path)

# Flush previous data and sync
daq.flush()
daq.sync()

# Start polling
poll_duration = 0.1  # seconds
total_time = 5  # seconds to run
start_time = time.time()

print("Streaming data...")
t1 = time.time()
while time.time() - start_time < total_time:
    # Poll returns a dictionary with data
    t1 = time.time()
    data = daq.poll(poll_duration, 500, 0, True)
    print(time.time()-t1)

    if path in data:
        samples = data[path]
        x = samples['x']
        y = samples['y']
        timestamps = samples['timestamp']
        complex_signal = np.array(x) + 1j * np.array(y)

        # Do something with the signal
        #print(f"Samples: {complex_signal[:5]} ...")  # print first 5 values
    else:
        print("No data received in this poll.")

# Cleanup
daq.unsubscribe(path)
