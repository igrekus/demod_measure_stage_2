import ast
import datetime
import os.path
import pprint

from collections import defaultdict
from subprocess import Popen
from textwrap import dedent

import pandas as pd

from util.file import load_ast_if_exists, pprint_to_file, make_dirs
from util.string import now_timestamp

KHz = 1_000
MHz = 1_000_000
GHz = 1_000_000_000
mA = 1_000
mV = 1_000


class MeasureResult:
    def __init__(self):
        self._secondaryParams = None
        self._raw = list()
        self._report = dict()
        self._processed = list()
        self._processed_cutoffs = list()
        self.ready = False

        self.data = defaultdict(list)
        self.data2 = dict()

        self.adjustment = load_ast_if_exists('adjust.ini', default=None)

    def __bool__(self):
        return self.ready

    def _process(self):
        cutoff_level = -1
        cutoffs = {1: []}

        for f_rf, datas in self.data.items():
            reference = datas[0][1]
            cutoff_point = 0
            cutoff_idx = 0
            for idx, pair in enumerate(datas):
                pow_in, pow_out = pair
                if reference - pow_out > abs(cutoff_level):
                    cutoff_idx = idx
                    cutoff_point = pow_in
                    break
            else:
                cutoff_point = pow_in
            cutoffs[1].append([f_rf, cutoff_point])

        self.data2 = cutoffs
        self._processed_cutoffs = cutoffs
        self.ready = True

    def _process_point(self, data):
        # region calc
        f_rf = data['f_rf']
        f_lo = data['f_lo']
        f_rf_label = data['f_rf_label']
        f_pch = f_rf - f_lo

        p_pch = data['pow_read']
        p_lo = data['p_lo']
        p_rf = data['p_rf']
        p_loss = data['loss']
        k_loss = p_pch - p_rf + p_loss
        # endregion

        if self.adjustment is not None:
            point = self.adjustment[len(self._processed)]
            k_loss += point['k_loss']

        self._report = {
            'p_lo': p_lo,
            'f_lo': f_lo,
            'p_rf': p_rf,
            'f_rf': f_rf,
            'f_pch': f_pch,
            'u_mul': round(data['u_mul'], 1),
            'i_mul': round(data['i_mul'] * mA, 2),
            'p_pch': p_pch,
            'k_loss': round(k_loss, 2),
        }

        self.data[f_rf_label].append([p_rf, k_loss])
        self._processed.append({**self._report})

    def clear(self):
        self._secondaryParams.clear()
        self._raw.clear()
        self._report.clear()
        self._processed.clear()
        self._processed_cutoffs.clear()

        self.data.clear()

        self.ready = False

    def set_secondary_params(self, params):
        self._secondaryParams = dict(**params)

    def add_point(self, data):
        self._raw.append(data)
        self._process_point(data)

    def save_adjustment_template(self):
        if self.adjustment is None:
            print('measured, saving template')
            self.adjustment = [{
                'p_lo': p['p_lo'],
                'f_lo': p['f_lo'],
                'p_rf': p['p_rf'],
                'f_rf': p['f_rf'],
                'k_loss': 0,

            } for p in self._processed]
        pprint_to_file('adjust.ini', self.adjustment)

    @property
    def report(self):
        return dedent("""        Генераторы:
        Pгет, дБм={p_lo}
        Fгет, ГГц={f_lo:0.2f}
        Pвх, дБм={p_rf}
        Fвх, ГГц={f_rf:0.2f}
        Fпч, МГц={f_pch:0.2f}
        
        Источник питания:
        U, В={u_mul}
        I, мА={i_mul}

        Анализатор:
        Pпч, дБм={p_pch}
        
        Расчётные параметры:
        Кп, дБм={k_loss}""".format(**self._report))

    def export_excel(self):
        device = 'demod'
        path = 'xlsx'

        make_dirs(path)

        file_name = f'./{path}/{device}-{now_timestamp()}.xlsx'
        df = pd.DataFrame(self._processed)

        df.columns = [
            'Pгет, дБм', 'Fгет, ГГц',
            'Pвх, дБм', 'Fвх, ГГц',
            'Fпч, ГГц',
            'Uпит, В', 'Iпит, мА',
            'Pпч, дБм',
            'Кп, дБм'
        ]
        df.to_excel(file_name, engine='openpyxl', index=False)

        file_name = f'./{path}/{device}-cutoff-{now_timestamp()}.xlsx'
        df = pd.DataFrame([{'f_lo': d[0], 'p_rf': d[1]} for d in self._processed_cutoffs[1]])

        df.columns = ['Fгет., ГГц', 'Pвх.-1дБ, дБ']
        df.to_excel(file_name, engine='openpyxl', index=False)

        full_path = os.path.abspath(file_name)
        Popen(f'explorer /select,"{full_path}"')
