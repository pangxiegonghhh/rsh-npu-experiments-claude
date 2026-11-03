"""Same-retained-output H-Skip cases from the measured, frozen H-V routes."""
from __future__ import annotations

from pathlib import Path
import json
import os
import shutil
import sys
import tempfile
import time

import numpy as np
from scipy.sparse import csr_matrix

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from rsh.planner import Matrix, execute_cpu, layout
from rsh.prepare import export
from scripts.hc_cases import load_frozen, verify_case
from scripts.hv_cases import check_split, digest, save

VARIANTS = ('V0-R', 'V2-R', 'H-Skip')
CONTROLS = (('V0', 'cases_v0'), ('V2', 'cases_v2'), ('H-V', 'cases_hv'), ('H-C', 'cases_hc'))
PLAN_ARRAYS = ('cube_ptr', 'colref', 'tiles', 'rowmap', 'srows', 'valid')
SHARED_ARRAYS = ('ptr', 'cols', 'values', 'rhs', 'golden')


def plans_for(a: Matrix, order: np.ndarray, split: dict) -> dict[str, dict]:
    """Restrict the existing order for V2-R; leave H-Skip G and S untouched."""
    check_split(a, split)
    assert np.array_equal(np.sort(order), np.arange(a.shape[0]))
    plans = {variant: layout(a, order, split, variant) for variant in VARIANTS}
    expected = np.ones(a.shape[0], np.uint8)
    expected[split['tail']] = 0
    retained = np.flatnonzero(expected).tolist()
    restricted = [int(r) for r in order if expected[r]]
    for variant, plan in plans.items():
        assert np.array_equal(plan['valid'], expected), variant
        assert len(set(plan['rowmap'][plan['rowmap'] >= 0].tolist() + plan['srows'].tolist())) == int(np.sum(plan['rowmap'] >= 0)) + len(plan['srows'])
    assert plans['V0-R']['srows'].tolist() == retained
    p = plans['V2-R']
    assert p['rowmap'][p['rowmap'] >= 0].tolist() == restricted
    p = plans['H-Skip']
    assert p['rowmap'][p['rowmap'] >= 0].tolist() == [r for group in split['groups'] for r in group]
    assert p['srows'].tolist() == split['residual']
    assert len(p['cube_ptr']) - 1 == len(split['groups'])
    return plans


def describe(a: Matrix, order: np.ndarray, split: dict, plans: dict[str, dict]) -> dict:
    nnz = np.diff(a.ptr)
    tail = split['tail']
    removed = set(tail)
    retained = [r for r in range(a.shape[0]) if r not in removed]

    def stats(rows: list[int]) -> dict:
        count = int(nnz[rows].sum()) if rows else 0
        return {'rows': len(rows), 'nnz': count,
                'zero_rows': int(np.sum(nnz[rows] == 0)) if rows else 0,
                'row_percent': 100. * len(rows) / a.shape[0] if a.shape[0] else 0.,
                'nnz_percent': 100. * count / len(a.col) if len(a.col) else 0.}

    variants = {}
    for variant, plan in plans.items():
        variants[variant] = {'cube_groups': len(plan['cube_ptr']) - 1, 'k16_tiles': len(plan['tiles']),
            'aiv_rows': len(plan['srows']), 'included_rows': int(plan['valid'].sum()),
            'cube_physical_slots': len(plan['tiles']) * 256,
            'b_gather_rows_per_call': len(plan['colref']),
            'plan_bytes': sum(plan[key].nbytes for key in PLAN_ARRAYS)}
    return {'m': a.shape[0], 'k': a.shape[1], 'nnz': len(a.col), 'w': 16,
        'tau_nnz': 4, 'tau_inc': 2, 'G': stats([r for group in split['groups'] for r in group]),
        'S': stats(split['residual']), 'T': stats(tail), 'Z': stats(split['zeros']), 'R': stats(retained),
        'retained_original_rows': retained, 'tail_original_rows': tail.copy(),
        'retained_v2_order': [int(r) for r in order if r not in removed],
        'variants': variants, 'tail_policy': 'excluded_from_output',
        'partial_output_diagnostic': True, 'full_output': not bool(tail),
        'same_output_variants': list(VARIANTS), 'b_policy': 'full original K rows; same full column space',
        'ownership_policy': 'exact saved H-V G/S/T/Z; H-Skip omits T only; V2-R restricts saved order',
        'reorder_rerun': False, 'partition_rerun': False, 'partition_seconds': 0.}


def add_controls(target: Path, name: str, n: int) -> None:
    for variant, dirname in CONTROLS:
        control = ROOT / dirname / name / f'N{n}' / variant
        link = target.parent / variant
        if link.is_symlink():
            assert link.resolve() == control.resolve(), str(link)
        elif link.exists():
            raise ValueError(f'Expected control symlink: {link}')
        else:
            link.symlink_to(os.path.relpath(control, link.parent), target_is_directory=True)


def materialize(a: Matrix, plan: dict, b: np.ndarray, gold: np.ndarray, target: Path, metadata: dict) -> dict:
    """Restore missing binaries exactly while preserving existing measured metadata."""
    if not (target / 'metadata.json').exists():
        started = time.perf_counter()
        export(a, plan, b, gold, target, metadata)
        meta = json.loads((target / 'metadata.json').read_text())
        meta['case_export_seconds'] = time.perf_counter() - started
        save(target / 'metadata.json', meta)
    else:
        meta = json.loads((target / 'metadata.json').read_text())
        with tempfile.TemporaryDirectory(prefix='restore-skip-', dir=ROOT) as temporary:
            tmp = Path(temporary)
            export(a, plan, b, gold, tmp, meta)
            regenerated = verify_case(tmp)
            assert regenerated['files_sha256'] == meta['files_sha256'], str(target)
            if (target / 'config.txt').exists():
                assert (tmp / 'config.txt').read_bytes() == (target / 'config.txt').read_bytes()
            for path in tmp.iterdir():
                if path.name == 'metadata.json':
                    continue
                old = target / path.name
                if not old.exists() or digest(old) != digest(path):
                    shutil.move(str(path), old)
    return verify_case(target)


def prepare_real(source: Path, dest: Path) -> dict:
    started = time.perf_counter()
    a, order, split, old = load_frozen(source, dest)
    validation_seconds = time.perf_counter() - started
    t = time.perf_counter()
    plans = plans_for(a, order, split)
    layout_seconds = time.perf_counter() - t
    summary = describe(a, order, split, plans) | {'matrix': source.stem,
        'input_sha256': digest(source), 'order_sha256': old['order_sha256'],
        'routing_sha256': old['routing_sha256'],
        'routing_source': f'results/hv/plans/{source.stem}/routing.json',
        'hv_structure_sha256': digest(ROOT / 'results/hv/plans' / source.stem / 'structure.json'),
        'provenance_load_validation_seconds': validation_seconds, 'layout_seconds': layout_seconds,
        'reused_v2_order_seconds': old['reused_v2_order_seconds'],
        'reused_hv_partition_seconds': old['partition_seconds']}
    pd = dest / 'plans' / source.stem
    previous = json.loads((pd / 'structure.json').read_text()) if (pd / 'structure.json').exists() else None
    if previous:
        for key in ('input_sha256', 'order_sha256', 'routing_sha256', 'variants', 'retained_original_rows', 'tail_original_rows'):
            assert previous[key] == summary[key], key
    records = []
    for n in (16, 64, 256):
        t = time.perf_counter()
        controls = {variant: ROOT / dirname / source.stem / f'N{n}' / variant for variant, dirname in CONTROLS}
        metas = {variant: verify_case(path) for variant, path in controls.items()}
        for variant in ('H-V', 'H-C'):
            assert metas[variant]['routing_sha256'] == summary['routing_sha256']
            assert metas[variant]['order_sha256'] == summary['order_sha256']
        base = controls['V0']
        stride = (n + 15) // 16 * 16
        b = np.fromfile(base / 'rhs.bin', np.float16).reshape(a.shape[1] + 1, stride)[:a.shape[1], :n]
        gold = np.fromfile(base / 'golden.bin', np.float32).reshape(a.shape[0], stride)[:, :n]
        cv_seconds = time.perf_counter() - t
        records_n = {}
        for variant, plan in plans.items():
            target = ROOT / 'cases_skip' / source.stem / f'N{n}' / variant
            meta = materialize(a, plan, b, gold, target, summary | summary['variants'][variant] |
                {'n': n, 'b_seed': 20261017 + n, 'control_validation_seconds': cv_seconds,
                 'hv_case_metadata_sha256': digest(controls['H-V'] / 'metadata.json')})
            assert meta['routing_sha256'] == summary['routing_sha256']
            for cm in metas.values():
                for key in SHARED_ARRAYS:
                    assert meta['files_sha256'][key] == cm['files_sha256'][key], (source.stem, n, variant, key)
            for key in ('cube_ptr', 'colref', 'tiles', 'rowmap'):
                if variant == 'H-Skip':
                    assert meta['files_sha256'][key] == metas['H-V']['files_sha256'][key], key
            records_n[variant] = {'metadata_sha256': digest(target / 'metadata.json'),
                                  'case_export_seconds': meta['case_export_seconds']}
        valid_hashes = {verify_case(ROOT / 'cases_skip' / source.stem / f'N{n}' / v)['files_sha256']['valid'] for v in VARIANTS}
        assert len(valid_hashes) == 1
        add_controls(ROOT / 'cases_skip' / source.stem / f'N{n}' / 'H-Skip', source.stem, n)
        records.append({'n': n, 'control_validation_seconds': cv_seconds, 'variants': records_n})
    summary['cases'] = records
    summary['prepare_export_seconds'] = time.perf_counter() - started
    if previous is None:
        save(pd / 'structure.json', summary)
    else:
        summary = previous
    print('SKIP_PREPARED', source.stem, 'R', summary['R'], 'T', summary['T'], flush=True)
    return summary


def _smoke_export(name: str, a: Matrix, order: np.ndarray, split: dict, b: np.ndarray,
                  gold: np.ndarray, metadata: dict, dest: Path) -> dict:
    plans = plans_for(a, order, split)
    summary = describe(a, order, split, plans)
    n = b.shape[1]
    base = ROOT / 'cases_skip' / f'smoke_{name}' / f'N{n}'
    keep = plans['H-Skip']['valid'].astype(bool)
    for variant, plan in plans.items():
        result = execute_cpu(a, plan, b)
        np.testing.assert_allclose(result[keep], gold[keep], atol=1e-3, rtol=1e-3)
        assert np.all(result[~keep] == 0)
        materialize(a, plan, b, gold, base / variant, summary | summary['variants'][variant] |
                    metadata | {'kind': metadata.get('kind', name), 'order': order.tolist(), 'split': split, 'n': n})
    hashes = [verify_case(base / variant)['files_sha256'] for variant in VARIANTS]
    for key in SHARED_ARRAYS + ('valid',):
        assert len({h[key] for h in hashes}) == 1
    source = dest / 'smoke_inputs' / f'{name}_N{n}.npz'
    source.parent.mkdir(parents=True, exist_ok=True)
    arrays = {'ptr': a.ptr, 'cols': a.col, 'values': a.val, 'shape': np.asarray(a.shape, np.int64)}
    if source.exists():
        with np.load(source) as old:
            for key, expected in arrays.items():
                np.testing.assert_array_equal(old[key], expected)
    else:
        np.savez(source, **arrays)
    return {'name': f'{name}_N{n}', 'root': str(base.relative_to(ROOT)), 'm': a.shape[0], 'k': a.shape[1], 'n': n,
        'input': str(source.resolve().relative_to(ROOT)), 'input_sha256': digest(source),
        'cube_groups': len(split['groups']), 'srows': len(split['residual']), 'tail': len(split['tail']),
        'retained_rows': int(keep.sum()), 'empty_R': not bool(keep.any()), 'tail_empty': not bool(split['tail']),
        'R_noncontiguous': bool(keep.any()) and np.flatnonzero(keep).tolist() != list(range(int(keep.sum()))),
        'order_nonidentity': not np.array_equal(order, np.arange(a.shape[0])),
        'tail_all_zero': bool(split['tail']) and summary['T']['nnz'] == 0,
        'variants': list(VARIANTS)}


def smoke_cases(dest: Path) -> list[dict]:
    cases = []
    sources = json.loads((ROOT / 'results/hv/smoke_preparation.json').read_text())
    assert sources['passed']
    bases = [ROOT / case['root'] / 'H-V' for case in sources['cases']]
    bases.append(ROOT / 'cases_hc/smoke_tail_all_zero/N33/H-C')
    for base in bases:
        meta = verify_case(base)
        m, k, n, stride, _, _, _, _ = map(int, (base / 'config.txt').read_text().split())
        a = Matrix(np.fromfile(base / 'ptr.bin', np.int32), np.fromfile(base / 'cols.bin', np.int32),
                   np.fromfile(base / 'values.bin', np.float16), (m, k))
        order = np.asarray(meta['order'], np.int32)
        b = np.fromfile(base / 'rhs.bin', np.float16).reshape(k + 1, stride)[:k, :n]
        gold = np.fromfile(base / 'golden.bin', np.float32).reshape(m, stride)[:, :n]
        name = base.parent.parent.name.removeprefix('smoke_')
        cases.append(_smoke_export(name, a, order, meta['split'], b, gold,
            {'kind': meta['kind'], 'reused_metadata_sha256': digest(base / 'metadata.json'),
             'reused_source': str(base.relative_to(ROOT))}, dest))
    for kind in ('T0_mixed', 'noncontiguous_B_tail_index'):
        m, k, n = (17, 37, 33) if kind == 'T0_mixed' else (20, 37, 33)
        rng = np.random.default_rng(61000 + m)
        dense = np.zeros((m, k), np.float16)
        dense[:, :5] = rng.uniform(-1, 1, (m, 5)).astype(np.float16)
        if kind == 'T0_mixed':
            order = np.arange(m, dtype=np.int32)[::-1].copy()
            split = {'groups': [order[:16].tolist()], 'residual': [0], 'tail': [], 'zeros': [], 'w': 16, 'tau_nnz': 4, 'tau_inc': 2}
            dense[int(order[0]), :] = rng.uniform(-1, 1, k).astype(np.float16)
        else:
            tail, residual = [0, 7, 15], [9]
            group = [r for r in range(m - 1, -1, -1) if r not in tail + residual]
            order = np.asarray(group + residual + tail, np.int32)
            split = {'groups': [group], 'residual': residual, 'tail': tail, 'zeros': [], 'w': 16, 'tau_nnz': 4, 'tau_inc': 2}
            # R rows still reference B rows whose numeric indices also occur in T.
            dense[group[0], tail] = [.5, -.75, .875]
            dense[residual[0], tail] = [.25, .625, -.5]
        c = csr_matrix(dense.astype(np.float32))
        a = Matrix(c.indptr.astype(np.int32), c.indices.astype(np.int32), c.data.astype(np.float16), c.shape)
        b = rng.uniform(-1, 1, (k, n)).astype(np.float16)
        gold = (dense.astype(np.float64) @ b.astype(np.float64)).astype(np.float32)
        cases.append(_smoke_export(kind, a, order, split, b, gold, {'kind': kind}, dest))
    assert len(cases) == 16 and any(c['empty_R'] for c in cases)
    assert any(c['tail_empty'] and c['cube_groups'] and c['srows'] for c in cases)
    assert any(c['R_noncontiguous'] and c['srows'] for c in cases)
    save(dest / 'smoke_preparation.json', {'passed': True, 'variants': list(VARIANTS),
        'reused_hv_cases': len(sources['cases']), 'cases': cases})
    return cases
