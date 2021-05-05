from PyQt5 import uic
from PyQt5.QtCore import pyqtSlot, pyqtSignal, QRunnable, QThreadPool
from PyQt5.QtWidgets import QWidget, QDoubleSpinBox, QCheckBox

from deviceselectwidget import DeviceSelectWidget


class MeasureTask(QRunnable):

    def __init__(self, fn, end, token, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.end = end
        self.token = token
        self.args = args
        self.kwargs = kwargs

    def run(self):
        self.fn(self.token, *self.args, **self.kwargs)
        self.end()


class CancelToken:
    def __init__(self):
        self.cancelled = False


class MeasureWidget(QWidget):

    selectedChanged = pyqtSignal(int)
    sampleFound = pyqtSignal()
    measureComplete = pyqtSignal()
    measureStarted = pyqtSignal()

    def __init__(self, parent=None, controller=None):
        super().__init__(parent=parent)

        self._ui = uic.loadUi('measurewidget.ui', self)
        self._controller = controller
        self._threads = QThreadPool()

        self._devices = DeviceSelectWidget(parent=self, params=self._controller.deviceParams)
        self._ui.layParams.insertWidget(0, self._devices)
        self._devices.selectedChanged.connect(self.on_selectedChanged)

        self._selectedDevice = self._devices.selected

    def check(self):
        print('checking...')
        self._modeDuringCheck()
        self._threads.start(MeasureTask(self._controller.check,
                                        self.checkTaskComplete,
                                        self._selectedDevice))

    def checkTaskComplete(self):
        if not self._controller.present:
            print('sample not found')
            # QMessageBox.information(self, 'Ошибка', 'Не удалось найти образец, проверьте подключение')
            self._modePreCheck()
            return False

        print('found sample')
        self._modePreMeasure()
        self.sampleFound.emit()
        return True

    def measure(self):
        print('measuring...')
        self._modeDuringMeasure()
        self._threads.start(MeasureTask(self._controller.measure,
                                        self.measureTaskComplete,
                                        self._selectedDevice))

    def cancel(self):
        pass

    def measureTaskComplete(self):
        if not self._controller.hasResult:
            print('error during measurement')
            return False

        self._modePreCheck()
        self.measureComplete.emit()
        return True

    @pyqtSlot()
    def on_instrumentsConnected(self):
        self._modePreCheck()

    @pyqtSlot()
    def on_btnCheck_clicked(self):
        print('checking sample presence')
        self.check()

    @pyqtSlot()
    def on_btnMeasure_clicked(self):
        print('start measure')
        self.measureStarted.emit()
        self.measure()

    @pyqtSlot()
    def on_btnCancel_clicked(self):
        print('cancel click')
        self.cancel()

    @pyqtSlot(int)
    def on_selectedChanged(self, value):
        self._selectedDevice = value
        self.selectedChanged.emit(value)

    def _modePreConnect(self):
        self._ui.btnCheck.setEnabled(False)
        self._ui.btnMeasure.setEnabled(False)
        self._ui.btnCancel.setEnabled(False)
        self._devices.enabled = True

    def _modePreCheck(self):
        self._ui.btnCheck.setEnabled(True)
        self._ui.btnMeasure.setEnabled(False)
        self._ui.btnCancel.setEnabled(False)
        self._devices.enabled = True

    def _modeDuringCheck(self):
        self._ui.btnCheck.setEnabled(False)
        self._ui.btnMeasure.setEnabled(False)
        self._ui.btnCancel.setEnabled(False)
        self._devices.enabled = False

    def _modePreMeasure(self):
        self._ui.btnCheck.setEnabled(False)
        self._ui.btnMeasure.setEnabled(True)
        self._ui.btnCancel.setEnabled(False)
        self._devices.enabled = False

    def _modeDuringMeasure(self):
        self._ui.btnCheck.setEnabled(False)
        self._ui.btnMeasure.setEnabled(False)
        self._ui.btnCancel.setEnabled(True)
        self._devices.enabled = False

    def updateWidgets(self, params):
        raise NotImplementedError


class MeasureWidgetWithSecondaryParameters(MeasureWidget):
    secondaryChanged = pyqtSignal(dict)

    def __init__(self, parent=None, controller=None):
        super().__init__(parent=parent, controller=controller)

        self._token = CancelToken()

        self._params = 0

        # region LO params
        self._spinPlo = QDoubleSpinBox(parent=self)
        self._spinPlo.setMinimum(-30)
        self._spinPlo.setMaximum(30)
        self._spinPlo.setSingleStep(1)
        self._spinPlo.setValue(-5)
        self._spinPlo.setSuffix(' дБм')
        self._devices._layout.addRow('Pгет=', self._spinPlo)

        self._spinFloMin = QDoubleSpinBox(parent=self)
        self._spinFloMin.setMinimum(0)
        self._spinFloMin.setMaximum(40)
        self._spinFloMin.setSingleStep(1)
        self._spinFloMin.setValue(0.05)
        self._spinFloMin.setSuffix(' ГГц')
        self._devices._layout.addRow('Fгет.мин=', self._spinFloMin)

        self._spinFloMax = QDoubleSpinBox(parent=self)
        self._spinFloMax.setMinimum(0)
        self._spinFloMax.setMaximum(40)
        self._spinFloMax.setSingleStep(1)
        self._spinFloMax.setValue(3.05)
        self._spinFloMax.setSuffix(' ГГц')
        self._devices._layout.addRow('Fгет.макс=', self._spinFloMax)

        self._spinFloDelta = QDoubleSpinBox(parent=self)
        self._spinFloDelta.setMinimum(0)
        self._spinFloDelta.setMaximum(40)
        self._spinFloDelta.setSingleStep(0.1)
        self._spinFloDelta.setValue(0.5)
        self._spinFloDelta.setSuffix(' ГГц')
        self._devices._layout.addRow('ΔFгет=', self._spinFloDelta)
        # endregion LO

        # region RF params
        self._spinPrfMin = QDoubleSpinBox(parent=self)
        self._spinPrfMin.setMinimum(-30)
        self._spinPrfMin.setMaximum(30)
        self._spinPrfMin.setSingleStep(1)
        self._spinPrfMin.setValue(-20)
        self._spinPrfMin.setSuffix(' дБм')
        self._devices._layout.addRow('Pвх.мин=', self._spinPrfMin)

        self._spinPrfMax = QDoubleSpinBox(parent=self)
        self._spinPrfMax.setMinimum(-30)
        self._spinPrfMax.setMaximum(30)
        self._spinPrfMax.setSingleStep(1)
        self._spinPrfMax.setValue(6)
        self._spinPrfMax.setSuffix(' дБм')
        self._devices._layout.addRow('Pвх.макс=', self._spinPrfMax)

        self._spinPrfDelta = QDoubleSpinBox(parent=self)
        self._spinPrfDelta.setMinimum(-30)
        self._spinPrfDelta.setMaximum(30)
        self._spinPrfDelta.setSingleStep(1)
        self._spinPrfDelta.setValue(2)
        self._spinPrfDelta.setSuffix(' дБм')
        self._devices._layout.addRow('ΔPвх.=', self._spinPrfDelta)

        self._spinFrfMin = QDoubleSpinBox(parent=self)
        self._spinFrfMin.setMinimum(0)
        self._spinFrfMin.setMaximum(40)
        self._spinFrfMin.setSingleStep(1)
        self._spinFrfMin.setValue(0.06)
        self._spinFrfMin.setSuffix(' ГГц')
        self._devices._layout.addRow('Fвх.мин=', self._spinFrfMin)

        self._spinFrfMax = QDoubleSpinBox(parent=self)
        self._spinFrfMax.setMinimum(0)
        self._spinFrfMax.setMaximum(40)
        self._spinFrfMax.setSingleStep(1)
        self._spinFrfMax.setValue(3.06)
        self._spinFrfMax.setSuffix(' ГГц')
        self._devices._layout.addRow('Fвх.макс=', self._spinFrfMax)

        self._spinFrfDelta = QDoubleSpinBox(parent=self)
        self._spinFrfDelta.setMinimum(0)
        self._spinFrfDelta.setMaximum(40)
        self._spinFrfDelta.setSingleStep(0.1)
        self._spinFrfDelta.setValue(0.5)
        self._spinFrfDelta.setSuffix(' ГГц')
        self._devices._layout.addRow('ΔFвх.=', self._spinFrfDelta)
        # endregion

        # region source params
        self._spinUsrc = QDoubleSpinBox(parent=self)
        self._spinUsrc.setMinimum(4.75)
        self._spinUsrc.setMaximum(5.25)
        self._spinUsrc.setSingleStep(0.25)
        self._spinUsrc.setValue(5)
        self._spinUsrc.setSuffix(' В')
        self._devices._layout.addRow('Uпит.=', self._spinUsrc)
        # endregion

        # region calc params
        self._spinLoss = QDoubleSpinBox(parent=self)
        self._spinLoss.setMinimum(0)
        self._spinLoss.setMaximum(50)
        self._spinLoss.setSingleStep(1)
        self._spinLoss.setValue(5)
        self._spinLoss.setSuffix(' дБ')
        self._devices._layout.addRow('Пбал.=', self._spinLoss)
        # endregion

        # region SA params
        self._spinRefLevel = QDoubleSpinBox(parent=self)
        self._spinRefLevel.setMinimum(-20)
        self._spinRefLevel.setMaximum(20)
        self._spinRefLevel.setSingleStep(1)
        self._spinRefLevel.setValue(10)
        self._spinRefLevel.setSuffix(' дБ')
        self._devices._layout.addRow('Ref.level=', self._spinRefLevel)

        self._spinScaleY = QDoubleSpinBox(parent=self)
        self._spinScaleY.setMinimum(0)
        self._spinScaleY.setMaximum(50)
        self._spinScaleY.setSingleStep(1)
        self._spinScaleY.setValue(5)
        self._spinScaleY.setSuffix(' дБ')
        self._devices._layout.addRow('Scale y=', self._spinScaleY)
        # endregion

        self._connectSignals()

    def _connectSignals(self):
        self._spinPlo.valueChanged.connect(self.on_params_changed)
        self._spinFloMin.valueChanged.connect(self.on_params_changed)
        self._spinFloMax.valueChanged.connect(self.on_params_changed)
        self._spinFloDelta.valueChanged.connect(self.on_params_changed)

        self._spinPrfMin.valueChanged.connect(self.on_params_changed)
        self._spinPrfMax.valueChanged.connect(self.on_params_changed)
        self._spinPrfDelta.valueChanged.connect(self.on_params_changed)

        self._spinFrfMin.valueChanged.connect(self.on_params_changed)
        self._spinFrfMax.valueChanged.connect(self.on_params_changed)
        self._spinFrfDelta.valueChanged.connect(self.on_params_changed)

        self._spinUsrc.valueChanged.connect(self.on_params_changed)

        self._spinLoss.valueChanged.connect(self.on_params_changed)

        self._spinRefLevel.valueChanged.connect(self.on_params_changed)
        self._spinScaleY.valueChanged.connect(self.on_params_changed)

    def check(self):
        print('subclass checking...')
        self._modeDuringCheck()
        self._threads.start(
            MeasureTask(
                self._controller.check,
                self.checkTaskComplete,
                self._token,
                [self._selectedDevice, self._params]
            ))

    def checkTaskComplete(self):
        res = super(MeasureWidgetWithSecondaryParameters, self).checkTaskComplete()
        if not res:
            self._token = CancelToken()
        return res

    def measure(self):
        print('subclass measuring...')
        self._modeDuringMeasure()
        self._threads.start(
            MeasureTask(
                self._controller.measure,
                self.measureTaskComplete,
                self._token,
                [self._selectedDevice, self._params]
            ))

    def measureTaskComplete(self):
        res = super(MeasureWidgetWithSecondaryParameters, self).measureTaskComplete()
        if not res:
            self._token = CancelToken()
            self._modePreCheck()
        return res

    def cancel(self):
        if not self._token.cancelled:
            if self._threads.activeThreadCount() > 0:
                print('cancelling task')
            self._token.cancelled = True

    def on_params_changed(self, value):
        params = {
            'Plo': self._spinPlo.value(),
            'Flo_delta': self._spinFloDelta.value(),
            'Flo_max': self._spinFloMax.value(),
            'Flo_min': self._spinFloMin.value(),
            'Prf_delta': self._spinPrfDelta.value(),
            'Prf_max': self._spinPrfMax.value(),
            'Prf_min': self._spinPrfMin.value(),
            'Frf_delta': self._spinFrfDelta.value(),
            'Frf_max': self._spinFrfMax.value(),
            'Frf_min': self._spinFrfMin.value(),
            'Usrc': self._spinUsrc.value(),
            'loss': self._spinLoss.value(),
            'ref_lev': self._spinRefLevel.value(),
            'scale_y': self._spinScaleY.value(),
        }
        self.secondaryChanged.emit(params)

    def updateWidgets(self, params):
        self._spinPlo.setValue(params['Plo'])
        self._spinFloDelta.setValue(params['Flo_delta'])
        self._spinFloMax.setValue(params['Flo_max'])
        self._spinFloMin.setValue(params['Flo_min'])
        self._spinPrfDelta.setValue(params['Prf_delta'])
        self._spinPrfMax.setValue(params['Prf_max'])
        self._spinPrfMin.setValue(params['Prf_min'])
        self._spinFrfDelta.setValue(params['Frf_delta'])
        self._spinFrfMax.setValue(params['Frf_max'])
        self._spinFrfMin.setValue(params['Frf_min'])
        self._spinUsrc.setValue(params['Usrc'])
        self._spinLoss.setValue(params['loss'])
        self._spinRefLevel.setValue(params['ref_lev'])
        self._spinScaleY.setValue(params['scale_y'])