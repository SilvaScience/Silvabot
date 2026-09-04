##
# \file        c4DemodSimple.py
# \author      Balz Marty
# \date        6 March 2024
# \copyright   Heliotis, 2024
# \version     1.0.0
#
# \brief       Simple Python example based on Harvester package for heliCam C4
import os
import numpy as np
import matplotlib.pyplot as plt
from time import sleep
import time
from harvesters.core import Harvester
from packaging.version import parse

import warnings
warnings.simplefilter('always')


def selectDevice(h):
    """
    Scan for available devices and print device list
    let the user select one and open the connection to the device
    if just one device available, open it without user interaction
    \param h harvester object
    \return harvesters camera object
    """

    h.update()
    NDevices = len(h.device_info_list)
    print("{} device(s) detected on the Network:\n".format(NDevices))
    for i,dev in enumerate(h.device_info_list):
        print("{}) {} ({})".format(i+1,dev.id_,dev.serial_number))

    if NDevices == 1:
        selectionInt = 1
    else:
        selectionStr = input("Select a device (0=exit): ")
        selectionInt = int(selectionStr)
        if((selectionInt <= 0) or (selectionInt > NDevices)):
            exit('No device selected - exit script')

    deviceID = h.device_info_list[selectionInt-1].id_
    print('selected device:', deviceID,'\n')
    return h.create(selectionInt-1)

def cameraConfig(camera):
    """
    simple configuration example of heliCam C4 using internal reference
    \param camera harvesters camera object
    """

    # Experiment Parameters


    # Lock-In Amplification (LIA)

    # Sensor sensitivity in %/100, 0.5 for C4-S40, 0.2 for C4-S40U, 0.05 for C4-S41U and 0.25 for C4M
    sensitivity = 0.5
    # Number of intergration periods
    NPeriods = 10
    # Background suppression on/off switch, 'AC' or 'DC'
    coupling = 'DC'
    # Reference frequency in Hz
    refFrequency = 10000.0
    # Source of reference signal, 'Internal' or 'External'
    refSource = 'Internal'
    # Expected frequency deviation of external reference input in %
    expFrequencyDev = 5
    # Number of frames to be recorded
    NFrames = 60

    # Illumination Driving Signal

    # Signal generator DC offset in % of full range
    sgnOffset = 20.0
    # Signal generator peak-to-peak amplitude in % of full range
    sgnAmplitude = 10.0
    # Signal generator frequency in Hz
    sgnFrequency = 9975.0


    # Configuration

    # Trigger

    camera.remote_device.node_map.TriggerSelector.value = "RecordingStart"
    camera.remote_device.node_map.TriggerMode.value = "Off"
    camera.remote_device.node_map.TriggerSelector.value = "FrameStart"
    camera.remote_device.node_map.TriggerMode.value = "On"
    camera.remote_device.node_map.TriggerSource.value = "Software"

    # LIA

    camera.remote_device.node_map.DeviceOperationMode.value = "LockInCam"
    camera.remote_device.node_map.Scan3dExtractionMethod.value = "rawIQ"

    camera.remote_device.node_map.LockInSensitivity.value = sensitivity
    camera.remote_device.node_map.LockInTargetTimeConstantNPeriods.value = NPeriods
    camera.remote_device.node_map.LockInCoupling.value = coupling
    camera.remote_device.node_map.LockInExpectedFrequencyDeviation.value = expFrequencyDev
    camera.remote_device.node_map.LockInTargetReferenceFrequency.value = refFrequency
    camera.remote_device.node_map.AcquisitionBurstFrameCount.value = NFrames

    camera.remote_device.node_map.LockInReferenceSourceType.value = refSource

    # For external reference signal only
    camera.remote_device.node_map.LockInReferenceFrequencyScaler.value = "Off"
    camera.remote_device.node_map.LockInReferenceSourceSignal.value = "FI2"

    # Illumination

    camera.remote_device.node_map.SignalGeneratorOffset.value = sgnOffset
    camera.remote_device.node_map.SignalGeneratorAmplitude.value = sgnAmplitude
    camera.remote_device.node_map.LightControllerSelector.value = "LightController0"
    camera.remote_device.node_map.SignalGeneratorModulationMode.value = "On"
    camera.remote_device.node_map.SignalGeneratorFrequency.value = sgnFrequency
    camera.remote_device.node_map.LightControllerSource.value = "SignalGenerator"

def getOutputShape(camera):
    """
    Get shape of measurement's in-phase/quadrature lock-in output.
    \param h harvester object
    \return tuple (NChannels,Nframes,height,width)
    """
    NFrames = camera.remote_device.node_map.AcquisitionBurstFrameCount.value
    height = camera.remote_device.node_map.Height.value
    width = camera.remote_device.node_map.Width.value

    return 2,NFrames,height,width

def acquire(camera,timeout=30):
    """
    Initiate a measurement and retrieve lock-in data.
    \param h harvester object
    \param t float
    \return numpy array [IRaw,QRaw]
    """

    outputShape = getOutputShape(camera)

    camera.start()
    camera.remote_device.node_map.TriggerSelector.value = 'FrameStart'
    camera.remote_device.node_map.TriggerSoftware.execute()

    with camera.fetch(timeout=timeout) as buffer:

        data = np.array([img.data%2**15//4 for img in buffer.payload.components]).reshape(outputShape)

    camera.stop()

    return data

def plotData(I, Q):
    """
    Plot measurement data
    """

    _,height,width=I.shape
    
    coords = [[110, 120],[451, 454]]
    IPlot = np.array([I[:,coord[1],coord[0]] for coord in coords])
    QPlot = np.array([Q[:,coord[1],coord[0]] for coord in coords])
        
    rms = np.sqrt(np.mean(np.sqrt(I**2 + Q**2)**2, axis=0))

    # styling for the I and Q signals
    style = {"markevery": 1, "mec": "1.0", "ls": ":", "marker": "o"}
    fig = plt.figure(figsize=(12, 9))
    gs = fig.add_gridspec(2, 2)

    ax = fig.add_subplot(gs[0, 0])
    ax.plot(IPlot[0, :], "C1", **style)
    ax.plot(QPlot[0, :], "C2", **style)
    ax.set_title(f"Raw I/Q Signal at (x0={coords[0][0]}, y0={coords[0][1]})")
    ax.set_xlabel("Frame Nr.")
    ax.set_ylabel("Intensity")
    ax.legend(["I", "Q"], loc=4)

    ax = fig.add_subplot(gs[1, 0])
    ax.plot(IPlot[1, :], "C3", **style)
    ax.plot(QPlot[1, :], "C4", **style)

    ax.set_title(f"Raw I/Q Signal at (x1={coords[1][0]}, y1={coords[1][1]})")
    ax.set_xlabel("Frame Nr.")
    ax.set_ylabel("Intensity")
    ax.legend(["I", "Q"], loc=4)

    ax = fig.add_subplot(gs[:, 1])
    im = ax.pcolormesh(rms , cmap="inferno")#,vmin=0, vmax=500
    fig.colorbar(im, ax=ax)
    ax.hlines(coords[0][1],
              xmin=0,
              xmax=width,
              colors="k",
              ls="-.",
              linewidth=0.75)
    ax.vlines(coords[0][0],
              ymin=0,
              ymax=height,
              colors="k",
              ls="-.",
              linewidth=0.75,
              label="_nolegend_")
    ax.hlines(coords[1][1],
              xmin=0,
              xmax=width,
              colors="royalblue",
              ls="-.",
              linewidth=0.75)
    ax.vlines(coords[1][0],
              ymin=0,
              ymax=height,
              colors="royalblue",
              ls="-.",
              linewidth=0.75,
              label="_nolegend_")
    marker = {"marker": "x", "markeredgewidth": 1, "markersize": 8}
    ax.plot(*coords[0], "k", **marker)
    ax.plot(*coords[1], "royalblue", **marker)
    ax.set_title(f"Root Mean Square Lock-In Amplitude")
    ax.legend(["(x0, y0)", "(x1, y1)"], loc=4)
    ax.set_xlabel("X")
    ax.set_ylabel("Y")

    # set the spacing between subplots
    fig.tight_layout(pad=2)
    plt.subplots_adjust(left=None, bottom=None, right=None, top=0.85, wspace=None, hspace=None)
    plt.suptitle("Lock-In Amplification with Sinusoid Input")
    plt.show()

if __name__ == '__main__':

    print('********************************************************')
    print('* Configure and acquire data in "Raw I/Q Mode"')
    print('********************************************************')

    h = Harvester()
    # read heliotis *.CTI path from environment variable
    ctiFile = os.environ['DIAPHUS_GENTL64_FILE']
    print(ctiFile)
    h.add_file(ctiFile)

    # create camera object for interaction
    camera = selectDevice(h)

    # configure camera
    cameraConfig(camera)
    print(f"LockInActualReferenceFrequency: {camera.remote_device.node_map.LockInActualReferenceFrequency.value}Hz")
    sleep(0.1) # make sure illumination output is settled

    # acquire data
    t1 = time.time()
    print(str(time.time() - t1) + 'Start acquisition')
    for i in range(1):
        print(str(time.time() - t1) + f'{i} acquisition')
        rawI,rawQ = acquire(camera)
        avg = np.average(rawI, axis=0)
        print(np.shape(avg))

    # Discard initial frames lacking information present in firmware versions <= 1.9.2
    NFramesDiscard = 0 if parse(camera.remote_device.node_map.DeviceFirmwareVersion.value) > parse('1.9.2') else 2
    print(NFramesDiscard)
    I = rawI[NFramesDiscard:].astype(float)
    Q = rawQ[NFramesDiscard:].astype(float)
    print(np.shape(I))

    # (Optionally) remove the offset (simple time average per pixel)
    removeOffset = True

    if removeOffset:

        I -= np.mean(I, axis=0)
        Q -= np.mean(Q, axis=0)


    # plot measurement data
    plotData(I,Q)

    # free resources
    camera.stop()
    camera.destroy()