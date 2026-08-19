import h5py
from PyQt5 import QtWidgets, QtCore, QtGui
import pyqtgraph as pg
import numpy as np
import time
import matplotlib.pyplot as plt
import h5py
import os
#from compute.TdepABS_Calibration import load_data



class SpectrometerPlot(QtWidgets.QMainWindow):

    """ Emitted when the readout region is dragged in the sensor view, as (y0, height). This widget
    has no access to the parameter tree -- main.py connects this to the same path a typed change to
    roi_y0/roi_height takes, so the drag and the tree stay one setting rather than two. """
    readout_region_changed = QtCore.pyqtSignal(int, int)

    def __init__(self, *args, **kwargs):
        super(SpectrometerPlot, self).__init__(*args, **kwargs)

        # create Widgets for plot
        self.graphWidget = pg.PlotWidget()
        self.hist = pg.HistogramLUTItem()
        self.img = pg.ImageItem()
        hist_view = pg.GraphicsLayoutWidget()
        hist_view.addItem(self.hist)
        hist_view.setMaximumWidth(80)

        """ Live sensor view, for cameras that can read their full 2D frame as well as an on-chip
        binned region (currently PixisDecoupled: set_full_frame/set_binned_roi). It reuses the
        ImageItem and histogram already above rather than adding a panel, so the layout is
        unchanged, and stays hidden for every camera that doesn't support it -- see
        set_spectrometer(). The readout region itself is NOT set here: it lives in the Hardware
        parameter tree as roi_y0/roi_height, like int_time. This view only shows where to put it,
        and dragging writes back into those parameters. """
        self.spectrometer = None
        self.sensor_height = None
        """ Set by main.py to callables reading/writing its measurement_busy flag -- the same gate
        every hardware-touching action goes through, so the sensor view can't stream while a real
        measurement uses the same camera, or vice versa. None until main.py wires them up. """
        self.is_busy = None
        self.set_busy = None
        self.bin_region = pg.LinearRegionItem(orientation='horizontal', movable=True)
        self.bin_region.setVisible(False)
        self.bin_region.sigRegionChangeFinished.connect(self._on_bin_region_changed)
        self._live_frame_shape = None  # forces one autoLevels pass on the first frame of a session
        graph_box = QtWidgets.QHBoxLayout()
        graph_box.addWidget(self.graphWidget)
        graph_box.addWidget(hist_view)
        self.graphWidget.addItem(self.img)
        self.graphWidget.addItem(self.bin_region, ignoreBounds=True)
        self.hist.setImageItem(self.img)
        self.clear_button = QtWidgets.QPushButton('Clear')
        self.bg_button = QtWidgets.QPushButton('Select Background')
        self.checkbox_bg = QtWidgets.QCheckBox()
        vbox = QtWidgets.QVBoxLayout()
        bg_hbox = QtWidgets.QHBoxLayout()
        bg_hbox.addWidget(self.bg_button)
        bg_hbox.addWidget(QtWidgets.QLabel("Correct background:"))
        bg_hbox.addWidget(self.checkbox_bg)
        bg_widget = QtWidgets.QWidget()
        bg_widget.setLayout(bg_hbox)
        vbox.addWidget(self.clear_button)
        vbox.addWidget(bg_widget)

        #construct math ROIs
        widget = QtWidgets.QWidget()
        self.roi_controls = []
        self.roi_values = {}
        widget.setLayout(self.construct_ROI_input())
        #vbox.addChildLayout(self.construct_ROI_input())
        vbox.addWidget(widget)
        #widget.setLayout(self.construct_ROI_input)


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
        self.y = {}
        self.wls = []

        # Empty array to store the reference values
        self.y_ref = {}
        self.y_calib = {}

        # connect events
        self.clear_button.clicked.connect(self.clear_plot)
        self.bg_button.clicked.connect(self.load_background)

    def set_spectrometer(self, spectrometer):
        """
            Shows the camera mode button when the given spectrometer can read both its full 2D frame
            and an on-chip binned region, and can stream live frames (currently PixisDecoupled).
            Called once from main.py after devices are loaded. For any other spectrometer the button
            stays hidden and nothing about this widget changes.
        """
        self.spectrometer = spectrometer
        capable = (spectrometer is not None
                   and hasattr(spectrometer, 'set_binned_roi')
                   and hasattr(spectrometer, 'set_full_frame')
                   and hasattr(spectrometer, 'get_roi')
                   and hasattr(spectrometer, 'worker'))
        self.camera_mode_button.setVisible(capable)
        if capable:
            self.sensor_height = int(getattr(spectrometer, 'sensor_height', 4096))
            y0, height, _ = spectrometer.get_roi()
            self.set_region_display(y0, height)

    def set_region_display(self, y0, height):
        """ Moves the visual region without echoing back out as a drag. Called from
            set_spectrometer() and from main.py whenever roi_y0/roi_height change in the tree, so
            the region on screen always shows the region the camera actually has. """
        self.bin_region.blockSignals(True)
        self.bin_region.setRegion((y0, y0 + height))
        self.bin_region.blockSignals(False)

    def _on_bin_region_changed(self):
        """ Slot for bin_region.sigRegionChangeFinished -- fires once per drag gesture, not
            continuously while dragging. Emits rather than driving the camera directly: the readout
            region is a hardware parameter, and it takes the same route whether it was dragged here
            or typed into the parameter tree. """
        y0, y1 = self.bin_region.getRegion()
        self.readout_region_changed.emit(int(round(y0)), max(int(round(y1 - y0)), 1))

    def toggle_camera_mode(self, checked):
        """
            Slot for camera_mode_button. Pressed, the camera reads its full frame and streams it
            here live, so the signal's position on the slit is visible. Released, the camera returns
            to the binned readout region held in roi_y0/roi_height.

            The view only shows: it never applies a region of its own. Dragging goes through
            readout_region_changed like any other change to those parameters, so closing the view
            can't silently apply something that was never asked for.
        """
        if self.spectrometer is None:
            return
        if checked:
            if self.is_busy is not None and self.is_busy():
                """ Refuse to touch the camera while a real measurement is using it -- switching to
                full frame here would reconfigure the readout out from under it. Revert the button
                without re-entering this slot (setChecked(False) would otherwise fire toggled(False)
                and run the release branch for a mode never actually entered). """
                print('Sensor view not opened: a measurement is currently using this device.')
                self.camera_mode_button.blockSignals(True)
                self.camera_mode_button.setChecked(False)
                self.camera_mode_button.blockSignals(False)
                return
            self.camera_mode_button.setText('Camera: 2D')
            self.img.setVisible(True)
            self.bin_region.setVisible(True)
            self._live_frame_shape = None
            self.spectrometer.set_full_frame()
            self.spectrometer.worker.sendSpectrum.connect(self.set_live_frame)
            self.spectrometer.start_acquisition()
            """ Locks the Y-axis to the sensor's row range. Left on auto-range it keeps whatever the
            previous 1D plot set (intensity counts, unrelated to row index), which squeezes the image
            into a sliver and puts the region nowhere near where a drag needs to land. """
            self.graphWidget.getViewBox().disableAutoRange(axis=pg.ViewBox.YAxis)
            self.graphWidget.setYRange(0, self.sensor_height or 256, padding=0)
            # Busy for as long as the view streams, so a measurement started elsewhere in the GUI is
            # rejected instead of running concurrently on this camera.
            if self.set_busy is not None:
                self.set_busy(True)
        else:
            self.camera_mode_button.setText('Camera: 1D')
            self.spectrometer.stop_acquisition()
            try:
                self.spectrometer.worker.sendSpectrum.disconnect(self.set_live_frame)
            except TypeError:
                pass  # already disconnected
            self.bin_region.setVisible(False)
            self.img.setVisible(False)
            self.graphWidget.getViewBox().enableAutoRange(axis=pg.ViewBox.YAxis)
            # Re-applies roi_y0/roi_height, which full-frame was temporarily overriding.
            self.spectrometer.apply_readout_region()
            if self.set_busy is not None:
                self.set_busy(False)

    @QtCore.pyqtSlot(np.ndarray, float)
    def set_live_frame(self, frame, int_time):
        """
            Live feed connected straight to the camera worker while the sensor view is open. Kept
            separate from set_data()/DataHandling on purpose -- this frame was never requested as a
            measurement and must never be saved or counted as one.
        """
        if frame.ndim < 2:
            return
        """ Without this the image keeps ImageItem's identity transform and is plotted against raw
        pixel index on an axis labelled nm. Recomputed every frame (cheap) rather than cached, since
        the calibration follows the monochromator and can change while the view is open. """
        if hasattr(self.spectrometer, 'get_wavelength'):
            wls = self.spectrometer.get_wavelength()
            wls_span = np.max(wls) - np.min(wls)
            tr = QtGui.QTransform()
            tr.translate(np.min(wls), 0)
            tr.scale(wls_span / len(wls), 1)
            self.img.setTransform(tr)
        auto = frame.shape != self._live_frame_shape
        self._live_frame_shape = frame.shape
        if auto:
            self.img.setImage(np.transpose(frame), autoLevels=True)
            self.hist.setLevels(*self.img.getLevels())
        else:
            self.img.setImage(np.transpose(frame), autoLevels=False, levels=self.hist.getLevels())

    def load_background(self):
        data_path = QtWidgets.QFileDialog.getOpenFileName()[0]
        with h5py.File(data_path, 'r') as f:
            bg_spec = f['spectra'][:]
            self.bg_xaxis = f['spectra'].attrs['xaxis']
            if bg_spec.ndim == 2:
                self.bg_spec = np.average(bg_spec[:, :], axis=1)
            else:
                self.bg_spec = np.average(bg_spec[1:,:,:],axis=0)



    def construct_ROI_input(self):
        layout = QtWidgets.QVBoxLayout()
        grid_layout = QtWidgets.QGridLayout()

        for i in range(4):
            group = QtWidgets.QGroupBox(f"ROI{i}")
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
        self.input_line.setPlaceholderText("Enter math expression using ROI0 to ROI3")
        self.input_line.setText('y[0]-y[1]') #'np.ones(len(self.y[0])) - self.y[0]/self.y[3] - self.y[1]/self.y[3]'
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

        # New line added to run the load_data function when load_ref_button is clicked.
        self.load_ref_button.clicked.connect(self.load_data)
        self.load_calib_button.clicked.connect(self.load_calib)

    def construct_ROI_input(self):
        layout = QtWidgets.QVBoxLayout()
        grid_layout = QtWidgets.QGridLayout()

        for i in range(4):
            group = QtWidgets.QGroupBox(f"ROI{i}")
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
        self.input_line.setPlaceholderText("Enter math expression using ROI0 to ROI3")
        self.input_line.setText('y[0]-y[1]') #'np.ones(len(self.y[0])) - self.y[0]/self.y[3] - self.y[1]/self.y[3]'
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
        """ A button rather than another checkbox on purpose: the two neighbours above are display
        choices about data already acquired, this one changes what the camera reads out. Its label
        names the camera's current state so the two can't be confused. Hidden unless the camera
        supports it (set_spectrometer), so nothing changes for any other experiment. """
        self.camera_mode_button = QtWidgets.QPushButton('Camera: 1D')
        self.camera_mode_button.setCheckable(True)
        self.camera_mode_button.setVisible(False)
        self.camera_mode_button.setToolTip(
            "Show the live 2D sensor frame, to see where the signal sits on the slit.\n"
            "Drag the horizontal region to set the camera's readout region -- the same\n"
            "roi_y0/roi_height shown under Hardware. Press again to return to 1D.")
        self.camera_mode_button.toggled.connect(self.toggle_camera_mode)
        hbox.addWidget(self.camera_mode_button)
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
        self.graphWidget.addItem(self.img)
        self.plotcounter = 0

    # New functions that allow to load reference and calibration data
    def load_data(self):
        self.data_path = QtWidgets.QFileDialog.getOpenFileName(self)[0]
        with h5py.File(self.data_path, 'r') as f:
            self.ref_spec = f['spectra']
            self.ref_wl = f['spectra'].attrs['xaxis']
            self.avg_ref_spec = np.average(self.ref_spec[5:,:,:], axis=0)
    
    def load_calib(self):
        self.folder_path = QtWidgets.QFileDialog.getExistingDirectory(self)

    def load_spectra(self):
        self.spectra = {}
        with h5py.File(self.path, 'r') as f:
            self.spec = f['spectra']
            self.wl = f['spectra'].attrs['xaxis']
            self.avg_spec = np.average(self.spec[5:,:,:], axis=0)
            for i in range(len(self.lim1)):
                self.spectra[i] = np.average(self.avg_spec[self.lim1[i]:self.lim2[i], :], axis=0)

    def gen_calib_spectra(self):
        # Initialize variables
        calib_spectra = []
        self.lim1 = [220, 140, 80, 30]
        self.lim2 = [230, 150, 90, 40]
        file_paths = []
        data_dict = {i: [] for i in range(len(self.lim1))}
        wl_min = float('inf')
        wl_max = float('-inf')

        # Create a list of file paths
        for file_name in sorted(os.listdir(self.folder_path)):
            if file_name.endswith('.h5'):
                file_paths.append(os.path.join(self.folder_path, file_name))

        # Place all the data in a dictionary and create a list of all the wavelengths in the loaded files
        for path in file_paths:
            self.path = path
            self.load_spectra()
            for i in range(len(self.lim1)):
                data_dict[i].append((self.wl, self.spectra[i]))
            wl_min = min(wl_min, np.min(self.wl))
            wl_max = max(wl_max, np.max(self.wl))
        nb_points = int(1024 * (wl_max - wl_min)/(max(self.wls) - min(self.wls)))
        wl_axis = np.linspace(wl_min, wl_max, nb_points)

        # Interpolate and average
        for i, spectra_list in data_dict.items():
            interpolated_spectra = []
            for wl, spec in spectra_list:
                mask = (wl_axis >= wl[0]) & (wl_axis <= wl[-1])
                interpolated = np.full_like(wl_axis, np.nan)
                interpolated[mask] = np.interp(wl_axis[mask], wl, spec)
                interpolated_spectra.append(interpolated)
            combined_spectra = np.nanmean(interpolated_spectra, axis=0)
            calib_spectra.append(combined_spectra)
    
        # Find the appropriate section of the data to use based on the minimum measured wavelength (linked to the center wavelength)
        difference_array = np.absolute(wl_axis - min(self.wls))
        index = difference_array.argmin()

        # Define the calibration arrays
        self.y_calib[0] = calib_spectra[0][index:index+1024]
        self.y_calib[1] = calib_spectra[1][index:index+1024]
        self.y_calib[2] = calib_spectra[1][index:index+1024]
        self.y_calib[3] = calib_spectra[3][index:index+1024]
    

    @QtCore.pyqtSlot(np.ndarray, np.ndarray)
    def set_data(self, wls, spec):
        self.wls = wls
        wls_span = np.max(wls) - np.min(wls)

        if spec.ndim > 1:
            for i in range (4):
                lim1 = self.roi_controls[i][0].value()
                lim2 = self.roi_controls[i][1].value()
                if lim2 > lim1:
        # Added/Modified section : The average between lim1 and lim2 is now calculated for the reference data
        # and the gen_calib_spectra function is used to do the same for the calibration data.
                    try:
                        ref = np.average(self.avg_ref_spec[lim1:lim2,:],axis=0)
                    except(AttributeError, TypeError):
                        ref = np.zeros(len(wls))
                    self.y_ref[i] = ref

                    try:
                        if i == 0:
                            self.gen_calib_spectra()
                    except(AttributeError, TypeError):
                        self.y_calib[i] = np.zeros(len(wls))
                    self.y[i] = np.average(spec[lim1:lim2,:],axis=0)

                else:
                    self.y[i] = spec[self.roi_controls[i][0].value()]
            # Arrange arrays for usage in 'eval' expression
            try:
                y = self.y
                y_ref = self.y_ref
                y_calib = self.y_calib
                self.y[4] = eval(self.input_line.text())
            except KeyError:
                print('Incorrect expression, key out of range')
            except SyntaxError:
                print('Incorrect expression, syntax error')

        if self.checkbox_bg.isChecked():
            spec = spec - self.bg_spec
        self.wls = wls
        wls_span = np.max(wls) - np.min(wls)
        if spec.ndim == 1:
            self.graphWidget.plot(wls, spec, pen=QtGui.QColor.fromRgbF(plt.cm.prism(self.plotcounter)[0],plt.cm.prism(self.plotcounter)[1],
                                                                   plt.cm.prism(self.plotcounter)[2],plt.cm.prism(self.plotcounter)[3]))
        else:
            for i in range(4):
                lim1 = self.roi_controls[i][0].value()
                lim2 = self.roi_controls[i][1].value()
                if lim2 > lim1:
                    self.y[i] = np.average(spec[lim1:lim2, :], axis=0)
                else:
                    self.y[i] = spec[self.roi_controls[i][0].value()]
                # 1 - R - T ; R = reflec/ref ; T = Trans/ref
            try:
                y = self.y
                self.y[4] = eval(self.input_line.text())
            except KeyError:
                print('Incorrect expression, key out of range')
            except SyntaxError:
                print('Incorrect expression, syntax error')
            if not self.checkbox_image.isChecked():
                #img =pg.ImageItem(np.transpose(spec))
                levels = self.hist.getLevels()
                self.img.setImage(np.transpose(spec), autoLevels=False, levels=levels)
                tr = QtGui.QTransform()  # prepare ImageItem transformation:
                tr.translate(np.min(wls), 0)  # move 3x3 image to locate center at axis origin
                tr.scale(wls_span / len(wls), 1)
                self.img.setTransform(tr)
                #self.hist.setImageItem(self.img)
                #self.graphWidget.clear()
                #self.graphWidget.addItem(self.img)
                if self.checkbox_limits.isChecked():
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
        calibration_mode = False
        if calibration_mode:
            try:
                pixel = np.argmin(abs(self.wls - mousePoint.x()))
                self.value_label.setText(f"Cursor: {mousePoint.x():.1f} nm {mousePoint.y():.1f} cts {pixel:.0f} pixel")
            except TypeError:
                print('Cursor deactivated, waiting for first data.')
        else:
            self.value_label.setText(f"Cursor: {mousePoint.x():.1f} nm {mousePoint.y():.1f} cts")

    @QtCore.pyqtSlot(np.ndarray)
    def update_datareader(self,max):
        self.maxvalue_label.setText(f"Data  : {max[2]:.1f} nm {max[1]:.1f} cts")