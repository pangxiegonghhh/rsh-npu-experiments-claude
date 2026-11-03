"""Run only H-C, with frozen H-V routes and resumable atomic checkpoints."""
from __future__ import annotations

from pathlib import Path
import argparse
import json
import math
import random
import statistics
import subprocess
import sys
import time
import traceback

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.hv_cases import digest, save
from scripts.hc_cases import smoke_cases, prepare_real

VARIANTS = ['V0', 'V2', 'H-V', 'H-C']
WIDTHS = [16, 64, 256]
SEED = 20261018
NULLS = [('SNAP_ca-HepTh', 64), ('SNAP_web-NotreDame', 64), ('Schmid_thermal1', 256)]
DEVELOPMENT = ['SNAP_ca-HepTh', 'SNAP_email-Enron', 'HB_bcsstk17']


def read(path: Path) -> dict:
    return json.loads(path.read_text())


def validate_record(x: dict, variants: list[str], warmups: int, repeats: int) -> None:
    assert x['correctness'] and x['warmups'] == warmups and x['repeats'] == repeats
    assert [r['variant'] for r in x['records']] == variants
    assert x['cores_aic_budget'] in (1, 24) and x['cores_aic'] in (0, x['cores_aic_budget'])
    if warmups == 10:
        assert x['interleaving'] == 'randomized_per_call' and x['b_rotation'] == 2
        assert x['cores_aic'] == 24 and x['cores_aiv'] == 48
    for r in x['records']:
        assert len(r['samples_us']) == repeats
        assert all(math.isfinite(t) and t > 0 for t in r['samples_us'])
        assert math.isfinite(r['max_abs_error']) and r['max_abs_error'] >= 0
        assert r['valid_rows'] == r['m']


def summarize(dest: Path, files: list[Path]) -> dict:
    rows = []
    for source in files:
        for n in WIDTHS:
            xs = [read(dest/'measurements'/source.stem/f'N{n}'/f'run{rep}.json') for rep in range(3)]
            row = {'matrix': source.stem, 'n': n,
                   'hc_max_abs_error': max(x['records'][3]['max_abs_error'] for x in xs)}
            for i, name in enumerate(['v0', 'v2', 'hv', 'hc']):
                meds = [statistics.median(x['records'][i]['samples_us']) for x in xs]
                row[name+'_process_medians_us'] = meds
                row[name+'_median_us'] = statistics.median(meds)
            for i, name in enumerate(['v0', 'v2', 'hv']):
                ratios = [statistics.median(a/b for a, b in zip(x['records'][i]['samples_us'],
                                                               x['records'][3]['samples_us'])) for x in xs]
                row[name+'_over_hc_per_process'] = ratios
                row[name+'_over_hc'] = statistics.median(ratios)
            rows.append(row)
    dev = [math.exp(statistics.mean(math.log(next(r for r in rows if r['matrix'] == name and r['n'] == 64)
                                                ['hv_over_hc_per_process'][rep]) for name in DEVELOPMENT))
           for rep in range(3)]
    result = {'version': 'H-C', 'correctness': True, 'configurations': len(rows),
              'paired_processes': len(rows)*3, 'null_processes': 9, 'variants': VARIANTS,
              'rows': rows, 'development_matrices': DEVELOPMENT, 'development_n': 64,
              'development_hv_over_hc_per_process': dev,
              'development_all_three_faster': all(x > 1 for x in dev),
              'threshold_decision_required': True, 'stop_before': 'H-Skip'}
    save(dest/'summary.json', result)
    return result


def provenance(exe: Path, files: list[Path]) -> dict:
    paths = sorted(list((ROOT/'npu').glob('*')) + [ROOT/'rsh/planner.py', ROOT/'rsh/prepare.py',
                   ROOT/'scripts/hv_cases.py', ROOT/'scripts/hc_cases.py'])
    return {'version': 'H-C', 'source_hashes': {str(p.relative_to(ROOT)): digest(p) for p in paths if p.is_file()},
            'controller_sha256': digest(Path(__file__)), 'executable_sha256': digest(exe),
            'hv_manifest_sha256': digest(ROOT/'results/hv/manifest.json'),
            'prospective_threshold_rule_sha256': digest(ROOT/'results/hc/prospective_threshold_rule.json'),
            'hv_mixed_validation_sha256': digest(ROOT/'results/hv/mixed_validation.json'),
            'inputs': {p.name: digest(p) for p in files},
            'orders': {p.stem: digest(ROOT/'results/v2/orders'/p.stem/'order.bin') for p in files},
            'hv_routes': {p.stem: digest(ROOT/'results/hv/plans'/p.stem/'routing.json') for p in files},
            'protocol': {'new_main_version': 'H-C', 'controls': ['V0', 'V2', 'H-V'],
                'primary_ratio': 'H-V/H-C', 'secondary_ratios': ['V2/H-C', 'V0/H-C'],
                'w': 16, 'tau_nnz': 4, 'tau_inc': 2,
                'tail': 'frozen T padded to W and appended to Cube; S stays AIV; G unchanged',
                'row_ownership': 'whole row', 'order': 'reuse measured V2 order.bin',
                'routing': 'exact frozen default H-V G/S/T/Z; never repartition',
                'aic_budget': 24, 'aiv_budget': 48, 'warmups': 10, 'samples': 30,
                'processes': 3, 'seed': SEED, 'b_seed': 'reuse H-V/V0 measured B, original seed 20261017+N',
                'timer': 'full synchronized resident call including clearing/B gather/output restore; excludes CPU/H2D',
                'null': 'H-C/H-C: ca-HepTh/N64, web-NotreDame/N64, thermal1/N256; 3 processes',
                'dispatch': 'unchanged native MIX_AIC_1_2 executable; reuse H-V validated profile',
                'threshold': 'frozen prospective_threshold_rule.json: default first; dev3 N64 all three process aggregate HV/HC must exceed max(1, nine HC null process medians and reciprocals) for strategy switch; explicit resolved decision required; no automatic grid',
                'development_matrices': DEVELOPMENT, 'stop_before': 'H-Skip'}}


def freeze_cases(dest: Path, files: list[Path], cases: list[dict]) -> dict:
    roots = [ROOT/'cases_hc'/p.stem/f'N{n}'/v for p in files for n in WIDTHS for v in VARIANTS]
    roots += [ROOT/c['root']/'H-C' for c in cases]
    frozen = {'version': 'H-C', 'configuration_count': len(files)*len(WIDTHS), 'smoke_cases': len(cases),
              'manifest_sha256': digest(dest/'manifest.json'), 'files': {}, 'binary_files': {}}
    for directory in roots:
        meta = read(directory/'metadata.json')
        assert meta['coverage'] == 'full' and meta['tail_skip_rows'] == []
        for name in ['metadata.json', 'config.txt']:
            p = directory/name
            frozen['files'][str(p.relative_to(ROOT))] = digest(p)
        key = str(directory.relative_to(ROOT))
        frozen['binary_files'][key] = meta['files_sha256']
        for name, sha in meta['files_sha256'].items():
            assert digest(directory/f'{name}.bin') == sha, (directory, name)
    return frozen


def verify_frozen_cases(dest: Path) -> None:
    frozen = read(dest/'case_manifest.json')
    assert digest(dest/'manifest.json') == frozen['manifest_sha256']
    for name, sha in frozen['files'].items():
        assert digest(ROOT/name) == sha, name
    for name, hashes in frozen['binary_files'].items():
        for array, sha in hashes.items():
            assert digest(ROOT/name/f'{array}.bin') == sha, (name, array)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--phase', choices=['prepare', 'measure', 'finish'], required=True)
    args = ap.parse_args()
    dest = ROOT/'results/hc'
    dest.mkdir(exist_ok=True)
    exe = ROOT/'build_v4/rsh_runner'
    files = sorted((ROOT/'inputs').glob('*.npz'))
    assert len(files) == 8
    hv_manifest = read(ROOT/'results/hv/manifest.json')
    hv_state = read(ROOT/'results/hv/progress.json')
    validation = read(ROOT/'results/hv/mixed_validation.json')
    assert hv_state['state'] == 'complete' and validation['passed']
    assert digest(exe) == hv_manifest['executable_sha256'] == validation['executable_sha256']
    manifest = provenance(exe, files)
    mf = dest/'manifest.json'
    if mf.exists():
        assert read(mf) == manifest, 'Provenance changed; preserve old evidence and resolve before continuing'
    else:
        save(mf, manifest)
    sf = dest/'progress.json'
    state = read(sf) if sf.exists() else {'version': 'H-C', 'state': 'running', 'stage': 'initial',
                                         'completed': [], 'prepared': []}
    if state['state'] == 'complete':
        print('HC_ALREADY_COMPLETE_STOP_BEFORE_HSKIP', flush=True)
        return

    def stage(name: str) -> None:
        state.update(state='running', stage=name)
        save(sf, state)
        print(name, flush=True)

    def run(cmd: list[str], out: Path, variants: list[str], warmups: int, repeats: int,
            timeout: int = 300) -> dict:
        if out.exists():
            result = read(out)
            validate_record(result, variants, warmups, repeats)
            print('HC_REUSE_VALID_RECORD', str(out.relative_to(ROOT)), flush=True)
            return result
        out.parent.mkdir(parents=True, exist_ok=True)
        pending = out.with_name(out.stem+f'.pending-{time.time_ns()}.json')
        cmd = [str(pending) if arg == str(out) else arg for arg in cmd]
        completed = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        pending.with_suffix('.log').write_text(completed.stdout+completed.stderr)
        if completed.returncode:
            raise RuntimeError(str(pending)+' '+(completed.stdout+completed.stderr)[-4000:])
        result = read(pending)
        validate_record(result, variants, warmups, repeats)
        assert not out.exists(), 'Concurrent controller output detected; refusing overwrite'
        pending.replace(out)
        pending.with_suffix('.log').replace(out.with_suffix('.log'))
        return result

    try:
        if args.phase == 'prepare':
            stage('HC_LAYOUT_SMOKE')
            cases = smoke_cases(dest)
            assert cases == read(dest/'smoke_preparation.json')['cases'] and cases
            for case in cases:
                for cores in [1, 24]:
                    out = dest/'smoke'/f'{case["name"]}_C{cores}.json'
                    run([str(exe), str(ROOT/case['root']), str(cores), '1', '2', str(SEED), str(out), 'H-C'],
                        out, ['H-C'], 1, 2, 90)
            stage(f'HC_SMOKE_PASS_{len(cases)*2}_OF_{len(cases)*2}')
            for source in files:
                stage('HC_PREPARING_'+source.stem)
                prepare_real(source, dest)
                for n in WIDTHS:
                    key = f'{source.stem}/N{n}'
                    if key not in state['prepared']:
                        state['prepared'].append(key)
                save(sf, state)
            frozen = freeze_cases(dest, files, cases)
            if (dest/'case_manifest.json').exists():
                assert read(dest/'case_manifest.json') == frozen, 'Prepared evidence changed'
            else:
                save(dest/'case_manifest.json', frozen)
            state.update(state='prepared', stage='HC_PREPARED_READY_FOR_MEASURE',
                         smoke_cases=len(cases), smoke_checks=len(cases)*2)
            save(sf, state)
            print(state['stage'], flush=True)
        elif args.phase == 'measure':
            assert len(set(state['prepared'])) == len(state['prepared']) == 24
            smoke = read(dest/'smoke_preparation.json')['cases']
            expected_smoke = {f'{case["name"]}_C{cores}.json' for case in smoke for cores in [1, 24]}
            assert {p.name for p in (dest/'smoke').glob('*.json') if '.pending-' not in p.name} == expected_smoke
            for name in expected_smoke:
                validate_record(read(dest/'smoke'/name), ['H-C'], 1, 2)
            verify_frozen_cases(dest)
            stage('HC_NULL_CONTROLS')
            for name, n in NULLS:
                for rep in range(3):
                    key = f'null/{name}/N{n}/run{rep}'
                    out = dest/'null_control'/f'{name}_N{n}_run{rep}.json'
                    run([str(exe), str(ROOT/'cases_hc'/name/f'N{n}'), '24', '10', '30', str(SEED+rep),
                         str(out), 'H-C', 'H-C'], out, ['H-C', 'H-C'], 10, 30)
                    if key not in state['completed']:
                        state['completed'].append(key)
                    state['last_completed'] = key
                    save(sf, state)
            stage('HC_FOURWAY_MEASUREMENTS')
            jobs = [(rep, source.stem, n) for rep in range(3) for source in files for n in WIDTHS]
            random.Random(SEED).shuffle(jobs)
            for rep, name, n in jobs:
                key = f'paired/{name}/N{n}/run{rep}'
                out = dest/'measurements'/name/f'N{n}'/f'run{rep}.json'
                run([str(exe), str(ROOT/'cases_hc'/name/f'N{n}'), '24', '10', '30', str(SEED+rep),
                     str(out), *VARIANTS], out, VARIANTS, 10, 30)
                if key not in state['completed']:
                    state['completed'].append(key)
                state['last_completed'] = key
                save(sf, state)
                print('HC_FOURWAY_DONE', sum(k.startswith('paired/') for k in state['completed']), '/72', key, flush=True)
            summary = summarize(dest, files)
            if not (dest/'threshold_decision.json').exists():
                save(dest/'threshold_decision.json', {'version': 'H-C', 'resolved': False,
                     'default_tau_nnz': 4, 'default_tau_inc': 2,
                     'development_hv_over_hc_per_process': summary['development_hv_over_hc_per_process'],
                     'development_all_three_faster': summary['development_all_three_faster'],
                     'status': 'pending_explicit_decision_no_automatic_grid', 'stop_before': 'H-Skip'})
            state.update(state='default_complete', stage='HC_AWAITING_THRESHOLD_DECISION')
            save(sf, state)
            print(state['stage'], flush=True)
        else:
            expected = {f'paired/{p.stem}/N{n}/run{rep}' for p in files for n in WIDTHS for rep in range(3)}
            expected |= {f'null/{name}/N{n}/run{rep}' for name, n in NULLS for rep in range(3)}
            assert len(state['completed']) == len(set(state['completed'])) == len(expected) == 81
            assert set(state['completed']) == expected
            decision = read(dest/'threshold_decision.json')
            assert decision['resolved'], 'Threshold follow-up decision still pending'
            summarize(dest, files)
            state.update(state='complete', stage='HC_COMPLETE_STOP_BEFORE_HSKIP', next_version='H-Skip',
                         stop_required=True)
            save(sf, state)
            print(state['stage'], flush=True)
    except BaseException:
        state.update(state='failed', error=traceback.format_exc())
        save(sf, state)
        raise


if __name__ == '__main__':
    main()
