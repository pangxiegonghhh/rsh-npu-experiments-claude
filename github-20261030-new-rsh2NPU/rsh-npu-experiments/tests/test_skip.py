"""Checks for same-output comparisons, preserved B space, and exact recovery."""
from pathlib import Path
import json
import shutil
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from scipy.sparse import csr_matrix

from rsh.planner import Matrix, execute_cpu, layout
from rsh.prepare import export
from scripts import hc_cases as hc
from scripts import skip_cases as skip
from scripts import restore_skip_cases as restore


def matrix(dense: np.ndarray) -> Matrix:
    c = csr_matrix(dense.astype(np.float32))
    return Matrix(c.indptr.astype(np.int32), c.indices.astype(np.int32), c.data.astype(np.float16), c.shape)


def noncontiguous() -> tuple[Matrix, np.ndarray, dict, np.ndarray]:
    dense = np.zeros((20, 37), np.float16)
    dense[:, :5] = .25
    tail, residual = [0, 7, 15], [9]
    group = [r for r in range(19, -1, -1) if r not in tail + residual]
    dense[group[0], :] = .125  # Retained long row stays whole on Cube.
    dense[9, tail] = [.5, .75, 1.]
    order = np.asarray(group + residual + tail, np.int32)
    split = {'groups': [group], 'residual': residual, 'tail': tail, 'zeros': [],
             'w': 16, 'tau_nnz': 4, 'tau_inc': 2}
    return matrix(dense), order, split, dense


class SkipCasesTest(unittest.TestCase):
    def test_noncontiguous_retained_rows_preserve_b_tail_indices_and_s(self) -> None:
        a, order, split, dense = noncontiguous()
        plans = skip.plans_for(a, order, split)
        b = np.random.default_rng(201).uniform(-1, 1, (37, 33)).astype(np.float16)
        golden = dense.astype(np.float64) @ b.astype(np.float64)
        keep = np.ones(20, bool)
        keep[split['tail']] = False
        for p in plans.values():
            result = execute_cpu(a, p, b)
            np.testing.assert_allclose(result[keep], golden[keep], atol=1e-4, rtol=1e-4)
            np.testing.assert_array_equal(result[~keep], 0)
            np.testing.assert_array_equal(p['valid'], keep)
        self.assertEqual(plans['H-Skip']['srows'].tolist(), [9])
        self.assertEqual(plans['V2-R']['rowmap'][plans['V2-R']['rowmap'] >= 0].tolist(), order[:17].tolist())
        # Removing same-numbered B rows would change retained output, exposing
        # accidental column compaction that a prefix-only smoke would miss.
        wrong_b = b.copy()
        wrong_b[split['tail']] = 0
        self.assertGreater(float(np.max(np.abs(execute_cpu(a, plans['H-Skip'], wrong_b)[keep] - golden[keep]))), .1)

    def test_empty_retained_output_and_retained_zero_rows(self) -> None:
        a = matrix(np.full((7, 37), .5, np.float16))
        order = np.arange(6, -1, -1, dtype=np.int32)
        split = {'groups': [], 'residual': [], 'tail': order.tolist(), 'zeros': [],
                 'w': 16, 'tau_nnz': 4, 'tau_inc': 2}
        for plan in skip.plans_for(a, order, split).values():
            self.assertEqual(int(plan['valid'].sum()), 0)
            self.assertEqual(len(plan['srows']), 0)
            self.assertEqual(len(plan['cube_ptr']), 1)
        a = matrix(np.zeros((17, 37), np.float16))
        order = np.arange(16, -1, -1, dtype=np.int32)
        split['zeros'], split['tail'] = order[:2].tolist(), order[2:].tolist()
        plans = skip.plans_for(a, order, split)
        self.assertEqual(plans['H-Skip']['cube_ptr'].tolist(), [0])
        self.assertEqual(plans['V2-R']['cube_ptr'].tolist(), [0, 0])
        self.assertEqual(plans['V2-R']['rowmap'][:2].tolist(), [16, 15])
        for plan in plans.values():
            self.assertEqual(int(plan['valid'].sum()), 2)
            np.testing.assert_array_equal(execute_cpu(a, plan, np.ones((37, 33), np.float16)), 0)

    def test_t0_equivalence_has_retained_long_row_without_splitting(self) -> None:
        dense = np.ones((17, 37), np.float16)
        a = matrix(dense)
        order = np.arange(16, -1, -1, dtype=np.int32)
        split = {'groups': [order[:16].tolist()], 'residual': [0], 'tail': [], 'zeros': [],
                 'w': 16, 'tau_nnz': 4, 'tau_inc': 2}
        plans = skip.plans_for(a, order, split)
        hv = layout(a, order, split, 'H-V')
        for key in skip.PLAN_ARRAYS:
            np.testing.assert_array_equal(plans['H-Skip'][key], hv[key])
        self.assertEqual(plans['H-Skip']['srows'].tolist(), [0])
        self.assertEqual(plans['H-Skip']['cube_ptr'].tolist(), [0, 3])
        self.assertEqual(int(plans['H-Skip']['valid'].sum()), 17)

    def test_frozen_prepare_and_compact_recovery_preserve_metadata(self) -> None:
        original_root = skip.ROOT
        a, order, split, dense = noncontiguous()
        with tempfile.TemporaryDirectory(prefix='test-skip-') as tmp:
            root = Path(tmp)
            source = root / 'inputs/tiny.npz'
            source.parent.mkdir()
            np.savez(source, indptr=a.ptr, indices=a.col, values=a.val, shape=np.array(a.shape))
            for rel in ('rsh/planner.py', 'rsh/prepare.py', 'scripts/hv_cases.py'):
                (root / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(original_root / rel, root / rel)
            od = root / 'results/v2/orders/tiny'
            od.mkdir(parents=True)
            order.tofile(od / 'order.bin')
            route = {'matrix': 'tiny', 'input_sha256': skip.digest(source),
                     'order_sha256': skip.digest(od / 'order.bin'), 'split': split}
            skip.save(od / 'structure.json', {k: route[k] for k in ('input_sha256', 'order_sha256')})
            pd = root / 'results/hv/plans/tiny'
            skip.save(pd / 'routing.json', route)
            hv = layout(a, order, split, 'H-V')
            old = {'order_sha256': route['order_sha256'], 'routing_sha256': skip.digest(pd / 'routing.json'),
                   'k16_tiles': len(hv['tiles']), 'cube_groups': 1, 'aiv_rows': 4,
                   'v2_k16_tiles': len(layout(a, order, split, 'V2')['tiles']),
                   'plan_bytes': sum(hv[key].nbytes for key in skip.PLAN_ARRAYS),
                   'b_gather_rows_per_call': len(hv['colref']), 'partition_seconds': .001,
                   'reused_v2_order_seconds': .002}
            skip.save(pd / 'structure.json', old)
            manifest = {'inputs': {'tiny.npz': route['input_sha256']}, 'orders': {'tiny': route['order_sha256']},
                        'source_hashes': {rel: skip.digest(root / rel) for rel in
                                         ('rsh/planner.py', 'rsh/prepare.py', 'scripts/hv_cases.py')}}
            skip.save(root / 'results/hv/manifest.json', manifest)
            skip.save(root / 'results/skip/manifest.json', manifest)
            for n in (16, 64, 256):
                b = np.random.default_rng(n).uniform(-1, 1, (37, n)).astype(np.float16)
                gold = (dense.astype(np.float64) @ b.astype(np.float64)).astype(np.float32)
                for variant, dirname in skip.CONTROLS:
                    export(a, layout(a, order, split, variant), b, gold,
                           root / dirname / 'tiny' / f'N{n}' / variant, old)
            with patch.object(skip, 'ROOT', root), patch.object(hc, 'ROOT', root), patch.object(restore, 'ROOT', root), \
                 patch('rsh.planner.reorder', side_effect=AssertionError('reorder rerun')), \
                 patch('rsh.planner.partition', side_effect=AssertionError('partition rerun')):
                info = skip.prepare_real(source, root / 'results/skip')
                self.assertEqual(info['R']['rows'], 17)
                self.assertEqual(info['tail_original_rows'], [0, 7, 15])
                self.assertEqual((root / 'results/skip/plans/tiny/routing.json').read_bytes(), (pd / 'routing.json').read_bytes())
                metadata = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in (root / 'cases_skip').rglob('metadata.json')}
                expected = {p: skip.digest(p) for p in (root / 'cases_skip').rglob('*.bin')}
                # Simulate the compact recovery package: saved metadata exists,
                # all three newly measured binary variants are absent.
                for p in expected:
                    p.unlink()
                records = restore.restore_formal(root / 'results/skip')
                self.assertEqual(len(records), 3)
                for p, h in expected.items():
                    self.assertEqual(skip.digest(p), h)
                for p, (data, modified) in metadata.items():
                    self.assertEqual(p.read_bytes(), data)
                    self.assertEqual(p.stat().st_mtime_ns, modified)
                # A new member ordering, despite equal overall coverage, is not
                # allowed to silently replace the measured frozen route.
                route['split']['tail'].reverse()
                skip.save(pd / 'routing.json', route)
                with self.assertRaises(AssertionError):
                    skip.load_frozen(source)


if __name__ == '__main__':
    unittest.main()
