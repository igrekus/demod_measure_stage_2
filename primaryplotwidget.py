import pyqtgraph as pg

from PyQt5.QtWidgets import QGridLayout, QWidget, QLabel
from PyQt5.QtCore import Qt


# https://www.learnpyqt.com/tutorials/plotting-pyqtgraph/
# https://pyqtgraph.readthedocs.io/en/latest/introduction.html#what-is-pyqtgraph

colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']


class PrimaryPlotWidget(QWidget):
    label_style = {'color': 'k', 'font-size': '15px'}

    def __init__(self, parent=None, controller=None):
        super().__init__(parent)

        self._controller = controller   # TODO decouple from controller, use explicit result passing
        self.only_main_states = False

        self._grid = QGridLayout()

        self._win = pg.GraphicsLayoutWidget(show=True)
        self._win.setBackground('w')

        self._stat_label = QLabel('Mouse position:')
        self._stat_label.setAlignment(Qt.AlignRight)

        self._grid.addWidget(self._stat_label, 0, 0)
        self._grid.addWidget(self._win, 1, 0)

        self._plot_00 = self._win.addPlot(row=1, col=0)
        # self._plot_00.setTitle('К-т преобразования')

        self._curves_00 = dict()

        self._plot_00.setLabel('left', 'Кп', **self.label_style)
        self._plot_00.setLabel('bottom', 'Pвх, ГГц', **self.label_style)
        # self._plot_00.setXRange(0, 11, padding=0)
        # self._plot_00.setYRange(20, 55, padding=0)
        self._plot_00.enableAutoRange('x')
        self._plot_00.enableAutoRange('y')
        self._plot_00.addLegend(offset=(30, 300))
        self._plot_00.showGrid(x=True, y=True)
        self._vb_00 = self._plot_00.vb
        self._vLine_00 = pg.InfiniteLine(angle=90, movable=False)
        self._hLine_00 = pg.InfiniteLine(angle=0, movable=False)
        self._plot_00.addItem(self._vLine_00, ignoreBounds=True)
        self._plot_00.addItem(self._hLine_00, ignoreBounds=True)
        self._proxy_00 = pg.SignalProxy(self._plot_00.scene().sigMouseMoved, rateLimit=60, slot=self.mouseMoved_00)

        self.setLayout(self._grid)

        self._init()

    def mouseMoved_00(self, event):
        pos = event[0]
        if self._plot_00.sceneBoundingRect().contains(pos):
            mouse_point = self._vb_00.mapSceneToView(pos)
            x = mouse_point.x()
            y = mouse_point.y()
            self._vLine_00.setPos(x)
            self._hLine_00.setPos(y)
            if not self._curves_00:
                return

            self._stat_label.setText(_label_text(x, y, [
                [f, curve.yData[_find_value_index(curve.xData, x)]]
                for f, curve in self._curves_00.items()
            ]))

    def _init(self):
        pass

    def clear(self):
        pass

    def plot(self):
        print('plotting primary stats')
        self.clear()
        self._init()

        _plot_curves(self._controller.result.data, self._curves_00, self._plot_00)


def _plot_curves(datas, curves, plot):
    for f_lo, data in datas.items():
        curve_xs, curve_ys = zip(*data)
        try:
            curves[f_lo].setData(x=curve_xs, y=curve_ys)
        except KeyError:
            try:
                color = colors[len(curves)]
            except IndexError:
                color = colors[len(curves) - len(colors)]
            curves[f_lo] = pg.PlotDataItem(
                curve_xs,
                curve_ys,
                pen=pg.mkPen(
                    color=color,
                    width=2,
                ),
                symbol='o',
                symbolSize=5,
                symbolBrush=color,
                name=f'{f_lo} ГГц'
            )
            plot.addItem(curves[f_lo])


def _label_text(x, y, vals):
    vals_str = ''.join(f'   <span style="color:{colors[i]}">{f:0.1f}={v:0.2f}</span>' for i, (f, v) in enumerate(vals))
    return f"<span style='font-size: 12pt'>x={x:0.2f},   y={y:0.2f}   {vals_str}</span>"


def _find_value_index(freqs: list, freq):
    return min(range(len(freqs)), key=lambda i: abs(freqs[i] - freq))
