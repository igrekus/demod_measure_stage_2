import datetime
import os
import time

from subprocess import Popen

from PyQt5 import uic
from PyQt5.QtGui import QGuiApplication
from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot

from formlayout.formlayout import fedit
from instrumentcontroller import InstrumentController
from connectionwidget import ConnectionWidget
from measurewidget import MeasureWidgetWithSecondaryParameters
from primaryplotwidget import PrimaryPlotWidget


class MainWindow(QMainWindow):

    instrumentsFound = pyqtSignal()
    sampleFound = pyqtSignal()
    measurementFinished = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setAttribute(Qt.WA_QuitOnClose)
        self.setAttribute(Qt.WA_DeleteOnClose)

        # create instance variables
        self._ui = uic.loadUi('mainwindow.ui', self)
        self._instrumentController = InstrumentController(parent=self)
        self._connectionWidget = ConnectionWidget(parent=self, controller=self._instrumentController)
        self._measureWidget = MeasureWidgetWithSecondaryParameters(parent=self, controller=self._instrumentController)
        self._plotWidget = PrimaryPlotWidget(parent=self, controller=self._instrumentController)

        # init UI
        self._ui.layInstrs.insertWidget(0, self._connectionWidget)
        self._ui.layInstrs.insertWidget(1, self._measureWidget)

        self._ui.tabWidget.insertTab(0, self._plotWidget, 'Автоматическое измерение')

        self._init()

    def _init(self):
        self._connectionWidget.connected.connect(self.on_instrumens_connected)
        self._connectionWidget.connected.connect(self._measureWidget.on_instrumentsConnected)

        self._measureWidget.secondaryChanged.connect(self._instrumentController.on_secondary_changed)

        self._measureWidget.measureStarted.connect(self.on_measureStarted)
        self._measureWidget.measureComplete.connect(self.on_measureComplete)

        self._instrumentController.pointReady.connect(self.on_point_ready)

        self._measureWidget.updateWidgets(self._instrumentController.secondaryParams)
        self._measureWidget.on_params_changed(1)

    def _saveScreenshot(self):
        screen = QGuiApplication.primaryScreen()
        if not screen:
            print('error saving screenshot')
            return
        pixmap = screen.grabWindow(self.winId())

        device = 'demod'
        path = 'png'
        if not os.path.isdir(f'{path}'):
            os.makedirs(f'{path}')

        file_name = f'./{path}/{device}-{datetime.datetime.now().isoformat().replace(":", ".")}.png'
        pixmap.save(file_name)

        full_path = os.path.abspath(file_name)
        Popen(f'explorer /select,"{full_path}"')

    @pyqtSlot()
    def on_instrumens_connected(self):
        print(f'connected {self._instrumentController}')

    @pyqtSlot()
    def on_measureComplete(self):
        print('meas complete')
        self._plotWidget.plot()
        self._instrumentController.result.save_adjustment_template()

    @pyqtSlot()
    def on_measureStarted(self):
        self._plotWidget.clear()

    @pyqtSlot()
    def on_actParams_triggered(self):
        data = [
            ('Корректировка', self._instrumentController.result.adjust),
            ('Калибровка', self._instrumentController.cal_set),
            ('Только основные', self._plotWidget.only_main_states),
            ('Набор для коррекции', [1, '+25', '+85', '-60']),
        ]

        values = fedit(data=data, title='Параметры')
        if not values:
            return

        adjust, cal_set, only_main_states, adjust_set = values

        self._instrumentController.result.adjust = adjust
        self._instrumentController.result.adjust_set = adjust_set
        self._instrumentController.cal_set = cal_set
        self._instrumentController.only_main_states = only_main_states
        self._instrumentController.result.only_main_states = only_main_states
        self._plotWidget.only_main_states = only_main_states

    @pyqtSlot()
    def on_point_ready(self):
        self._ui.pteditProgress.setPlainText(self._instrumentController.result.report)
        self._plotWidget.plot()

    def closeEvent(self, _):
        self._instrumentController.saveConfigs()
        self._measureWidget.cancel()
        while self._measureWidget._threads.activeThreadCount() > 0:
            time.sleep(0.1)

    @pyqtSlot()
    def on_btnExcel_clicked(self):
        self._instrumentController.result.export_excel()

    @pyqtSlot()
    def on_btnScreenShot_clicked(self):
        self._saveScreenshot()
