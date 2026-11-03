"""Independently audit same-R H-Skip, frozen routes, and all raw measurements."""
from __future__ import annotations
from pathlib import Path
import csv
import hashlib
import json
import math
import statistics
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.hv_cases import digest, save, check_split
from rsh.planner import Matrix, layout

VARIANTS = ['V0', 'V2', 'H-V', 'H-C', 'V0-R', 'V2-R', 'H-Skip']
KEYS = ['v0', 'v2', 'hv', 'hc', 'v0r', 'v2r', 'skip']
PARTIAL = ['V0-R', 'V2-R', 'H-Skip']
PLAN_ARRAYS = ['cube_ptr', 'colref', 'tiles', 'rowmap', 'srows', 'valid']
NULLS = [('SNAP_ca-HepTh', 64), ('SNAP_web-NotreDame', 64), ('Schmid_thermal1', 256)]


def resolve_case_alias(path: Path) -> Path:
    try:
        parts = path.relative_to(ROOT).parts
    except ValueError:
        return path
    controls = {'V0': 'cases_v0', 'V2': 'cases_v2', 'H-V': 'cases_hv', 'H-C': 'cases_hc'}
    if len(parts) >= 4 and parts[0] == 'cases_skip' and parts[3] in controls:
        return ROOT/controls[parts[3]]/Path(*parts[1:])
    return path


def read(path: Path) -> dict:
    return json.loads(resolve_case_alias(path).read_text())


def adigest(array: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest()


def validate(x: dict, variants: list[str], valid_rows: list[int], repeats: int = 30,
             warmups: int = 10) -> None:
    assert x['correctness'] and x['warmups'] == warmups and x['repeats'] == repeats
    assert [r['variant'] for r in x['records']] == variants
    assert x['cores_aic_budget'] in (1, 24)
    assert x['cores_aic'] in (0, x['cores_aic_budget'])
    assert x['cores_aiv'] == 2*x['cores_aic_budget']
    if warmups == 10:
        assert x['cores_aic_budget'] == 24 and x['b_rotation'] == 2
        assert x['interleaving'] == 'randomized_per_call'
        assert x['timer'] == 'resident_synchronized_full_call_us'
    assert x['mixed_dispatch'] == 'native_mix_1_2_not_yet_profiled'
    for r, expected in zip(x['records'], valid_rows):
        assert r['valid_rows'] == expected and 0 <= expected <= r['m']
        assert len(r['samples_us']) == repeats
        assert all(math.isfinite(t) and t > 0 for t in r['samples_us'])
        assert math.isfinite(r['max_abs_error']) and r['max_abs_error'] >= 0
    assert len({r['valid_rows'] for r in x['records'] if r['variant'] in PARTIAL}) <= 1


def verify_plans(a: Matrix, order: np.ndarray, split: dict, base: Path,
                 variants: list[str]) -> dict[str, dict]:
    """Rebuild every layout, even when compact recovery omits GB-sized binaries."""
    tail = sorted(split['tail'])
    valid = np.ones(a.shape[0], np.uint8)
    valid[tail] = 0
    restricted_order = [int(r) for r in order if valid[r]]
    metas = {}
    for variant in variants:
        path = base/variant
        meta = read(path/'metadata.json')
        plan = layout(a, order, split, variant)
        assert meta['variant'] == variant
        expected_tail = tail if variant in PARTIAL else []
        assert meta['tail_skip_rows'] == expected_tail
        assert meta['coverage'] == ('retained_rows_only' if expected_tail else 'full')
        for key in PLAN_ARRAYS:
            assert meta['files_sha256'][key] == adigest(plan[key]), (path, key)
        for key, arr in [('ptr', a.ptr), ('cols', a.col), ('values', a.val)]:
            assert meta['files_sha256'][key] == adigest(arr), (path, key)
        config = list(map(int, resolve_case_alias(path/'config.txt').read_text().split()))
        assert config == [a.shape[0], a.shape[1], config[2], ((config[2]+15)//16)*16,
                          len(a.col), len(plan['cube_ptr'])-1, len(plan['tiles']), len(plan['srows'])]
        if variant in PARTIAL:
            assert np.array_equal(plan['valid'], valid)
            assert meta.get('included_rows', int(valid.sum())) == int(valid.sum())
            if 'retained_original_rows' in meta:
                assert meta['retained_original_rows'] == np.flatnonzero(valid).tolist()
                assert meta['tail_original_rows'] == split['tail']
                assert meta['retained_v2_order'] == restricted_order
        if variant == 'H-Skip':
            assert plan['rowmap'][plan['rowmap'] >= 0].tolist() == [r for group in split['groups'] for r in group]
            assert plan['srows'].tolist() == split['residual']
        if variant == 'V0-R':
            assert plan['srows'].tolist() == np.flatnonzero(valid).tolist()
        if variant == 'V2-R':
            assert plan['rowmap'][plan['rowmap'] >= 0].tolist() == restricted_order
        for key in ['cube_groups', 'k16_tiles', 'aiv_rows']:
            expected = {'cube_groups': len(plan['cube_ptr'])-1, 'k16_tiles': len(plan['tiles']),
                        'aiv_rows': len(plan['srows'])}[key]
            if key in meta:
                assert meta[key] == expected, (path, key)
        metas[variant] = meta
    for key in ['ptr', 'cols', 'values', 'rhs', 'golden']:
        assert len({meta['files_sha256'][key] for meta in metas.values()}) == 1, (base, key)
    partial_hashes = {meta['files_sha256']['valid'] for variant, meta in metas.items() if variant in PARTIAL}
    assert len(partial_hashes) <= 1
    if 'H-V' in metas and 'H-Skip' in metas:
        for key in ['cube_ptr', 'colref', 'tiles', 'rowmap']:
            assert metas['H-V']['files_sha256'][key] == metas['H-Skip']['files_sha256'][key]
    return metas


def audit() -> dict:
    dest = ROOT/'results/skip'
    state, mf = read(dest/'progress.json'), read(dest/'manifest.json')
    assert state['state'] == 'complete' and state['next_version'] == 'none' and state['stop_required']
    assert state['completed_main_versions'] == 6
    names = sorted(Path(name).stem for name in mf['inputs'])
    assert len(names) == 8
    expected = {f'paired/{name}/N{n}/run{rep}' for name in names for n in [16, 64, 256] for rep in range(3)}
    expected |= {f'null/{name}/N{n}/run{rep}' for name, n in NULLS for rep in range(3)}
    assert len(state['completed']) == len(set(state['completed'])) == len(expected) == 81
    assert set(state['completed']) == expected
    assert len(state['prepared']) == len(set(state['prepared'])) == 24
    assert set(state['prepared']) == {f'{name}/N{n}' for name in names for n in [16, 64, 256]}
    protocol = mf['protocol']
    assert protocol['variants'] == VARIANTS and protocol['next_version'] == 'none' and protocol['stop_required']
    assert (protocol['w'], protocol['tau_nnz'], protocol['tau_inc']) == (16, 4, 2)
    assert 'cannot select thresholds' in protocol['threshold']
    snap = dest/'source_snapshot'
    for name, sha in mf['source_hashes'].items():
        assert digest(snap/name) == sha, name
    assert digest(snap/'scripts/run_skip.py') == mf['controller_sha256']
    assert digest(ROOT/'results/v0/device_binary/rsh_runner') == mf['executable_sha256']
    for previous in ['hv', 'hc']:
        assert digest(ROOT/f'results/{previous}/manifest.json') == mf[previous+'_manifest_sha256']
        assert digest(ROOT/f'results/{previous}/threshold_decision.json') == mf[previous+'_threshold_decision_sha256']
        assert read(ROOT/f'results/{previous}/manifest.json')['executable_sha256'] == mf['executable_sha256']
    assert digest(ROOT/'results/hv/mixed_validation.json') == mf['hv_mixed_validation_sha256']
    validation = read(ROOT/'results/hv/mixed_validation.json')
    assert validation['passed'] and validation['executable_sha256'] == mf['executable_sha256']
    profile = ROOT/validation['profile_summary']
    assert digest(profile) == validation['profile_summary_sha256']
    with profile.open() as stream:
        mixed = [r for r in csv.DictReader(stream) if r['Op Name'] == 'rsh_mix']
    assert len(mixed) == 5
    for r in mixed:
        assert r['Task Type'] == 'MIX_AIC' and int(r['Block Num']) == 24 and int(r['Mix Block Num']) == 48
        assert float(r['aic_mac_time(us)']) > 0 and float(r['aiv_vec_time(us)']) > 0
    frozen = read(dest/'case_manifest.json')
    assert frozen['manifest_sha256'] == digest(dest/'manifest.json') and frozen['configuration_count'] == 24
    for name, sha in frozen['files'].items():
        assert digest(resolve_case_alias(ROOT/name)) == sha, name
    for name, hashes in frozen['binary_files'].items():
        assert read(ROOT/name/'metadata.json')['files_sha256'] == hashes, name
    smoke = read(dest/'smoke_preparation.json')['cases']
    assert len(smoke) == frozen['smoke_cases'] == state['smoke_cases']
    expected_smoke = {f'{c["name"]}_C{cores}.json' for c in smoke for cores in [1, 24]}
    assert {p.name for p in (dest/'smoke').glob('*.json') if '.pending-' not in p.name} == expected_smoke
    assert state['smoke_checks'] == len(expected_smoke)
    assert state['smoke_variant_checks'] == len(expected_smoke)*3
    empty_r_checks = 0
    smoke_maxerr = 0.
    for case in smoke:
        base = ROOT/case['root']
        meta = read(base/'H-Skip'/'metadata.json')
        # Tiny smoke CSR snapshots remain inside results for compact recovery.
        config = list(map(int, (base/'H-Skip'/'config.txt').read_text().split()))
        m, k, n = config[:3]
        input_path = ROOT/case['input']
        assert digest(input_path) == case['input_sha256']
        with np.load(input_path) as z:
            a = Matrix(z['ptr'].astype(np.int32), z['cols'].astype(np.int32),
                       z['values'].astype(np.float16), tuple(map(int, z['shape'])))
        assert a.shape == (m, k)
        assert (m, n) == (case['m'], case['n'])
        split = meta['split']
        check_split(a, split)
        order = np.asarray(meta['order'], np.int32)
        assert np.array_equal(np.sort(order), np.arange(m))
        verify_plans(a, order, split, base, PARTIAL)
        kept = m-len(split['tail'])
        for cores in [1, 24]:
            x = read(dest/'smoke'/f'{case["name"]}_C{cores}.json')
            validate(x, PARTIAL, [kept]*3, repeats=2, warmups=1)
            assert x['cores_aic_budget'] == cores
            if not kept:
                empty_r_checks += 1
            for r in x['records']:
                assert (r['m'], r['k'], r['n']) == (m, k, n)
                smoke_maxerr = max(smoke_maxerr, r['max_abs_error'])
    expected_null = {f'{name}_N{n}_run{rep}.json' for name, n in NULLS for rep in range(3)}
    assert {p.name for p in (dest/'null_control').glob('*.json') if '.pending-' not in p.name} == expected_null
    structures = []
    for input_name, sha in mf['inputs'].items():
        source = ROOT/'inputs'/input_name
        assert digest(source) == sha
        name = source.stem
        a = Matrix.load(str(source))
        routepath = ROOT/'results/hv/plans'/name/'routing.json'
        route = read(routepath)
        assert digest(routepath) == mf['hv_routes'][name]
        assert digest(dest/'plans'/name/'routing.json') == digest(routepath)
        assert route['input_sha256'] == sha
        orderpath = ROOT/'results/v2/orders'/name/'order.bin'
        assert digest(orderpath) == mf['orders'][name] == route['order_sha256']
        order = np.fromfile(orderpath, np.int32)
        assert np.array_equal(np.sort(order), np.arange(a.shape[0]))
        split = route['split']
        check_split(a, split)
        assert (split['w'], split['tau_nnz'], split['tau_inc']) == (16, 4, 2)
        nnz = np.diff(a.ptr)
        def stats(rows: list[int]) -> dict:
            return {'rows': len(rows), 'nnz': int(nnz[rows].sum()) if rows else 0,
                    'zero_rows': int(np.sum(nnz[rows] == 0)) if rows else 0}
        retained = sorted(set(range(a.shape[0]))-set(split['tail']))
        raw = read(dest/'plans'/name/'structure.json')
        assert raw['retained_original_rows'] == retained
        assert raw['tail_original_rows'] == split['tail']
        retained_set = set(retained)
        assert raw['retained_v2_order'] == [int(r) for r in order if r in retained_set]
        assert raw['reorder_rerun'] is False and raw['partition_rerun'] is False
        parts = {'G': stats([r for g in split['groups'] for r in g]), 'S': stats(split['residual']),
                 'T': stats(split['tail']), 'Z': stats(split['zeros']), 'R': stats(retained)}
        for key, values in parts.items():
            for field, value in values.items():
                assert raw[key][field] == value, (name, key, field)
        assert parts['R']['rows']+parts['T']['rows'] == a.shape[0]
        assert parts['R']['nnz']+parts['T']['nnz'] == len(a.col)
        structure = dict(raw)
        structure.update(matrix=name, m=a.shape[0], k=a.shape[1], nnz=len(a.col),
                         tail_row_fraction=len(split['tail'])/a.shape[0],
                         tail_nnz_fraction=parts['T']['nnz']/len(a.col) if len(a.col) else 0.)
        for n in [16, 64, 256]:
            metas = verify_plans(a, order, split, ROOT/'cases_skip'/name/f'N{n}', VARIANTS)
            for variant in PARTIAL:
                assert metas[variant]['routing_sha256'] == digest(routepath)
                assert metas[variant]['order_sha256'] == digest(orderpath)
        structures.append(structure)
    null_ratios, null_medians = [], []
    for name, n in NULLS:
        kept = next(s for s in structures if s['matrix'] == name)['R']['rows']
        for rep in range(3):
            x = read(dest/'null_control'/f'{name}_N{n}_run{rep}.json')
            validate(x, ['H-Skip', 'H-Skip'], [kept, kept])
            assert all(r['n'] == n for r in x['records'])
            ratios = np.asarray(x['records'][0]['samples_us'])/np.asarray(x['records'][1]['samples_us'])
            null_ratios.extend(ratios.tolist())
            null_medians.append(float(np.median(ratios)))
    low, high = map(float, np.quantile(null_ratios, [.05, .95]))
    summary = read(dest/'summary.json')
    assert summary['version'] == 'H-Skip' and summary['next_version'] == 'none' and summary['stop_required']
    assert summary['threshold_tuning_allowed'] is False
    assert summary['same_r_ratios'] == ['v0r_over_skip', 'v2r_over_skip']
    assert summary['optimistic_full_ratios'] == ['v0_over_skip', 'v2_over_skip', 'hv_over_skip', 'hc_over_skip']
    assert len(summary['rows']) == 24
    assert {(r['matrix'], r['n']) for r in summary['rows']} == {(name, n) for name in names for n in [16, 64, 256]}
    expected_measures = {dest/'measurements'/name/f'N{n}'/f'run{rep}.json' for name in names for n in [16,64,256] for rep in range(3)}
    assert {p for p in (dest/'measurements').rglob('run*.json') if '.pending-' not in p.name} == expected_measures
    rows, flags, maxerr, per_variant_errors = [], [], 0., {key: 0. for key in KEYS}
    for summary_row in summary['rows']:
        name, n = summary_row['matrix'], summary_row['n']
        structure = next(s for s in structures if s['matrix'] == name)
        kept = structure['R']['rows']
        meds, samples, ratios = [[] for _ in KEYS], [[] for _ in KEYS], [[] for _ in KEYS[:-1]]
        skip_errors = []
        for rep in range(3):
            x = read(dest/'measurements'/name/f'N{n}'/f'run{rep}.json')
            validate(x, VARIANTS, [structure['m']]*4+[kept]*3)
            for i, record in enumerate(x['records']):
                assert (record['m'], record['k'], record['n']) == (structure['m'], structure['k'], n)
                meds[i].append(float(np.median(record['samples_us'])))
                samples[i].extend(record['samples_us'])
                per_variant_errors[KEYS[i]] = max(per_variant_errors[KEYS[i]], record['max_abs_error'])
                if record['variant'] in PARTIAL:
                    expected_variant = structure['variants'][record['variant']]
                    for key in ['cube_groups', 'k16_tiles', 'aiv_rows']:
                        assert record[key] == expected_variant[key], (name, n, key)
            skip = x['records'][-1]
            skip_errors.append(skip['max_abs_error'])
            maxerr = max(maxerr, skip['max_abs_error'])
            for i in range(len(KEYS)-1):
                ratios[i].append(float(np.median(np.asarray(x['records'][i]['samples_us'])/np.asarray(skip['samples_us']))))
        row = dict(summary_row)
        assert row['skip_max_abs_error'] == max(skip_errors)
        assert row['m'] == structure['m'] and row['valid_rows'] == kept and row['tail_rows'] == structure['T']['rows']
        for i, key in enumerate(KEYS):
            assert meds[i] == row[key+'_process_medians_us']
            assert statistics.median(meds[i]) == row[key+'_median_us']
            row[key+'_iqr_us'] = float(np.subtract(*np.quantile(samples[i], [.75, .25])))
            row[key+'_process_max_min'] = max(meds[i])/min(meds[i])
        for i, key in enumerate(KEYS[:-1]):
            np.testing.assert_allclose(ratios[i], row[key+'_over_skip_per_process'], rtol=1e-12)
            assert statistics.median(ratios[i]) == row[key+'_over_skip']
            row[key+'_all_three_faster'] = all(t > 1 for t in ratios[i])
            row[key+'_all_three_slower'] = all(t < 1 for t in ratios[i])
            row[key+'_gain_above_null_envelope'] = all(t > high for t in ratios[i])
        if max(row[key+'_process_max_min'] for key in KEYS) > 1.10:
            flags.append({'matrix': name, 'n': n, **{key: row[key+'_process_max_min'] for key in KEYS}})
        rows.append(row)
    result = {'passed': True, 'version': 'H-Skip', 'completed_main_versions': 6,
              'configurations': 24, 'paired_processes': 72, 'null_processes': 9,
              'smoke_cases': len(smoke), 'smoke_checks': len(expected_smoke),
              'smoke_variant_checks': len(expected_smoke)*3, 'empty_r_smoke_processes': empty_r_checks,
              'empty_r_note': 'valid_rows=0 is an empty-scope smoke check, not nonempty numerical evidence',
              'samples_per_variant': 2160, 'total_main_samples': 15120,
              'skip_max_abs_error': maxerr, 'per_variant_max_abs_error': per_variant_errors,
              'smoke_max_abs_error': smoke_maxerr,
              'null_ratio_p05_p95': [low, high], 'null_process_median_range': [min(null_medians), max(null_medians)],
              'null_process_noise_guard': max([1.] + null_medians + [1./t for t in null_medians]),
              'rows': rows, 'structure': structures, 'timing_flags': flags,
              'same_r_ratios': summary['same_r_ratios'], 'optimistic_full_ratios': summary['optimistic_full_ratios'],
              'threshold_tuning_allowed': False, 'mixed_validation_reused_from': 'results/hv/mixed_validation.json',
              'next_version': 'none', 'stop_required': True,
              'limits': 'H-Skip/V0-R/V2-R compute same R only. Full-output/Skip ratios are optimistic diagnostic ratios, not complete SpMM speedups or rigorous upper bounds. Timing includes full-M output clearing and mapped restoration but excludes CPU preprocessing/first H2D. Controlled backend only, no Neutron/strong library baseline. Exact per-lane overlap fraction unknown. Six main versions completed is a stage boundary, not acceptance of end-to-end benefit. All samples retained; noise is descriptive.'}
    result['same_r'] = {}
    result['optimistic_full'] = {}
    for key in KEYS[:-1]:
        stats = {'geomean': math.exp(statistics.mean(math.log(r[key+'_over_skip']) for r in rows))}
        for metric in ['all_three_faster', 'all_three_slower', 'gain_above_null_envelope']:
            stats[metric] = sum(r[key+'_'+metric] for r in rows)
        result['same_r' if key in ['v0r', 'v2r'] else 'optimistic_full'][key+'_over_skip'] = stats
    save(dest/'local_audit.json', result)
    print(json.dumps({k: v for k, v in result.items() if k not in ['rows', 'structure']}, ensure_ascii=False))
    return result


if __name__ == '__main__':
    audit()
