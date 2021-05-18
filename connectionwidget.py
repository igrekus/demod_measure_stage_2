from PyQt5 import uic
from PyQt5.QtCore import pyqtSlot, pyqtSignal, QRunnable, QThreadPool
from PyQt5.QtWidgets import QWidget

from instrumentwidget import InstrumentWidget


class ConnectTask(QRunnable):

    def __init__(self, fn, end, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.end = end
        self.args = args
        self.kwargs = kwargs

    def run(self):
        self.fn(*self.args, **self.kwargs)
        self.end()


class ConnectionWidget(QWidget):

    connected = pyqtSignal()

    def __init__(self, parent=None, controller=None):
        super().__init__(parent=parent)

        self._ui = uic.loadUi('connectionwidget.ui', self)
        self._controller = controller
        self._threads = QThreadPool()

        self._widgets = {
            k: InstrumentWidget(parent=self, title=f'{k}', addr=f'{v.addr}')
            for k, v in self._controller.requiredInstruments.items()
        }

        self._setupUi()

    def _setupUi(self):
        for i, iw in enumerate(self._widgets.items()):
            self._ui.layInstruments.insertWidget(i, iw[1])

    @pyqtSlot()
    def on_btnConnect_clicked(self):
        print('connect')

        self._threads.start(ConnectTask(self._controller.connect,
                                        self.connectTaskComplete,
                                        {k: w.address for k, w in self._widgets.items()}))

    @pyqtSlot(bool)
    def on_grpInstruments_toggled(self, state):
        self._ui.widgetContainer.setVisible(state)

    def connectTaskComplete(self):
        if not self._controller.found:
            print('connect error, check connection')
            return

        for w, s in zip(self._widgets.values(), self._controller.status):
            w.status = s
        self.connected.emit()
