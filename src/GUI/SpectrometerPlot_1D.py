from PyQt5 import QtWidgets, QtCore, QtGui
import pyqtgraph as pg
import numpy as np
import time
import matplotlib.pyplot as plt


class SpectrometerPlot(QtWidgets.QMainWindow):

    def __init__(self, *args, **kwargs):
        super(SpectrometerPlot, self).__init__(*args, **kwargs)

        # create Widgets for plot
        self.graphWidget = pg.PlotWidget()
        self.clear_button = QtWidgets.QPushButton('Clear')
        vbox = QtWidgets.QVBoxLayout()
        vbox.addWidget(self.clear_button)
        vbox.addWidget(self.graphWidget)
        widget = QtWidgets.QWidget()
        widget.setLayout(vbox)
        self.setCentralWidget(widget)
        styles = {'color':'#c8c8c8', 'font-size':'20px'}
        fontForTickValues = QtGui.QFont()
        fontForTickValues.setPixelSize(20)

        # set plot counter to clear if too many plots
        self.plotcounter = 0
        self.startplot_idx = 0

        # add firstplot for Acquire mode
        self.first_plot = True

        # create random example data set
        sigma = 40
        mu = 2
        wls = np.array(np.linspace(177.2218, 884.00732139, 512))
        spec = np.random.randint(0, 100, 512) + 20000./ (sigma * np.sqrt(2. * np.pi)) * np.exp(- (wls - mu - 620.) ** 2. / (2. * sigma ** 2.)) - 50,
        flatspec = np.array(spec)

        # plot data: x, y values
        self.graphWidget.plot(wls.reshape(-1), flatspec.reshape(-1),pen =pg.mkPen([200,200,200], width = 2))
        self.graphWidget.getAxis('left').setStyle(tickFont = fontForTickValues)
        self.graphWidget.getAxis('bottom').setStyle(tickFont = fontForTickValues)
        self.graphWidget.setLabel('left', 'Intensity (counts)', **styles)
        self.graphWidget.setLabel('bottom', 'Wavelength (nm)', **styles)
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

        # connect events
        self.clear_button.clicked.connect(self.clear_plot)

    @QtCore.pyqtSlot()
    def clear_plot(self):
        self.graphWidget.clear()
        self.startplot_idx = self.plotcounter
        # restore crosshair
        self.graphWidget.addItem(self.crosshair_v, ignoreBounds=True)
        self.graphWidget.addItem(self.crosshair_h, ignoreBounds=True)
        self.plotcounter = 0

    @QtCore.pyqtSlot(np.ndarray, np.ndarray)
    def set_data(self, wls, spec):
        #color = list(np.random.choice(range(256), size=3))
        self.graphWidget.plot(wls, spec, pen=QtGui.QColor.fromRgbF(plt.cm.prism(self.plotcounter)[0],plt.cm.prism(self.plotcounter)[1],
                                                                   plt.cm.prism(self.plotcounter)[2],plt.cm.prism(self.plotcounter)[3]))
        self.plotcounter = self.plotcounter + 1
        if self.plotcounter > 100:
            self.clear_plot()
            print(time.strftime('%H:%M:%S') + ' Too many spectra in live plot, clear display for performance')
            self.plotcounter = 0

    @QtCore.pyqtSlot(np.ndarray, np.ndarray)
    def set_data_preview(self, wls, spec):
        if not self.first_plot:
            self.graphWidget.removeItem(self.preview_plot)
        else:
            self.first_plot = False
        self.preview_plot = self.graphWidget.plot(wls, spec, pen=pg.mkPen([200,200,200], width = 1))

    def update_crosshair(self, e):
        pos = e[0]
        if self.graphWidget.sceneBoundingRect().contains(pos):
            mousePoint = self.graphWidget.getPlotItem().vb.mapSceneToView(pos)
            self.crosshair_v.setPos(mousePoint.x())
            self.crosshair_h.setPos(mousePoint.y())
        self.value_label.setText(f"Cursor: {mousePoint.x():.1f} nm {mousePoint.y():.1f} cts")

    @QtCore.pyqtSlot(np.ndarray)
    def update_datareader(self,max):
        self.maxvalue_label.setText(f"Data  : {max[2]:.1f} nm {max[1]:.1f} cts")




