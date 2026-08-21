from PyQt5 import QtWidgets, QtCore, QtGui
import pyqtgraph as pg
import numpy as np
import time


class ParameterPlot(QtWidgets.QMainWindow):

    send_idx_change = QtCore.pyqtSignal(int, int)
    send_parameter_filename = QtCore.pyqtSignal(str)

    def __init__(self, parameter_dict, *args, **kwargs):
        super(ParameterPlot, self).__init__(*args, **kwargs)
        self.parameter_dict = parameter_dict
        self.unit_list = ['s','h']
        self.display_unit = 'unit'

        # create Widgets for plot
        self.graphWidget = pg.PlotWidget()
        self.clear_button = QtWidgets.QPushButton('Clear')
        self.update_button = QtWidgets.QPushButton('Update')
        self.save_button = QtWidgets.QPushButton('Save Parameter')
        self.x_axis_button = QtWidgets.QComboBox()
        self.y_axis_button = QtWidgets.QComboBox()
        x_label = QtWidgets.QLabel('X Axis')
        y_label = QtWidgets.QLabel('Y Axis')
        hbox = QtWidgets.QHBoxLayout()
        hbox.addWidget(self.x_axis_button)
        hbox.addWidget(x_label)
        hbox.addSpacing(30)
        hbox.addWidget(self.y_axis_button)
        hbox.addWidget(y_label)
        hbox.addSpacing(30)
        hbox.addWidget(self.save_button)
        vbox = QtWidgets.QVBoxLayout()
        vbox.addWidget(self.update_button)
        vbox.addWidget(self.clear_button)
        vbox.addLayout(hbox)
        vbox.addWidget(self.graphWidget)
        widget = QtWidgets.QWidget()
        widget.setLayout(vbox)
        self.setCentralWidget(widget)
        self.styles = {'color':'#c8c8c8', 'font-size':'20px'}
        self.fontForTickValues = QtGui.QFont()
        self.fontForTickValues.setPixelSize(20)


        # fill QComboBoxes
        self.x_axis_button.addItem('time')
        self.y_axis_button.addItem('time')
        self.x_axis_button.addItem('absolute_time')
        self.y_axis_button.addItem('absolute_time')
        for devices in self.parameter_dict.keys():
            for param in self.parameter_dict[devices].keys():
                self.x_axis_button.addItem(param)
                self.y_axis_button.addItem(param)
                self.unit_list.append(self.parameter_dict[devices][param]['unit'][1:])
            #print(self.unit_list)

        # set plot counter to clear if too many plots
        self.plotcounter = 0
        self.startplot_idx = 0


        # plot data: x, y values
        self.graphWidget.getAxis('left').setStyle(tickFont=self.fontForTickValues)
        self.graphWidget.getAxis('bottom').setStyle(tickFont=self.fontForTickValues)
        self.graphWidget.setLabel('left', 'Temperature (K)', **self.styles)
        self.graphWidget.setLabel('bottom', 'Time (s)', **self.styles)
        self.graphWidget.showGrid(True, True)
        self.x_axis_button.setStyleSheet("background-color : white")
        self.y_axis_button.setStyleSheet("background-color : white")

        # add value display
        self.value_label = pg.LabelItem('Current', **{'color':'#c8c8c8', 'size':'60pt'})
        self.value_label.setParentItem(self.graphWidget.getPlotItem())
        self.value_label.anchor(itemPos=(1,0), parentPos=(1,0), offset=(-50,10))


        # connect events
        self.clear_button.clicked.connect(self.clear_plot)
        self.update_button.clicked.connect(self.update_plot)
        self.save_button.clicked.connect(self.save_parameter)

        # update plot to initialize axis
        self.update_plot()

    @QtCore.pyqtSlot()
    def clear_plot(self):
        self.graphWidget.clear()
        self.startplot_idx = self.plotcounter

    @QtCore.pyqtSlot(np.ndarray, np.ndarray)
    def set_data(self, x_array, y_array):
        self.graphWidget.clear()
        self.graphWidget.plot(x_array[self.startplot_idx:],y_array[self.startplot_idx:])
        self.plotcounter = self.plotcounter + 1
        try:
            self.value_label.setText(f'Current: {y_array[-1]:,.1f} ' + self.display_unit)
        except:
            pass

    def update_plot(self):
        if self.x_axis_button.currentText() == 'absolute_time':
            self.graphWidget.setAxisItems(axisItems={'bottom': pg.DateAxisItem()})
            self.graphWidget.setLabel('bottom', 'Time (s)', **self.styles)
            self.graphWidget.getAxis('bottom').setStyle(tickFont=self.fontForTickValues)
        else:
            self.graphWidget.setAxisItems(axisItems={'bottom': pg.AxisItem(orientation='bottom')})
            self.graphWidget.getAxis('bottom').setStyle(tickFont=self.fontForTickValues)
        self.graphWidget.setLabel('left', self.y_axis_button.currentText().capitalize() +
                                  ' (' + self.unit_list[self.y_axis_button.currentIndex()] + ')', **self.styles)
        self.graphWidget.setLabel('bottom', self.x_axis_button.currentText().capitalize() +
                                  ' (' + self.unit_list[self.x_axis_button.currentIndex()] + ')', **self.styles)
        self.display_unit = self.unit_list[self.y_axis_button.currentIndex()]
        self.send_idx_change.emit(self.x_axis_button.currentIndex(), self.y_axis_button.currentIndex())

    def save_parameter(self):
        save_parameter_filename = QtWidgets.QFileDialog.getSaveFileName(self, 'Select parameter save name',
                                                                        filter='*')
        self.send_parameter_filename.emit(save_parameter_filename[0])






