"""H-C layouts from frozen H-V ownership; never reorder or repartition."""
from __future__ import annotations

from pathlib import Path
import json
import os
import shutil
import sys
import time

import numpy as np
from scipy.sparse import csr_matrix

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from rsh.planner import Matrix, execute_cpu, layout
from rsh.prepare import export
from scripts.hv_cases import check_split, digest, save

PLAN_ARRAYS = ('cube_ptr', 'colref', 'tiles', 'rowmap', 'srows', 'valid')
SHARED_ARRAYS = ('ptr', 'cols', 'values', 'rhs', 'golden', 'valid')


def verify_case(path: Path) -> dict:
    meta = json.loads((path / 'metadata.json').read_text())
    for key, expected in meta['files_sha256'].items():
        assert digest(path / f'{key}.bin') == expected, (str(path), key)
    return meta


def add_controls(target: Path, name: str, n: int) -> None:
    for variant, dirname in [('V0', 'cases_v0'), ('V2', 'cases_v2'), ('H-V', 'cases_hv')]:
        control = ROOT / dirname / name / f'N{n}' / variant
        link = target.parent / variant
        if link.is_symlink():
            assert link.resolve() == control.resolve(), str(link)
        elif link.exists():
            raise ValueError(f'Expected control symlink: {link}')
        else:
            link.symlink_to(os.path.relpath(control, link.parent), target_is_directory=True)


def load_frozen(source: Path, dest: Path | None = None) -> tuple[Matrix, np.ndarray, dict, dict]:
    """Validate existing H-V provenance and optionally copy its exact route bytes."""
    name = source.stem
    manifest = json.loads((ROOT / 'results/hv/manifest.json').read_text())
    for relative in ('rsh/planner.py', 'rsh/prepare.py', 'scripts/hv_cases.py'):
        assert digest(ROOT / relative) == manifest['source_hashes'][relative], relative
    pd = ROOT / 'results/hv/plans' / name
    route = json.loads((pd / 'routing.json').read_text())
    old = json.loads((pd / 'structure.json').read_text())
    od = ROOT / 'results/v2/orders' / name
    v2 = json.loads((od / 'structure.json').read_text())
    assert digest(source) == manifest['inputs'][source.name] == route['input_sha256'] == v2['input_sha256']
    assert digest(od / 'order.bin') == manifest['orders'][name] == route['order_sha256'] == old['order_sha256'] == v2['order_sha256']
    assert digest(pd / 'routing.json') == old['routing_sha256']
    a = Matrix.load(str(source))
    order = np.fromfile(od / 'order.bin', np.int32)
    assert np.array_equal(np.sort(order), np.arange(a.shape[0]))
    split = route['split']
    check_split(a, split)
    assert (split['w'], split['tau_nnz'], split['tau_inc']) == (16, 4, 2)
    assert all(a.ptr[r] == a.ptr[r + 1] for r in split['zeros'])
    if dest is not None:
        target = dest / 'plans' / name / 'routing.json'
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            assert target.read_bytes() == (pd / 'routing.json').read_bytes()
        else:
            shutil.copyfile(pd / 'routing.json', target)
        assert digest(target) == old['routing_sha256']
    return a, order, split, old


def describe(a: Matrix, split: dict, plan: dict) -> dict:
    nnz = np.diff(a.ptr)

    def stats(rows: list[int]) -> dict:
        return {'rows': len(rows), 'nnz': int(nnz[rows].sum()) if rows else 0,
                'zero_rows': int(np.sum(nnz[rows] == 0)) if rows else 0}

    g = [r for group in split['groups'] for r in group]
    unions = [int(np.count_nonzero(plan['colref'][plan['cube_ptr'][i]*16:plan['cube_ptr'][i+1]*16] != a.shape[1]))
              for i in range(len(plan['cube_ptr']) - 1)]
    tail_union = unions[-1] if split['tail'] else 0
    tail_tiles = (tail_union + 15) // 16
    assert len(plan['cube_ptr']) - 1 == len(split['groups']) + bool(split['tail'])
    assert plan['srows'].tolist() == split['residual']
    assert np.all(plan['valid'] == 1)
    expected_rows = g + split['tail']
    assert plan['rowmap'][plan['rowmap'] >= 0].tolist() == expected_rows
    assert len(set(expected_rows + split['residual'] + split['zeros'])) == a.shape[0]
    return {'m': a.shape[0], 'k': a.shape[1], 'nnz': len(a.col), 'w': 16,
            'tau_nnz': 4, 'tau_inc': 2, 'G': stats(g), 'S': stats(split['residual']),
            'T': stats(split['tail']), 'Z': stats(split['zeros']),
            'cube_groups': len(plan['cube_ptr']) - 1, 'main_cube_groups': len(split['groups']),
            'tail_cube_groups': int(bool(split['tail'])), 'tail_k16_tiles': tail_tiles,
            'tail_column_union': tail_union, 'tail_padding_rows': 16-len(split['tail']) if split['tail'] else 0,
            'tail_physical_slots': tail_tiles*256, 'tail_b_gather_rows_per_call': tail_tiles*16,
            'tail_rowmap_slots': 16 if split['tail'] else 0,
            'k16_tiles': len(plan['tiles']), 'aiv_rows': len(plan['srows']),
            'cube_nnz': stats(g)['nnz']+stats(split['tail'])['nnz'],
            'column_union_quantiles': np.quantile(unions, [0, .25, .5, .75, 1]).tolist() if unions else [0]*5,
            'cube_physical_slots': len(plan['tiles'])*256, 'b_gather_rows_per_call': len(plan['colref']),
            'plan_bytes': sum(plan[key].nbytes for key in PLAN_ARRAYS),
            'tail_policy': 'zero_padded_Cube', 'full_output': True,
            'ownership_policy': 'exact saved H-V G/S/T/Z; no new partition or order'}


def smoke_cases(dest: Path) -> list[dict]:
    cases = []
    hv_smoke = json.loads((ROOT / 'results/hv/smoke_preparation.json').read_text())
    assert hv_smoke['passed']
    for case in hv_smoke['cases']:
        base = ROOT / case['root'] / 'H-V'
        meta = verify_case(base)
        m, k, n, stride, _, _, _, _ = map(int, (base / 'config.txt').read_text().split())
        a = Matrix(np.fromfile(base / 'ptr.bin', np.int32), np.fromfile(base / 'cols.bin', np.int32),
                   np.fromfile(base / 'values.bin', np.float16), (m, k))
        order = np.asarray(meta['order'], np.int32)
        split = meta['split']
        check_split(a, split)
        assert np.array_equal(np.sort(order), np.arange(m))
        plan = layout(a, order, split, 'H-C')
        b = np.fromfile(base / 'rhs.bin', np.float16).reshape(k+1, stride)[:k, :n]
        gold = np.fromfile(base / 'golden.bin', np.float32).reshape(m, stride)[:, :n]
        np.testing.assert_allclose(execute_cpu(a, plan, b), gold, atol=1e-3, rtol=1e-3)
        target = ROOT / 'cases_hc' / base.parent.parent.name / f'N{n}' / 'H-C'
        summary = describe(a, split, plan)
        export(a, plan, b, gold, target, summary | {'kind': meta['kind'], 'order': order.tolist(),
               'split': split, 'reused_hv_metadata_sha256': digest(base/'metadata.json')})
        newmeta = verify_case(target)
        for key in SHARED_ARRAYS:
            assert newmeta['files_sha256'][key] == meta['files_sha256'][key]
        link = target.parent / 'H-V'
        if not link.exists():
            link.symlink_to(os.path.relpath(base, link.parent), target_is_directory=True)
        cases.append(case | {'root': str(target.parent.relative_to(ROOT)), 'srows': len(plan['srows']),
                             'cube_groups': summary['cube_groups'], 'tail_all_zero': bool(split['tail']) and summary['T']['nnz'] == 0})
    # One nonzero full group followed by an all-zero tail. No new routing algorithm.
    m, k, n = 17, 37, 33
    rng = np.random.default_rng(51017)
    dense = np.zeros((m, k), np.float16)
    dense[:16, :5] = rng.uniform(-1, 1, (16, 5)).astype(np.float16)
    c = csr_matrix(dense.astype(np.float32))
    a = Matrix(c.indptr.astype(np.int32), c.indices.astype(np.int32), c.data.astype(np.float16), c.shape)
    order = np.r_[np.arange(15, -1, -1), 16].astype(np.int32)
    split = {'groups': [order[:16].tolist()], 'residual': [], 'tail': [16], 'zeros': [],
             'tau_nnz': 4, 'tau_inc': 2, 'w': 16}
    check_split(a, split)
    plan = layout(a, order, split, 'H-C')
    b = rng.uniform(-1, 1, (k, n)).astype(np.float16)
    gold = (dense.astype(np.float64) @ b.astype(np.float64)).astype(np.float32)
    np.testing.assert_allclose(execute_cpu(a, plan, b), gold, atol=1e-3, rtol=1e-3)
    target = ROOT / 'cases_hc/smoke_tail_all_zero/N33/H-C'
    export(a, plan, b, gold, target, describe(a, split, plan) |
           {'kind': 'tail_all_zero', 'order': order.tolist(), 'split': split})
    cases.append({'name': 'tail_all_zero', 'root': str(target.parent.relative_to(ROOT)), 'm': m, 'n': n,
                  'cube_groups': 2, 'srows': 0, 'tail': 1, 'order_nonidentity': True, 'tail_all_zero': True})
    assert len(cases) == len(hv_smoke['cases']) + 1
    assert any(x['cube_groups'] and x['srows'] for x in cases)
    save(dest / 'smoke_preparation.json', {'passed': True, 'reused_hv_cases': len(hv_smoke['cases']), 'cases': cases})
    return cases


def prepare_real(source: Path, dest: Path) -> dict:
    started = time.perf_counter()
    a, order, split, old = load_frozen(source, dest)
    provenance_seconds = time.perf_counter() - started
    t = time.perf_counter()
    plan = layout(a, order, split, 'H-C')
    layout_seconds = time.perf_counter() - t
    summary = describe(a, split, plan) | {'matrix': source.stem,
        'input_sha256': digest(source), 'order_sha256': old['order_sha256'],
        'routing_sha256': old['routing_sha256'], 'routing_source': f'results/hv/plans/{source.stem}/routing.json',
        'hv_structure_sha256': digest(ROOT/'results/hv/plans'/source.stem/'structure.json'),
        'hv_k16_tiles': old['k16_tiles'], 'hv_cube_groups': old['cube_groups'],
        'hv_aiv_rows': old['aiv_rows'], 'hv_b_gather_rows_per_call': old['b_gather_rows_per_call'],
        'v2_k16_tiles': old['v2_k16_tiles'],
        'additional_k16_tiles_vs_hv': len(plan['tiles'])-old['k16_tiles'],
        'additional_physical_slots_vs_hv': (len(plan['tiles'])-old['k16_tiles'])*256,
        'additional_plan_bytes_vs_hv': sum(plan[key].nbytes for key in PLAN_ARRAYS)-old['plan_bytes'],
        'reused_v2_order_seconds': old['reused_v2_order_seconds'],
        'reused_hv_partition_seconds': old['partition_seconds'],
        'partition_seconds': 0., 'partition_policy': 'reuse saved H-V routing; not rerun',
        'reorder_rerun': False, 'partition_rerun': False,
        'provenance_load_validation_seconds': provenance_seconds, 'layout_seconds': layout_seconds}
    assert summary['additional_k16_tiles_vs_hv'] == summary['tail_k16_tiles']
    pd = dest / 'plans' / source.stem
    previous = json.loads((pd/'structure.json').read_text()) if (pd/'structure.json').exists() else None
    if previous:
        for key in ('input_sha256', 'order_sha256', 'routing_sha256', 'k16_tiles', 'plan_bytes'):
            assert previous[key] == summary[key]
    records = []
    for n in (16, 64, 256):
        t = time.perf_counter()
        controls = {v: ROOT/d/source.stem/f'N{n}'/v for v, d in
                    [('V0', 'cases_v0'), ('V2', 'cases_v2'), ('H-V', 'cases_hv')]}
        metas = {v: verify_case(p) for v, p in controls.items()}
        hvmeta = metas['H-V']
        assert hvmeta['routing_sha256'] == summary['routing_sha256']
        assert hvmeta['order_sha256'] == summary['order_sha256']
        control_validation_seconds = time.perf_counter()-t
        base = controls['V0']
        target = ROOT/'cases_hc'/source.stem/f'N{n}'/'H-C'
        if not (target/'metadata.json').exists():
            t = time.perf_counter()
            stride = (n+15)//16*16
            b = np.fromfile(base/'rhs.bin', np.float16).reshape(a.shape[1]+1, stride)[:a.shape[1], :n]
            gold = np.fromfile(base/'golden.bin', np.float32).reshape(a.shape[0], stride)[:, :n]
            export(a, plan, b, gold, target, summary | {'n': n, 'b_seed': 20261017+n,
                   'hv_case_metadata_sha256': digest(controls['H-V']/'metadata.json'),
                   'control_validation_seconds': control_validation_seconds})
            meta = json.loads((target/'metadata.json').read_text())
            meta['case_export_seconds'] = time.perf_counter()-t
            save(target/'metadata.json', meta)
        meta = verify_case(target)
        assert meta['routing_sha256'] == summary['routing_sha256']
        for cm in metas.values():
            for key in SHARED_ARRAYS:
                assert meta['files_sha256'][key] == cm['files_sha256'][key], (source.stem, n, key)
        add_controls(target, source.stem, n)
        records.append({'n': n, 'control_validation_seconds': control_validation_seconds,
                        'case_export_seconds': meta['case_export_seconds'], 'metadata_sha256': digest(target/'metadata.json')})
    summary['cases'] = records
    summary['prepare_export_seconds'] = time.perf_counter()-started
    if previous is None:
        save(pd/'structure.json', summary)
    else:
        summary = previous
    print('HC_PREPARED', source.stem, 'G', summary['G'], 'S', summary['S'], 'T', summary['T'], flush=True)
    return summary
