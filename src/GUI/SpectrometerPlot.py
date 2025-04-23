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

        #construct math ROIs
        widget = QtWidgets.QWidget()
        self.roi_controls = []
        self.roi_values = {}
        widget.setLayout(self.construct_ROI_input())
        #vbox.addChildLayout(self.construct_ROI_input())
        vbox.addWidget(widget)
        #widget.setLayout(self.construct_ROI_input)


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

        # empty array
        self.y ={}
        # connect events
        self.clear_button.clicked.connect(self.clear_plot)

    def construct_ROI_input(self):
        layout = QtWidgets.QVBoxLayout()
        grid_layout = QtWidgets.QGridLayout()

        for i in range(4):
            group = QtWidgets.QGroupBox(f"ROI{i+1}")
            hbox = QtWidgets.QHBoxLayout()

            min_spin = QtWidgets.QSpinBox()
            min_spin.setRange(0, 1000)
            min_spin.setValue(i * 63 + 26)

            max_spin = QtWidgets.QSpinBox()
            max_spin.setRange(0, 1000)
            max_spin.setValue(i * 63 + 36)

            hbox.addWidget(QtWidgets.QLabel("Min:"))
            hbox.addWidget(min_spin)
            hbox.addWidget(QtWidgets.QLabel("Max:"))
            hbox.addWidget(max_spin)
            group.setLayout(hbox)

            row = 0
            col = i
            grid_layout.addWidget(group, row, col)

            self.roi_controls.append((min_spin, max_spin))

        layout.addLayout(grid_layout)

        hbox_widget =QtWidgets.QWidget()
        hbox = QtWidgets.QHBoxLayout()
        self.input_line = QtWidgets.QLineEdit()
        self.input_line.setPlaceholderText("Enter math expression using ROI1 to ROI4")
        self.input_line.setText('np.ones(len(self.y[0])) - self.y[0]/self.y[3] - self.y[1]/self.y[3]')
        hbox.addWidget(self.input_line)
        self.input_line_range = QtWidgets.QLineEdit()
        self.input_line_range.setText("[0,1,2,3,4]")
        hbox.addWidget(self.input_line_range)
        hbox.addWidget(QtWidgets.QLabel("Binning:"))
        self.checkbox_bin = QtWidgets.QCheckBox()
        self.spinbox_bin = QtWidgets.QSpinBox()
        self.spinbox_bin.setValue(1)
        hbox.addWidget(self.checkbox_bin)
        hbox.addWidget(self.spinbox_bin)
        hbox.addWidget(QtWidgets.QLabel("Sum mode:"))
        self.checkbox_image = QtWidgets.QCheckBox()
        hbox.addWidget(self.checkbox_image)
        hbox.addWidget(QtWidgets.QLabel("show Limits:"))
        self.checkbox_limits = QtWidgets.QCheckBox()
        hbox.addWidget(self.checkbox_limits)
        hbox_widget.setLayout(hbox)
        layout.addWidget(hbox_widget)
        return layout

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
        wls_span = np.max(wls) - np.min(wls)
        for i in range (4):
            self.y[i] = np.average(spec[self.roi_controls[i][0].value():self.roi_controls[i][1].value(),:],axis=0)
            # 1 - R - T ; R = reflec/ref ; T = Trans/ref
        try:
            self.y[4] = eval(self.input_line.text())
        except KeyError:
            print('Incorrect expression, key out of range')
        except SyntaxError:
            print('Incorrect expression, syntax error')
        if spec.ndim == 1:
            self.graphWidget.plot(wls, spec, pen=QtGui.QColor.fromRgbF(plt.cm.prism(self.plotcounter)[0],plt.cm.prism(self.plotcounter)[1],
                                                                   plt.cm.prism(self.plotcounter)[2],plt.cm.prism(self.plotcounter)[3]))
        else:
            if not self.checkbox_image.isChecked():
                img =pg.ImageItem(np.transpose(spec))
                tr = QtGui.QTransform()  # prepare ImageItem transformation:
                tr.translate(np.min(wls), 0)  # move 3x3 image to locate center at axis origin
                tr.scale(wls_span / 1024, 1)
                img.setTransform(tr)
                self.graphWidget.clear()
                self.graphWidget.addItem(img)
                if self.checkbox_limits.isChecked():
                    print('checked')
                    for i in range(4):
                        y1 = self.roi_controls[i][0].value()
                        y2 = self.roi_controls[i][1].value()
                        self.graphWidget.addLine(x=None, y=y1)
                        self.graphWidget.addLine(x=None, y=y2)
            else:
                colors = [QtGui.QColor("red"), QtGui.QColor("green"), QtGui.QColor("blue"), QtGui.QColor("cyan"),QtGui.QColor("white")]
                plot_range = eval(self.input_line_range.text())
                for i in plot_range:
                    if self.checkbox_bin.isChecked():
                        self.graphWidget.plot(wls, self.do_binning(self.y[i]), pen=colors[i])
                    else:
                        self.graphWidget.plot(wls, self.y[i], pen=colors[i])
        self.plotcounter = self.plotcounter + 1
        if self.plotcounter > 100:
            self.clear_plot()
            print(time.strftime('%H:%M:%S') + ' Too many spectra in live plot, clear display for performance')
            self.plotcounter = 0

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




