from pathlib import Path

# Import the module
import pecamerapy
import numpy as np

# Information on the module structure
print("Available methods:")
print(dir(pecamerapy))

# Uncomment to access the documentation
# Lib helper
# help(pecamerapy)

# Camera module helper
# help(pecamerapy.Camera)

# Define a Camera
cam = pecamerapy.Camera()

# Choose the desired connection mode
mode = pecamerapy.OpenMode.USB3
# mode = pecamerapy.OpenMode.SAPERA_FRAME_GRABBER

print(mode)
# Find index, serial
index = -1
try:
    index, serial = cam.find_first(mode)
    print(f"Camera {serial} available at index {index} with mode {mode}")
except Exception as e:
    print(f"Error during connection: {e}")
    exit(-1)

# Open the connection
#index = 11
try:
    cam.open(index, mode)
except pecamerapy.CommOpenError as e:
    print(f"Error during opening: {e}")
    exit(-1)

# Test Getter/Setter
my_mode = cam.get_trigger_mode()  # should be TRIGGER_NONE (or other specified mode)
cam.set_trigger_mode(pecamerapy.TRIGGER_FALLING_EDGE)  # set another mode
cam.get_trigger_mode()  # ensure mode is TRIGGER_FALLING_EDGE
cam.set_trigger_mode(my_mode)  # set initial mode

# Some imaging process
try:
    # Capture 3 frames
    cam.capture(3,3)
    print(cam.get_exposure_time_range())
    print(cam.get_detector_size())

    # Retrieve image + metadata
    img, metadata = cam.get_image(timeout_sec=1)
    img2, metadata = cam.get_image(timeout_sec=1)
    img3, metadata = cam.get_image(timeout_sec=1)
    #img4, metadata = cam.get_image(timeout_sec=1)

    # Display image and metadata values
    print(f"Image values: \n {img}")
    print(np.shape(img), np.max(img), np.min(img))
    print(np.shape(img2), np.max(img2), np.min(img2))
    print(np.shape(img3), np.max(img3), np.min(img3))
    #print(np.shape(img4), np.max(img4), np.min(img4))
    print("Metadata values:")
    print(f"counter: {metadata.counter}")

    # Abort the capture
    cam.abort()

    # Close the camera
    cam.close()
except Exception as e:
    print(f"Error during processing: {e}")