from PyQt5 import uic
from PyQt5.QtWidgets import QWidget


class InstrumentWidget(QWidget):

    def __init__(self, parent=None, title='stub', addr='stub'):
        super().__init__(parent=parent)

        self._ui = uic.loadUi('instrumentwidget.ui', self)

        self.title = title
        self.address = addr
        self.status = 'нет подключения'

    @property
    def title(self):
        return self._ui.label.text()
    @title.setter
    def title(self, value):
        self._ui.label.setText(value)

    @property
    def address(self):
        return self._ui.editAddress.text()
    @address.setter
    def address(self, value):
        self._ui.editAddress.setText(value)

    @property
    def status(self):
        return self._ui.editStatus.text()
    @status.setter
    def status(self, value):
        self._ui.editStatus.setText(value)
