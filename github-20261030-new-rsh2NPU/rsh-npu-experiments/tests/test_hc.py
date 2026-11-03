"""CPU checks for frozen ownership, zero-block tails, and exact recovery."""
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


class FrozenHCTest(unittest.TestCase):
    def test_all_zero_tail_has_mapping_but_no_k_blocks(self) -> None:
        dense = np.zeros((17, 37), np.float16)
        dense[:16, :5] = .25
        c = csr_matrix(dense.astype(np.float32))
        a = Matrix(c.indptr.astype(np.int32), c.indices.astype(np.int32), c.data.astype(np.float16), c.shape)
        order = np.r_[np.arange(15, -1, -1), 16].astype(np.int32)
        split = {'groups': [order[:16].tolist()], 'residual': [], 'tail': [16], 'zeros': [],
                 'tau_nnz': 4, 'tau_inc': 2, 'w': 16}
        p = layout(a, order, split, 'H-C')
        info = hc.describe(a, split, p)
        self.assertEqual(p['cube_ptr'].tolist(), [0, 1, 1])
        self.assertEqual(p['rowmap'][16:].tolist(), [16] + [-1]*15)
        self.assertEqual(info['tail_column_union'], 0)
        self.assertEqual(info['tail_k16_tiles'], 0)
        self.assertEqual(info['tail_cube_groups'], 1)
        b = np.ones((37, 33), np.float16)
        np.testing.assert_allclose(execute_cpu(a, p, b), dense.astype(np.float32) @ b.astype(np.float32))

    def test_prepare_uses_frozen_route_and_reproduces_all_bytes(self) -> None:
        original_root = hc.ROOT
        with tempfile.TemporaryDirectory(prefix='test-hc-') as tmp:
            root = Path(tmp)
            for rel in ('rsh/planner.py', 'rsh/prepare.py', 'scripts/hv_cases.py'):
                (root/rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(original_root/rel, root/rel)
            m, k = 32, 37
            rng = np.random.default_rng(1234)
            dense = np.zeros((m, k), np.float16)
            dense[:, :5] = rng.uniform(-1, 1, (m, 5)).astype(np.float16)
            dense[0, 1:] = 0
            c = csr_matrix(dense.astype(np.float32))
            a = Matrix(c.indptr.astype(np.int32), c.indices.astype(np.int32), c.data.astype(np.float16), c.shape)
            source = root/'inputs/tiny.npz'
            source.parent.mkdir()
            np.savez(source, indptr=a.ptr, indices=a.col, values=a.val, shape=np.array(a.shape))
            order = np.roll(np.arange(m, dtype=np.int32)[::-1], 1).copy()
            split = {'groups': [order[1:17].tolist()], 'residual': [0], 'tail': order[17:].tolist(),
                     'zeros': [], 'tau_nnz': 4, 'tau_inc': 2, 'w': 16}
            od = root/'results/v2/orders/tiny'
            od.mkdir(parents=True)
            order.tofile(od/'order.bin')
            route = {'matrix': 'tiny', 'input_sha256': hc.digest(source), 'order_sha256': hc.digest(od/'order.bin'), 'split': split}
            hc.save(od/'structure.json', {key: route[key] for key in ('input_sha256', 'order_sha256')})
            pd = root/'results/hv/plans/tiny'
            hc.save(pd/'routing.json', route)
            hvplan = layout(a, order, split, 'H-V')
            v2plan = layout(a, order, split, 'V2')
            old = {'order_sha256': route['order_sha256'], 'routing_sha256': hc.digest(pd/'routing.json'),
                   'k16_tiles': len(hvplan['tiles']), 'cube_groups': 1, 'aiv_rows': 16,
                   'v2_k16_tiles': len(v2plan['tiles']), 'plan_bytes': sum(hvplan[key].nbytes for key in hc.PLAN_ARRAYS),
                   'b_gather_rows_per_call': len(hvplan['colref']), 'partition_seconds': .001, 'reused_v2_order_seconds': .002}
            hc.save(pd/'structure.json', old)
            hc.save(root/'results/hv/manifest.json', {'inputs': {source.name: route['input_sha256']},
                    'orders': {'tiny': route['order_sha256']}, 'source_hashes': {r: hc.digest(root/r) for r in
                    ('rsh/planner.py', 'rsh/prepare.py', 'scripts/hv_cases.py')}})
            for n in (16, 64, 256):
                b = rng.uniform(-1, 1, (k, n)).astype(np.float16)
                gold = (dense.astype(np.float64) @ b.astype(np.float64)).astype(np.float32)
                for variant, dirname in [('V0', 'cases_v0'), ('V2', 'cases_v2'), ('H-V', 'cases_hv')]:
                    p = layout(a, order, split, variant)
                    export(a, p, b, gold, root/dirname/'tiny'/f'N{n}'/variant, old)
            with patch.object(hc, 'ROOT', root), patch('rsh.planner.reorder', side_effect=AssertionError('reorder rerun')), patch('rsh.planner.partition', side_effect=AssertionError('partition rerun')):
                info = hc.prepare_real(source, root/'results/hc')
                self.assertFalse(info['partition_rerun'])
                self.assertEqual(info['tail_k16_tiles'], 1)
                self.assertEqual((root/'results/hc/plans/tiny/routing.json').read_bytes(), (pd/'routing.json').read_bytes())
                p = layout(a, order, split, 'H-C')
                for n in (16, 64, 256):
                    target = root/'cases_hc/tiny'/f'N{n}'/'H-C'
                    meta = hc.verify_case(target)
                    base = root/'cases_v0/tiny'/f'N{n}'/'V0'
                    b = np.fromfile(base/'rhs.bin', np.float16).reshape(k+1, n)[:k]
                    gold = np.fromfile(base/'golden.bin', np.float32).reshape(m, n)
                    with tempfile.TemporaryDirectory(dir=root) as out:
                        export(a, p, b, gold, Path(out), meta)
                        regenerated = hc.verify_case(Path(out))
                        self.assertEqual(meta['files_sha256'], regenerated['files_sha256'])
                        self.assertEqual((target/'config.txt').read_bytes(), (Path(out)/'config.txt').read_bytes())
                    np.testing.assert_allclose(execute_cpu(a, p, b), gold, rtol=1e-3, atol=1e-3)
                # An altered route must fail, even if it retains complete coverage.
                route['split']['tail'].reverse()
                hc.save(pd/'routing.json', route)
                with self.assertRaises(AssertionError):
                    hc.load_frozen(source)


if __name__ == '__main__':
    unittest.main()
