from zhinst.toolkit import Session

# Connect to LabOne Data Server
session = Session("localhost")

print("Connected to Data Server")

devices = session.devices

# List available devices
print("Available devices:")
print(list(devices))
