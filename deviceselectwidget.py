from PyQt5.QtCore import pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QWidget, QComboBox, QFormLayout


class DeviceSelectWidget(QWidget):

    selectedChanged = pyqtSignal(str)

    def __init__(self, parent=None, params=None):
        super().__init__(parent=parent)

        self._layout = QFormLayout()
        self._combo = QComboBox()

        for i, label in enumerate(params.keys()):
            self._combo.addItem(label)

        self._layout.addRow('Прибор', self._combo)

        self.setLayout(self._layout)

        self._combo.setCurrentIndex(0)
        self._combo.currentTextChanged.connect(self.on_textChanged)

        self._enabled = True

    @property
    def selected(self):
        return self._combo.currentText()

    @pyqtSlot(str)
    def on_textChanged(self, text):
        self.selectedChanged.emit(text)

    @property
    def enabled(self):
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool):
        self._enabled = value
        self._combo.setEnabled(value)
