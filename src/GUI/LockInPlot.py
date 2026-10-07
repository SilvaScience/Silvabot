import h5py
from PyQt5 import QtWidgets, QtCore, QtGui
import pyqtgraph as pg
import numpy as np
import time
import matplotlib.pyplot as plt
import h5py
import os
#from compute.TdepABS_Calibration import load_data



class LockInPlot(QtWidgets.QMainWindow):

    def __init__(self, *args, **kwargs):
        super(LockInPlot, self).__init__(*args, **kwargs)

        # create Widgets for plot
        self.graphWidget = pg.PlotWidget()
        graph_box = QtWidgets.QHBoxLayout()
        graph_box.addWidget(self.graphWidget)
        self.clear_button = QtWidgets.QPushButton('Clear')
        self.view_demod_button = QtWidgets.QPushButton('View Demodulator')
        vbox = QtWidgets.QVBoxLayout()
        vbox.addWidget(self.clear_button)
        vbox.addWidget(self.view_demod_button)

        #construct math ROIs


        #vbox.addWidget(self.graphWidget)
        graph_widget = QtWidgets.QWidget()
        graph_widget.setLayout(graph_box)
        vbox.addWidget(graph_widget)
        widget = QtWidgets.QWidget()
        widget.setLayout(vbox)
        self.setCentralWidget(widget)
        styles = {'color':'#c8c8c8', 'font-size':'20px'}
        fontForTickValues = QtGui.QFont()
        fontForTickValues.setPixelSize(20)


        # create random example data set
        sigma = 40
        mu = 2
        wls = np.array(np.linspace(177.2218, 884.00732139, 512))
        spec = np.random.randint(0, 100, 512) + 20000./ (sigma * np.sqrt(2. * np.pi)) * np.exp(- (wls - mu - 620.) ** 2. / (2. * sigma ** 2.)) - 50,
        flatspec = np.array(spec)

        # plot data: x, y values
        self.graphWidget.plot(wls.reshape(-1), flatspec.reshape(-1),pen =pg.mkPen([200,200,200], width = 2))
        self.graphWidget.setAxisItems(axisItems={'bottom': pg.DateAxisItem()})
        self.graphWidget.getAxis('left').setStyle(tickFont = fontForTickValues)
        self.graphWidget.getAxis('bottom').setStyle(tickFont = fontForTickValues)
        self.graphWidget.setLabel('left', 'Amplitude (nV)', **styles)
        self.graphWidget.setLabel('bottom', 'Time (s)', **styles)
        self.graphWidget.showGrid(True,True)

        # add cross hair
        cursor = QtCore.Qt.CrossCursor
        self.graphWidget.setCursor(cursor) #set Blank Cursor
        self.crosshair_v = pg.InfiniteLine(angle=90, movable=False)
        self.crosshair_h = pg.InfiniteLine(angle=0, movable=False)
        self.graphWidget.addItem(self.crosshair_v, ignoreBounds=True)
        self.graphWidget.addItem(self.crosshair_h, ignoreBounds=True)

        # set proxy for Mouse movement
        self.proxy = pg.SignalProxy(self.graphWidget.scene().sigMouseMoved, rateLimit=60, slot=self.update_crosshair)

        # add value reader
        self.value_label = pg.LabelItem('Move Cursor', **{'color':'#c8c8c8', 'size':'20pt'})
        self.value_label.setParentItem(self.graphWidget.getPlotItem())
        self.value_label.anchor(itemPos=(1,0), parentPos=(1,0), offset=(-50,10))
        self.maxvalue_label = pg.LabelItem('No Data', **{'color':'#c8c8c8', 'size':'20pt'})
        self.maxvalue_label.setParentItem(self.graphWidget.getPlotItem())
        self.maxvalue_label.anchor(itemPos=(1,0), parentPos=(1,0), offset=(-50,35))

        # empty array
        self.y = {}
        self.wls = []

        # connect events
        self.clear_button.clicked.connect(self.clear_plot)


    @QtCore.pyqtSlot()
    def clear_plot(self):
        self.graphWidget.clear()
        # restore crosshair
        self.graphWidget.addItem(self.crosshair_v, ignoreBounds=True)
        self.graphWidget.addItem(self.crosshair_h, ignoreBounds=True)


    @QtCore.pyqtSlot(np.ndarray,np.ndarray)
    def set_data(self,t_array, r_array):
        self.clear_plot()
        self.graphWidget.plot(t_array, r_array)


    def do_binning(self, spectrum):
        """ Manual binning of the spectra. Some cameras might allow to readout pixel together to increase
        signal-to-noise at the cost of lower resolution. """
        #print(spectrum)
        spec_length = len(spectrum)
        binned_spec = np.empty(len(spectrum))
        binning = self.spinbox_bin.value()
        for i in range(spec_length):
            if i > spec_length - binning:
                binned_spec[i] = np.sum(spectrum[spec_length - binning:spec_length])
            elif i < binning:
                binned_spec[i] = np.sum(spectrum[0:i])
            else:
                binned_spec[i] = np.sum(spectrum[i - binning + 1:i + binning])
        return binned_spec/(2 * (binning - 1) + 1)

    def update_crosshair(self, e):
        pos = e[0]
        if self.graphWidget.sceneBoundingRect().contains(pos):
            mousePoint = self.graphWidget.getPlotItem().vb.mapSceneToView(pos)
            self.crosshair_v.setPos(mousePoint.x())
            self.crosshair_h.setPos(mousePoint.y())
        calibration_mode = False
        if calibration_mode:
            try:
                pixel = np.argmin(abs(self.wls - mousePoint.x()))
                self.value_label.setText(f"Cursor: {mousePoint.x():.1f} s {mousePoint.y():.1f} nV {pixel:.0f} pixel")
            except TypeError:
                print('Cursor deactivated, waiting for first data.')
        else:
            self.value_label.setText(f"Cursor: {mousePoint.x():.1f} s {mousePoint.y():.1f} nV")
