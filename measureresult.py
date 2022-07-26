import os.path
import random

from collections import defaultdict
from subprocess import Popen
from textwrap import dedent

import openpyxl
import pandas as pd

from forgot_again.file import load_ast_if_exists, pprint_to_file, make_dirs
from forgot_again.string import now_timestamp

KHz = 1_000
MHz = 1_000_000
GHz = 1_000_000_000
mA = 1_000
mV = 1_000


class MeasureResult:
    def __init__(self):
        self._primary_params = None
        self._secondaryParams = None
        self._raw = list()
        self._report = dict()
        self._processed = list()
        self._processed_cutoffs = list()
        self.ready = False

        self.data = defaultdict(list)
        self.data2 = dict()

        self.adjustment = load_ast_if_exists('adjust.ini', default=None)
        self._table_header = list()
        self._table_data = list()

    def __bool__(self):
        return self.ready

    def process(self):
        cutoff_level = -1
        cutoffs = {1: []}

        for f_rf, datas in self.data.items():
            reference = datas[0][1]
            cutoff_point = 0
            cutoff_idx = 0
            pow_in = 0
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

        self._prepare_table_data()

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
            try:
                point = self.adjustment[len(self._processed)]
                k_loss += point['k_loss']
            except LookupError:
                pass

        self._report = {
            'p_lo': p_lo,
            'f_lo': f_lo,
            'p_rf': p_rf,
            'f_rf': f_rf,
            'f_pch': f_pch,
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

        self.adjustment = load_ast_if_exists(self._primary_params.get('adjust', ''), default={})

        self.ready = False

    def set_secondary_params(self, params):
        self._secondaryParams = dict(**params)

    def set_primary_params(self, params):
        self._primary_params = dict(**params)

    def add_point(self, data):
        self._raw.append(data)
        self._process_point(data)

    def save_adjustment_template(self):
        if not self.adjustment:
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
        Fпч, ГГц={f_pch:0.3f}

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

    def _prepare_table_data(self):
        table_file = self._primary_params.get('result', '')

        if not os.path.isfile(table_file):
            return

        wb = openpyxl.load_workbook(table_file)
        ws = wb.active

        rows = list(ws.rows)
        self._table_header = [row.value for row in rows[0][1:]]

        gens = [
            [rows[1][j].value, rows[2][j].value, rows[3][j].value]
            for j in range(1, ws.max_column)
        ]

        self._table_data = [self._gen_value(col) for col in gens]

    def _gen_value(self, data):
        if not data:
            return '-'
        if '-' in data:
            return '-'
        span, step, mean = data
        start = mean - span
        stop = mean + span
        if span == 0 or step == 0:
            return mean
        return round(random.randint(0, int((stop - start) / step)) * step + start, 2)

    def get_result_table_data(self):
        return list(self._table_header), list(self._table_data)
