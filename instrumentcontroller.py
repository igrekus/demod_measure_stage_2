import ast
import time

import numpy as np

from pprint import pprint
from os.path import isfile
from PyQt5.QtCore import QObject, pyqtSlot, pyqtSignal

from instr.instrumentfactory import mock_enabled, GeneratorFactory, SourceFactory, \
    MultimeterFactory, AnalyzerFactory
from measureresult import MeasureResult


# TODO calibration
# TODO add attenuation field -- calculate each pow point + att power
# TODO clear plots after data reset

class InstrumentController(QObject):
    pointReady = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.requiredInstruments = {
            'Анализатор': AnalyzerFactory('GPIB1::7::INSTR'),
            'P LO': GeneratorFactory('GPIB1::6::INSTR'),
            'P RF': GeneratorFactory('GPIB1::20::INSTR'),
            'Источник': SourceFactory('GPIB1::3::INSTR'),
            'Мультиметр': MultimeterFactory('GPIB1::22::INSTR'),
        }

        if isfile('./instr.ini'):
            with open('./instr.ini', mode='rt', encoding='utf-8') as f:
                addrs = ast.literal_eval(''.join(f.readlines()))
                self.requiredInstruments = {
                    'Анализатор': AnalyzerFactory(addrs['Анализатор']),
                    'P LO': GeneratorFactory(addrs['P LO']),
                    'P RF': GeneratorFactory(addrs['P RF']),
                    'Источник': SourceFactory(addrs['Источник']),
                    'Мультиметр': MultimeterFactory(addrs['Мультиметр']),
                }

        self.deviceParams = {
            'Демодулятор': {
                'F': 1,
            },
        }

        self.secondaryParams = {
            'Frf_delta': 0.5,
            'Frf_max': 3.06,
            'Frf_min': 0.06,
            'Prf_delta': 2.0,
            'Prf_max': 6.0,
            'Prf_min': -20.0,
            'Flo_delta': 0.5,
            'Flo_max': 3.05,
            'Flo_min': 0.05,
            'Plo': -5.0,
            'Usrc': 5.0,
            'loss': 0.82,
            'ref_lev': 10.0,
            'scale_y': 5.0,
        }

        if isfile('./params.ini'):
            with open('./params.ini', 'rt', encoding='utf-8') as f:
                self.secondaryParams = ast.literal_eval(''.join(f.readlines()))

        self._instruments = dict()
        self.found = False
        self.present = False
        self.hasResult = False
        self.only_main_states = False

        self.result = MeasureResult()

    def __str__(self):
        return f'{self._instruments}'

    def connect(self, addrs):
        print(f'searching for {addrs}')
        for k, v in addrs.items():
            self.requiredInstruments[k].addr = v
        self.found = self._find()

    def _find(self):
        self._instruments = {
            k: v.find() for k, v in self.requiredInstruments.items()
        }
        return all(self._instruments.values())

    def check(self, token, params):
        print(f'call check with {token} {params}')
        device, secondary = params
        self.present = self._check(token, device, secondary)
        print('sample pass')

    def _check(self, token, device, secondary):
        print(f'launch check with {self.deviceParams[device]} {self.secondaryParams}')
        return True

    def measure(self, token, params):
        print(f'call measure with {token} {params}')
        device, _ = params
        try:
            self.result.set_secondary_params(self.secondaryParams)
            self._measure(token, device)
            # self.hasResult = bool(self.result)
            self.hasResult = True  # HACK
        except RuntimeError as ex:
            print('runtime error:', ex)

    def _measure(self, token, device):
        param = self.deviceParams[device]
        secondary = self.secondaryParams
        print(f'launch measure with {token} {param} {secondary}')

        self._clear()
        self._init()
        self._measure_s_params(token, param, secondary)
        return True

    def _clear(self):
        self.result.clear()

    def _init(self):
        self._instruments['P LO'].send('*RST')
        self._instruments['P RF'].send('*RST')
        self._instruments['Источник'].send('*RST')
        self._instruments['Мультиметр'].send('*RST')
        self._instruments['Анализатор'].send('*RST')

    def _measure_s_params(self, token, param, secondary):
        gen_lo = self._instruments['P LO']
        gen_rf = self._instruments['P RF']
        src = self._instruments['Источник']
        mult = self._instruments['Мультиметр']
        sa = self._instruments['Анализатор']

        src_u = secondary['Usrc']
        src_i = 200  # mA

        pow_lo = secondary['Plo']
        freq_lo_start = secondary['Flo_min']
        freq_lo_end = secondary['Flo_max']
        freq_lo_step = secondary['Flo_delta']

        pow_rf_start = secondary['Prf_min']
        pow_rf_end = secondary['Prf_max']
        pow_rf_step = secondary['Prf_delta']

        freq_rf_start = secondary['Frf_min']
        freq_rf_end = secondary['Frf_max']
        freq_rf_step = secondary['Frf_delta']

        ref_level = secondary['ref_lev']
        scale_y = secondary['scale_y']

        p_loss = secondary['loss']

        pow_rf_values = [round(x, 3) for x in np.arange(start=pow_rf_start, stop=pow_rf_end + 0.002, step=pow_rf_step)]
        freq_lo_values = [round(x, 3) for x in
                          np.arange(start=freq_lo_start, stop=freq_lo_end + 0.002, step=freq_lo_step)]
        freq_rf_values = [round(x, 3) for x in
                          np.arange(start=freq_rf_start, stop=freq_rf_end + 0.002, step=freq_rf_step)]

        src.send(f'APPLY p6v,{src_u}V,{src_i}mA')

        gen_lo.send(f'SOUR:POW {pow_lo}dbm')

        sa.send(':CAL:AUTO OFF')
        sa.send(':SENS:FREQ:SPAN 1MHz')
        sa.send(f'DISP:WIND:TRAC:Y:RLEV {ref_level}')
        sa.send(f'DISP:WIND:TRAC:Y:PDIV {scale_y}')

        gen_lo.send(f':OUTP:MOD:STAT OFF')
        # gen_rf.send(f':OUTP:MOD:STAT OFF')

        if mock_enabled:
            with open('./mock_data/-5db.txt', mode='rt', encoding='utf-8') as f:
                index = 0
                mocked_raw_data = ast.literal_eval(''.join(f.readlines()))

        res = []
        for freq_lo, freq_rf in zip(freq_lo_values, freq_rf_values):
            gen_lo.send(f'SOUR:FREQ {freq_lo}GHz')
            gen_rf.send(f'SOUR:FREQ {freq_rf}GHz')

            for pow_rf in pow_rf_values:

                if token.cancelled:
                    gen_lo.send(f'OUTP:STAT OFF')
                    gen_rf.send(f'OUTP:STAT OFF')

                    if not mock_enabled:
                        time.sleep(0.5)

                    src.send('OUTPut OFF')

                    gen_rf.send(f'SOUR:POW {pow_rf_start}dbm')
                    gen_lo.send(f'SOUR:POW {pow_lo}dbm')

                    gen_rf.send(f'SOUR:FREQ {freq_rf_start}GHz')
                    gen_lo.send(f'SOUR:FREQ {freq_rf_start}GHz')
                    raise RuntimeError('measurement cancelled')

                gen_rf.send(f'SOUR:POW {pow_rf}dbm')

                src.send('OUTPut ON')

                gen_lo.send(f'OUTP:STAT ON')
                gen_rf.send(f'OUTP:STAT ON')

                time.sleep(0.1)
                if not mock_enabled:
                    time.sleep(0.5)

                i_mul_read = float(mult.query('MEAS:CURR:DC? 1A,DEF'))

                center_freq = freq_rf - freq_lo
                sa.send(':CALC:MARK1:MODE POS')
                sa.send(f':SENSe:FREQuency:CENTer {center_freq}GHz')
                sa.send(f':CALCulate:MARKer1:X:CENTer {center_freq}GHz')

                if not mock_enabled:
                    time.sleep(0.5)

                pow_read = float(sa.query(':CALCulate:MARKer:Y?'))

                raw_point = {
                    'f_lo': freq_lo,
                    'f_rf': freq_rf,
                    'p_lo': pow_lo,
                    'p_rf': pow_rf,
                    'u_mul': src_u,
                    'i_mul': i_mul_read,
                    'pow_read': pow_read,
                    'loss': p_loss,
                }

                if mock_enabled:
                    raw_point = mocked_raw_data[index]
                    raw_point['loss'] = p_loss
                    index += 1

                print(raw_point)
                self._add_measure_point(raw_point)

                res.append(raw_point)

        if not mock_enabled:
            with open('out.txt', mode='wt', encoding='utf-8') as f:
                f.send(str(res))

        gen_lo.send(f'OUTP:STAT OFF')
        gen_rf.send(f'OUTP:STAT OFF')

        if not mock_enabled:
            time.sleep(0.5)

        src.send('OUTPut OFF')

        gen_rf.send(f'SOUR:POW {pow_rf_start}dbm')
        gen_lo.send(f'SOUR:POW {pow_lo}dbm')

        gen_rf.send(f'SOUR:FREQ {freq_rf_start}GHz')
        gen_lo.send(f'SOUR:FREQ {freq_rf_start}GHz')
        return res

    def _add_measure_point(self, data):
        print('measured point:', data)
        self.result.add_point(data)
        self.pointReady.emit()

    def saveConfigs(self):
        with open('./params.ini', 'wt', encoding='utf-8') as f:
            pprint(self.secondaryParams, stream=f)

    @pyqtSlot(dict)
    def on_secondary_changed(self, params):
        self.secondaryParams = params

    @property
    def status(self):
        return [i.status for i in self._instruments.values()]


def parse_float_list(lst):
    return [float(x) for x in lst.split(',')]
