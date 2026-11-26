##
# \file        c4DemodFrameTrigger.py
# \author      Balz Marty
# \date        28 October 2026
# \copyright   Heliotis, 2026
# \version     1.0.2
#
# \brief       Python frame triggering example based on Harvester package for heliCam C4
import os
import numpy as np
import matplotlib.pyplot as plt

from harvesters.core import Harvester
from packaging.version import parse

import warnings
warnings.simplefilter('always')


def selectDevice(h):
    """
    Scan for available devices, let the user select one, and open the connection.
    
    If only one device is found, it connects automatically without user interaction.

    Args:
        h: Harvester object.

    Returns:
        Harvesters camera object.
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
    """Configure the heliCam C4 using its internal reference.

    Args:
        camera: Harvester camera object - the camera instance to be configured.
    """

    # Experiment Parameters


    # Lock-In Amplification (LIA)

    # Sensor sensitivity in %/100, 0.25 for C4-S40, 0.1 for C4-S40U, 0.025 for C4-S41U and 0.125 for C4M
    sensitivity = 0.5
    # Number of demodulated intergration periods
    NPeriods = 41
    # Number of blank periods
    NBlankPeriods = 0
    # Background suppression on/off switch, 'AC' or 'DC'
    coupling = 'DC'
    # Reference frequency in Hz
    refFrequency = 350
    # Source of reference signal, 'Internal' or 'External'
    refSource = 'External'
    # Expected frequency deviation of external reference input in %
    expFrequencyDev = 10
    # Number of frames to be recorded
    NFrames = 50

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
    camera.remote_device.node_map.LockInTargetBlankDurationNPeriods.value = NBlankPeriods
    camera.remote_device.node_map.LockInCoupling.value = coupling
    camera.remote_device.node_map.LockInExpectedFrequencyDeviation.value = expFrequencyDev
    camera.remote_device.node_map.LockInTargetReferenceFrequency.value = refFrequency
    camera.remote_device.node_map.AcquisitionBurstFrameCount.value = NFrames

    camera.remote_device.node_map.LockInReferenceSourceType.value = refSource

    # quarter periodic reference triggering accounting for 2f instead of 4f synchronization signal
    camera.remote_device.node_map.LockInReferenceFrequencyScaler.value = "DivideBy4"
    camera.remote_device.node_map.LockInReferenceSourceSignal.value = "FI3"
    camera.remote_device.node_map.TriggerSelector.value = "Reference"
    camera.remote_device.node_map.TriggerActivation.value = "RisingEdge" #"AnyEdge" #
    camera.remote_device.node_map.LockInReferenceTimeShift.value = 100 # additional delay between triggers in μs

    camera.remote_device.node_map.LineSelector.value = "RTIO3"
    camera.remote_device.node_map.LineSource.value = "RecordingActive"
    camera.remote_device.node_map.LineSelector.value = "RTIO2"
    camera.remote_device.node_map.LineSource.value = "LockInReference"

    # Illumination

    camera.remote_device.node_map.LightControllerSource.value = 'SFIO5'
       
    # *********** Setting for frametriggering ******************

    camera.remote_device.node_map.TriggerSelector.value = "LockInFrameStart"
    camera.remote_device.node_map.TriggerMode.value = "On"
    camera.remote_device.node_map.TriggerSource.value = "FI2"
    

def getOutputShape(camera):
    """Get the shape of the measurement's in-phase/quadrature lock-in output.

    Args:
        h: Harvester object.

    Returns:
        Tuple containing (NChannels, Nframes, height, width).
    """
    NFrames = camera.remote_device.node_map.AcquisitionBurstFrameCount.value
    height = camera.remote_device.node_map.Height.value
    width = camera.remote_device.node_map.Width.value

    return 2,NFrames,height,width

def acquire(camera,timeout=30):
    """Initiate a measurement and retrieve lock-in data.

    Args:
        h: Harvester object.
        t: Float representing the exposure or measurement time.

    Returns:
        NumPy array containing [IRaw, QRaw].
    """

    outputShape = getOutputShape(camera)

    camera.start()
    camera.remote_device.node_map.TriggerSelector.value = 'FrameStart'
    camera.remote_device.node_map.TriggerSoftware.execute()

    with camera.fetch(timeout=timeout) as buffer:

        data = np.array([img.data%2**15//4 for img in buffer.payload.components]).reshape(outputShape)

    camera.stop()

    return data

class DataPlotter():
    """
    Abstract superclass for plotting measurement data.
    """
    markersHeatMap = ['v','o']
    colors = plt.rcParams['axes.prop_cycle'].by_key()['color']

    def __init__(self,coords,dataHeatMap,titlesHeatMap,frameRate,suptitleFig,suptitleLateral):
        
        self.coords = coords
        self.NPixels = len(coords)
        self.dataHeatMapPlot = dataHeatMap
        self.titlesHeatMap = titlesHeatMap
        self.frameRate = frameRate
        self.suptitleFig,self.suptitleLateral = suptitleFig,suptitleLateral
    
    def plot(self):

        self.fig,self.axesHeatMap,self.axesTimeSeries = self.partitionPlot()
        self.plotHeatMap()
        self.plotTimeSeries()
        plt.show()

    def partitionPlot(self):

        fig = plt.figure(layout="constrained",figsize=(7.5,7.5))
        fig.suptitle(self.suptitleFig, weight='bold')

        subfigLateral,subfigTimeSeries = fig.subfigures(nrows=2, ncols=1,height_ratios=[1,2])
        subfigLateral.suptitle(self.suptitleLateral)
        subfigTimeSeries.suptitle("Pixelwise Time Evolution")

        axesHeatMap = subfigLateral.subplots(nrows=1,ncols=2)
        axesTimeSeries = subfigTimeSeries.subplots(nrows=self.NPixels,ncols=1,sharey=True)
        return fig,axesHeatMap,axesTimeSeries
    
    def plotHeatMap(self):
        
        for ax,img,title,marker in zip(self.axesHeatMap,self.dataHeatMapPlot,
                                       self.titlesHeatMap,DataPlotter.markersHeatMap):

            vmin,vmax = np.percentile(img,2.5),np.percentile(img,97.5)
            im = ax.imshow(img,origin='lower',vmin=vmin,vmax=vmax)
            ax.set_title(title)
            ax.set_xlabel("x")
            ax.set_ylabel("y",rotation=0)
            self.fig.colorbar(im,ax=ax) 
        
            for coord in self.coords:
                ax.plot(*coord[::-1],marker=marker,ms=7.5,mew=1,mec='black')
    
    def plotTimeSeries(self):

        self.plotDataTSP()
        self.labelAxesTSP()

    def plotDataTSP(self):

        raise NotImplementedError()
    
    def extractDataTSP(self,dataTimeSeries,coords):
        if dataTimeSeries.ndim ==3:
            return np.array([dataTimeSeries[:,*coord[::-1]] for coord in coords])
        elif dataTimeSeries.ndim ==2:
            return np.array([dataTimeSeries[*coord[::-1]] for coord in coords])
        
    def plotLineTSP(self,data,i,ax,**kwags):
        ax.plot(data,color=DataPlotter.colors[i],markevery=2,**kwags)
    
    def labelAxesTSP(self):

        for ax,coord in zip(self.axesTimeSeries[::-1],self.coords):

            ax.set_title('x = {}, y = {}'.format(*coord[::-1]))

            if self.frameRate is not None:
                secax = ax.twiny()
                secax.set_xticks(ax.get_xticks())
                secax.set_xlim(ax.get_xlim())
                secax.set_xticklabels([round(label.get_position()[0]/frameRate*1000,3) for label in ax.get_xticklabels()])

            ax.legend(loc="center right",bbox_to_anchor=(-0.05, 0.5),frameon=False,ncols=1)

        if self.frameRate is not None: secax.set_title("t in ms",loc='right',fontsize=10)
        self.axesTimeSeries[-1].set_xlabel("frame index",loc='right') 

class DataPlotterFrameExtraction(DataPlotter):
    """
    Abstract class for extracting frame to plot from time stack.
    """

    def __init__(self,coords,dataHeatMaps3D,titlesHeatMap,indFrame,frameRate,
                 suptitleFig):
        
        self.indFrame = indFrame if indFrame is not None else len(dataHeatMaps3D)//2
        DataPlotter.__init__(self,coords,dataHeatMaps3D[:2,self.indFrame],titlesHeatMap,frameRate,
                          suptitleFig,'Frame Nr. {}'.format(self.indFrame))
        
    def plotTimeSeries(self):

        DataPlotter.plotTimeSeries(self)
        for ax in self.axesTimeSeries:
            ax.axvline(self.indFrame,color='red',linestyle='dashed')

class DataPlotterInphaseQuadrature(DataPlotterFrameExtraction):
    """
    Code to plot Inphase and Quadrature data stacks using template
    """

    def __init__(self,coords,I,Q,indFrame=None,frameRate=None,stackLabels=['I','Q']):

        self.IDataTSP = self.extractDataTSP(I,coords)
        self.QDataTSP = self.extractDataTSP(Q,coords)
        self.stackLabels = stackLabels
        
        DataPlotterFrameExtraction.__init__(self,coords,np.array([I,Q]),stackLabels,indFrame,frameRate,'In-Phase and Quadrature')

    def plotDataTSP(self):

        for i,ax in enumerate(self.axesTimeSeries[::-1]):

            self.plotLineTSP(self.IDataTSP[i],i,ax,marker=DataPlotter.markersHeatMap[0],label=self.stackLabels[0])
            self.plotLineTSP(self.QDataTSP[i],i,ax,marker=DataPlotter.markersHeatMap[1],label=self.stackLabels[1])

if __name__ == '__main__':

    print('********************************************************')
    print('* Configure and acquire data in "Frame Trigger Mode"*')
    print('********************************************************')

    h = Harvester()
    # read heliotis *.CTI path from environment variable
    ctiFile = os.environ['DIAPHUS_GENTL64_FILE']
    h.add_file(ctiFile)

    # create camera object for interaction
    camera = selectDevice(h)

    # check firmware requirement
    assert parse(camera.remote_device.node_map.DeviceFirmwareVersion.value) >= parse('1.11.0')

    # configure camera
    cameraConfig(camera)
    #dataRaw = acquire(camera)
    
    outputShape = getOutputShape(camera)

    camera.start()
    camera.remote_device.node_map.TriggerSelector.value = 'FrameStart'
    camera.remote_device.node_map.TriggerSoftware.execute()

    timeout = 30
    with camera.fetch(timeout=timeout) as buffer:

        data = np.array([img.data%2**15//4 for img in buffer.payload.components]).reshape(outputShape)

    camera.stop()
    
    NChannels,NFrames,height,width = getOutputShape(camera)
    frameRate = camera.remote_device.node_map.FrameRate.value
    dataRaw = data

    # plot measurement data
    
    NPixels = 3 # Select pixel coordinates whose time evolution is plotted
    coords = np.array([np.linspace(1,axis,NPixels+2)[1:-1].astype(int) for axis in [height,width]]).T
    indFrame = 25 # Select index of frame in stack which is plotted

    DataPlotterInphaseQuadrature(coords,*dataRaw,indFrame=indFrame,frameRate=frameRate,stackLabels=['$I_{Raw}$','$Q_{Raw}$']).plot()

    # free resources
    camera.stop()
    camera.destroy()
