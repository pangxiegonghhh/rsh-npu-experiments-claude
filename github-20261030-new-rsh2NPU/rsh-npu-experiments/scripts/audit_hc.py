"""Independently audit H-C provenance, frozen routing, and all raw timings."""
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

VARIANTS = ['V0', 'V2', 'H-V', 'H-C']
KEYS = ['v0', 'v2', 'hv', 'hc']
NULLS = [('SNAP_ca-HepTh', 64), ('SNAP_web-NotreDame', 64), ('Schmid_thermal1', 256)]


def resolve_case_alias(path: Path) -> Path:
    """Read control metadata canonically when compact archives omit symlinks."""
    try:
        parts = path.relative_to(ROOT).parts
    except ValueError:
        return path
    controls = {'V0': 'cases_v0', 'V2': 'cases_v2', 'H-V': 'cases_hv'}
    if len(parts) >= 4 and parts[0] == 'cases_hc' and parts[3] in controls:
        return ROOT/controls[parts[3]]/Path(*parts[1:])
    return path


def read(path: Path) -> dict:
    return json.loads(resolve_case_alias(path).read_text())


def array_digest(array: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest()


def validate(x: dict, variants: list[str], repeats: int = 30, warmups: int = 10) -> None:
    assert x['correctness'] and x['warmups'] == warmups and x['repeats'] == repeats
    assert [r['variant'] for r in x['records']] == variants
    if warmups == 10:
        assert x['cores_aic'] == 24 and x['cores_aiv'] == 48 and x['b_rotation'] == 2
        assert x['interleaving'] == 'randomized_per_call'
        assert x['timer'] == 'resident_synchronized_full_call_us'
    assert x['mixed_dispatch'] == 'native_mix_1_2_not_yet_profiled'
    for record in x['records']:
        assert record['valid_rows'] == record['m']
        assert len(record['samples_us']) == repeats
        assert all(math.isfinite(t) and t > 0 for t in record['samples_us'])
        assert math.isfinite(record['max_abs_error']) and record['max_abs_error'] >= 0


def verify_threshold_decision(dest: Path, mf: dict, rule: dict, summary: dict,
                              result: dict, rows: list[dict], null_medians: list[float],
                              dev_ratios: list[float]) -> None:
    decision = result['threshold_decision']
    # Independently check the saved decision against the raw measurements and
    # the rule declared before any H-C device measurements.
    assert summary['development_matrices'] == rule['development_matrices'] == mf['protocol']['development_matrices']
    assert summary['development_n'] == rule['n'] == 64
    assert decision['version'] == 'H-C' and decision['stop_before'] == 'H-Skip'
    assert decision['rule_sha256'] == digest(dest/'prospective_threshold_rule.json') == mf['prospective_threshold_rule_sha256']
    assert decision['historical_hv_threshold_decision_sha256'] == digest(ROOT/'results/hv/threshold_decision.json')
    np.testing.assert_allclose(decision['null_process_median_ratios'], null_medians, rtol=1e-12, atol=0)
    assert math.isclose(decision['null_process_noise_guard'], result['null_process_noise_guard'], rel_tol=1e-12, abs_tol=0)
    np.testing.assert_allclose(decision['development_hv_over_hc_per_process'], dev_ratios, rtol=1e-12, atol=0)
    assert decision['development_all_three_faster'] == result['development_all_three_faster']
    switch = result['development_strategy_switch_above_null_guard']
    assert decision['development_strategy_switch_above_null_guard'] == switch
    strongest_all = all(row['v0_all_three_faster'] and row['v2_all_three_faster'] for row in rows)
    assert decision['default_consistently_beats_strongest_control_at_all_points'] == strongest_all
    assert decision['grid_required'] == (switch and not strongest_all)
    if not decision['grid_required']:
        assert decision['resolved'] is True and decision['grid_complete'] is False
        assert decision['default_retained'] is True
        assert decision['selected_public_configuration'] == {'tau_nnz': 4, 'tau_inc': 2}
        assert not any((dest/'grid').rglob('run*.json')), 'Untriggered H-C grid measurements exist'
        assert not any((ROOT/'cases_hc_grid').rglob('metadata.json')), 'Untriggered H-C grid cases exist'
    else:
        raise AssertionError('Triggered H-C grid requires a dedicated independently checked grid audit before completion')


def audit() -> dict:
    dest = ROOT/'results/hc'
    state = read(dest/'progress.json')
    assert state['state'] == 'complete' and state['next_version'] == 'H-Skip' and state['stop_required']
    mf = read(dest/'manifest.json')
    matrix_names = sorted(Path(name).stem for name in mf['inputs'])
    expected = {f'paired/{name}/N{n}/run{rep}' for name in matrix_names for n in [16, 64, 256] for rep in range(3)}
    expected |= {f'null/{name}/N{n}/run{rep}' for name, n in NULLS for rep in range(3)}
    assert len(state['completed']) == len(set(state['completed'])) == len(expected) == 81
    assert set(state['completed']) == expected
    assert len(state['prepared']) == len(set(state['prepared'])) == 24
    assert set(state['prepared']) == {f'{name}/N{n}' for name in matrix_names for n in [16, 64, 256]}
    assert mf['protocol']['stop_before'] == 'H-Skip'
    assert digest(dest/'prospective_threshold_rule.json') == mf['prospective_threshold_rule_sha256']
    rule = read(dest/'prospective_threshold_rule.json')
    assert rule['declared_before_hc_device_measurements'] and rule['stop_before'] == 'H-Skip'
    assert mf['protocol']['tau_nnz'] == 4 and mf['protocol']['tau_inc'] == 2
    snap = dest/'source_snapshot'
    for name, sha in mf['source_hashes'].items():
        assert digest(snap/name) == sha, name
    assert digest(snap/'scripts/run_hc.py') == mf['controller_sha256']
    assert digest(ROOT/'results/v0/device_binary/rsh_runner') == mf['executable_sha256']
    assert digest(ROOT/'results/hv/manifest.json') == mf['hv_manifest_sha256']
    assert digest(ROOT/'results/hv/mixed_validation.json') == mf['hv_mixed_validation_sha256']
    hv_manifest = read(ROOT/'results/hv/manifest.json')
    assert mf['executable_sha256'] == hv_manifest['executable_sha256']
    validation = read(ROOT/'results/hv/mixed_validation.json')
    assert validation['passed'] and validation['executable_sha256'] == mf['executable_sha256']
    profile = ROOT/validation['profile_summary']
    assert digest(profile) == validation['profile_summary_sha256']
    with profile.open() as stream:
        mixed = [r for r in csv.DictReader(stream) if r['Op Name'] == 'rsh_mix']
    assert len(mixed) == 5
    for row in mixed:
        assert row['Task Type'] == 'MIX_AIC' and int(row['Block Num']) == 24 and int(row['Mix Block Num']) == 48
        assert float(row['aic_mac_time(us)']) > 0 and float(row['aiv_vec_time(us)']) > 0
    # Metadata/config hashes can be checked in the compact archive without GB-sized binaries.
    frozen = read(dest/'case_manifest.json')
    assert frozen['manifest_sha256'] == digest(dest/'manifest.json') and frozen['configuration_count'] == 24
    for name, sha in frozen['files'].items():
        assert digest(resolve_case_alias(ROOT/name)) == sha, name
    for name, hashes in frozen['binary_files'].items():
        assert read(ROOT/name/'metadata.json')['files_sha256'] == hashes, name
    smoke = read(dest/'smoke_preparation.json')['cases']
    assert len(smoke) == frozen['smoke_cases'] == state['smoke_cases']
    expected_smoke = {f'{case["name"]}_C{cores}.json' for case in smoke for cores in [1, 24]}
    smoke_files = {p.name for p in (dest/'smoke').glob('*.json') if '.pending-' not in p.name}
    assert smoke_files == expected_smoke and state['smoke_checks'] == len(expected_smoke)
    for case in smoke:
        for cores in [1, 24]:
            x = read(dest/'smoke'/f'{case["name"]}_C{cores}.json')
            validate(x, ['H-C'], repeats=2, warmups=1)
            assert x['cores_aic_budget'] == cores
            assert x['records'][0]['m'] == case['m'] and x['records'][0]['n'] == case['n']
    expected_null = {f'{name}_N{n}_run{rep}.json' for name, n in NULLS for rep in range(3)}
    assert {p.name for p in (dest/'null_control').glob('*.json') if '.pending-' not in p.name} == expected_null
    null_ratios = []
    null_medians = []
    null_by_rep = {rep: [] for rep in range(3)}
    for name, n in NULLS:
        for rep in range(3):
            x = read(dest/'null_control'/f'{name}_N{n}_run{rep}.json')
            validate(x, ['H-C', 'H-C'])
            a, b = x['records']
            assert a['n'] == b['n'] == n and a['m'] == b['m']
            ratios = np.asarray(a['samples_us'])/np.asarray(b['samples_us'])
            med = float(np.median(ratios))
            null_ratios.extend(ratios.tolist())
            null_medians.append(med)
            null_by_rep[rep].append(med)
    low, high = map(float, np.quantile(null_ratios, [.05, .95]))
    null_aggregates = [math.exp(statistics.mean(math.log(t) for t in null_by_rep[rep])) for rep in range(3)]
    structures = []
    for input_name, sha in mf['inputs'].items():
        source = ROOT/'inputs'/input_name
        assert digest(source) == sha
        matrix = source.stem
        a = Matrix.load(str(source))
        hvpd = ROOT/'results/hv/plans'/matrix
        routepath = hvpd/'routing.json'
        route = read(routepath)
        assert digest(routepath) == mf['hv_routes'][matrix]
        assert route['input_sha256'] == sha
        orderpath = ROOT/'results/v2/orders'/matrix/'order.bin'
        assert digest(orderpath) == mf['orders'][matrix] == route['order_sha256']
        order = np.fromfile(orderpath, np.int32)
        assert np.array_equal(np.sort(order), np.arange(a.shape[0]))
        split = route['split']
        check_split(a, split)
        assert split['tau_nnz'] == 4 and split['tau_inc'] == 2 and split['w'] == 16
        pd = dest/'plans'/matrix
        assert read(pd/'routing.json') == route, matrix
        assert digest(pd/'routing.json') == digest(routepath), matrix
        raw = read(pd/'structure.json')
        hvs = read(hvpd/'structure.json')
        plan = layout(a, order, split, 'H-C')
        nnz = np.diff(a.ptr)
        def rowstats(rows: list[int]) -> dict:
            return {'rows': len(rows), 'nnz': int(nnz[rows].sum()) if rows else 0,
                    'zero_rows': int(np.sum(nnz[rows] == 0)) if rows else 0}
        groups = [r for group in split['groups'] for r in group]
        parts = {'G': rowstats(groups), 'S': rowstats(split['residual']),
                 'T': rowstats(split['tail']), 'Z': rowstats(split['zeros'])}
        for label, counts in parts.items():
            assert hvs[label] == counts
            if label in raw:
                assert raw[label] == counts
        assert sum(x['rows'] for x in parts.values()) == a.shape[0]
        assert sum(x['nnz'] for x in parts.values()) == len(a.col)
        expected_groups = len(split['groups'])+bool(split['tail'])
        assert raw['cube_groups'] == len(plan['cube_ptr'])-1 == expected_groups
        assert raw['k16_tiles'] == len(plan['tiles']) and raw['aiv_rows'] == len(split['residual'])
        tailtiles = len(plan['tiles'])-hvs['k16_tiles']
        assert tailtiles >= 0 and len(plan['colref'])-hvs['b_gather_rows_per_call'] == tailtiles*16
        stats = dict(raw)
        stats.update(parts)
        stats.update(matrix=matrix, m=a.shape[0], k=a.shape[1], nnz=len(a.col),
                     hv_cube_groups=hvs['cube_groups'], hv_k16_tiles=hvs['k16_tiles'],
                     hv_aiv_rows=hvs['aiv_rows'], tail_cube_groups=int(bool(split['tail'])),
                     tail_k16_tiles=tailtiles,
                     tail_padding_rows=16-len(split['tail']) if split['tail'] else 0,
                     tail_added_physical_slots=tailtiles*256,
                     hv_b_gather_rows_per_call=hvs['b_gather_rows_per_call'],
                     b_gather_rows_per_call=len(plan['colref']),
                     tail_b_gather_rows_per_call=tailtiles*16,
                     routing_sha256=digest(routepath), order_sha256=digest(orderpath),
                     reused_v2_order_seconds=hvs['reused_v2_order_seconds'],
                     hv_partition_seconds=hvs['partition_seconds'])
        for n in [16, 64, 256]:
            metas = [read(ROOT/'cases_hc'/matrix/f'N{n}'/variant/'metadata.json') for variant in VARIANTS]
            for variant, meta in zip(VARIANTS, metas):
                assert meta['variant'] == variant and meta['coverage'] == 'full' and meta['tail_skip_rows'] == []
                for key in ['ptr', 'cols', 'values', 'rhs', 'golden']:
                    assert meta['files_sha256'][key] == metas[0]['files_sha256'][key]
            hc = metas[3]
            for key in ['cube_ptr', 'colref', 'tiles', 'rowmap', 'srows', 'valid']:
                assert hc['files_sha256'][key] == array_digest(plan[key]), (matrix, n, key)
            for key, arr in [('ptr', a.ptr), ('cols', a.col), ('values', a.val)]:
                assert hc['files_sha256'][key] == array_digest(arr)
            for key in ['cube_groups', 'k16_tiles', 'aiv_rows']:
                assert hc[key] == stats[key], (matrix, n, key)
        structures.append(stats)
    summary = read(dest/'summary.json')
    assert summary['version'] == 'H-C' and summary['stop_before'] == 'H-Skip'
    assert len(summary['rows']) == 24
    assert {(r['matrix'], r['n']) for r in summary['rows']} == {(name, n) for name in matrix_names for n in [16, 64, 256]}
    rows, flags, maxerr = [], [], 0.
    for summary_row in summary['rows']:
        name, n = summary_row['matrix'], summary_row['n']
        meds = [[], [], [], []]
        samples = [[], [], [], []]
        ratios = [[], [], []]
        stats = next(s for s in structures if s['matrix'] == name)
        for rep in range(3):
            x = read(dest/'measurements'/name/f'N{n}'/f'run{rep}.json')
            validate(x, VARIANTS)
            for i, record in enumerate(x['records']):
                assert record['m'] == stats['m'] and record['k'] == stats['k'] and record['n'] == n
                meds[i].append(float(np.median(record['samples_us'])))
                samples[i].extend(record['samples_us'])
            hc = x['records'][3]
            for key in ['cube_groups', 'k16_tiles', 'aiv_rows']:
                assert hc[key] == stats[key]
            hv = x['records'][2]
            assert hv['cube_groups'] == stats['hv_cube_groups'] and hv['k16_tiles'] == stats['hv_k16_tiles']
            assert hv['aiv_rows'] == stats['hv_aiv_rows']
            maxerr = max(maxerr, hc['max_abs_error'])
            for i in range(3):
                ratios[i].append(float(np.median(np.asarray(x['records'][i]['samples_us'])/np.asarray(hc['samples_us']))))
        row = dict(summary_row)
        assert row['hc_max_abs_error'] == max(read(dest/'measurements'/name/f'N{n}'/f'run{rep}.json')['records'][3]['max_abs_error'] for rep in range(3))
        for i, key in enumerate(KEYS):
            assert meds[i] == row[key+'_process_medians_us']
            assert statistics.median(meds[i]) == row[key+'_median_us']
            row[key+'_iqr_us'] = float(np.subtract(*np.quantile(samples[i], [.75, .25])))
            row[key+'_process_max_min'] = max(meds[i])/min(meds[i])
        for i, key in enumerate(KEYS[:3]):
            np.testing.assert_allclose(ratios[i], row[key+'_over_hc_per_process'], rtol=1e-12)
            assert statistics.median(ratios[i]) == row[key+'_over_hc']
            row[key+'_all_three_faster'] = all(t > 1 for t in ratios[i])
            row[key+'_all_three_slower'] = all(t < 1 for t in ratios[i])
            row[key+'_gain_above_null_envelope'] = all(t > high for t in ratios[i])
        if max(row[key+'_process_max_min'] for key in KEYS) > 1.10:
            flags.append({'matrix': name, 'n': n, **{key: row[key+'_process_max_min'] for key in KEYS}})
        rows.append(row)
    decision = read(dest/'threshold_decision.json')
    assert decision['resolved'], 'Threshold follow-up is not resolved'
    result = {'passed': True, 'version': 'H-C', 'configurations': 24, 'paired_processes': 72,
              'null_processes': 9, 'smoke_cases': len(smoke), 'smoke_checks': len(expected_smoke),
              'samples_per_variant': 2160, 'hc_max_abs_error': maxerr,
              'null_ratio_p05_p95': [low, high],
              'null_process_median_range': [min(null_medians), max(null_medians)],
              'null_process_noise_guard': max([1.] + null_medians + [1./t for t in null_medians]),
              'null_process_aggregate_ratios': null_aggregates,
              'null_process_aggregate_range': [min(null_aggregates), max(null_aggregates)],
              'rows': rows, 'structure': structures, 'timing_flags': flags,
              'mixed_validation_reused_from': 'results/hv/mixed_validation.json',
              'threshold_decision': decision, 'next_version': 'H-Skip', 'stop_required': True,
              'limits': 'Controlled full-output backend; approximate shared-column order. H-V/H-C measures total tail-policy impact, not isolated tail cost. Native mixed executable/profile reused; exact overlap fraction unresolved. CPU/H2D excluded. No strong library or Neutron baseline. All timing samples retained; noise diagnostics are descriptive.'}
    for key in KEYS[:3]:
        result[key+'_over_hc_geomean'] = math.exp(statistics.mean(math.log(r[key+'_over_hc']) for r in rows))
        for metric in ['all_three_faster', 'all_three_slower', 'gain_above_null_envelope']:
            result[key+'_'+metric] = sum(r[key+'_'+metric] for r in rows)
    dev = summary['development_matrices']
    dev_ratios = [math.exp(statistics.mean(math.log(next(r for r in rows if r['matrix'] == name and r['n'] == 64)
                                                ['hv_over_hc_per_process'][rep]) for name in dev)) for rep in range(3)]
    np.testing.assert_allclose(dev_ratios, summary['development_hv_over_hc_per_process'], rtol=1e-12)
    result['development_hv_over_hc_per_process'] = dev_ratios
    result['development_all_three_faster'] = all(t > 1 for t in dev_ratios)
    result['development_strategy_switch_above_null_guard'] = all(t > result['null_process_noise_guard'] for t in dev_ratios)
    result['prospective_threshold_rule'] = rule
    verify_threshold_decision(dest, mf, rule, summary, result, rows, null_medians, dev_ratios)
    result['threshold_decision_audit_passed'] = True
    save(dest/'local_audit.json', result)
    print(json.dumps({k: v for k, v in result.items() if k not in ['rows', 'structure', 'threshold_decision']}, ensure_ascii=False))
    return result


if __name__ == '__main__':
    audit()
