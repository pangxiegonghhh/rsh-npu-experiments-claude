"""Run only H-Skip with same-R controls and resumable frozen evidence."""
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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.hv_cases import digest, save
from scripts.skip_cases import smoke_cases, prepare_real

VARIANTS = ['V0', 'V2', 'H-V', 'H-C', 'V0-R', 'V2-R', 'H-Skip']
PARTIAL = ['V0-R', 'V2-R', 'H-Skip']
KEYS = ['v0', 'v2', 'hv', 'hc', 'v0r', 'v2r', 'skip']
WIDTHS = [16, 64, 256]
SEED = 20261018
NULLS = [('SNAP_ca-HepTh', 64), ('SNAP_web-NotreDame', 64), ('Schmid_thermal1', 256)]


def read(path: Path) -> dict:
    return json.loads(path.read_text())


def expected_rows(root: Path, variants: list[str]) -> list[int]:
    counts = []
    for variant in variants:
        meta = read(root/variant/'metadata.json')
        m = int((root/variant/'config.txt').read_text().split()[0])
        counts.append(m-len(meta['tail_skip_rows']))
    assert len({counts[i] for i, v in enumerate(variants) if v in PARTIAL}) <= 1
    return counts


def validate_record(x: dict, variants: list[str], warmups: int, repeats: int,
                    valid_rows: list[int] | None = None) -> None:
    assert x['correctness'] and x['warmups'] == warmups and x['repeats'] == repeats
    assert [r['variant'] for r in x['records']] == variants
    assert x['cores_aic_budget'] in (1, 24) and x['cores_aic'] in (0, x['cores_aic_budget'])
    assert x['cores_aiv'] == 2*x['cores_aic_budget']
    if warmups == 10:
        assert x['interleaving'] == 'randomized_per_call' and x['b_rotation'] == 2
        assert x['cores_aic_budget'] == 24 and x['cores_aiv'] == 48
        assert x['timer'] == 'resident_synchronized_full_call_us'
    for i, r in enumerate(x['records']):
        assert len(r['samples_us']) == repeats
        assert all(math.isfinite(t) and t > 0 for t in r['samples_us'])
        assert math.isfinite(r['max_abs_error']) and r['max_abs_error'] >= 0
        assert 0 <= r['valid_rows'] <= r['m']
        if valid_rows is not None:
            assert r['valid_rows'] == valid_rows[i]
        if r['variant'] not in PARTIAL:
            assert r['valid_rows'] == r['m']
    partial_counts = {r['valid_rows'] for r in x['records'] if r['variant'] in PARTIAL}
    assert len(partial_counts) <= 1


def summarize(dest: Path, files: list[Path]) -> dict:
    rows = []
    for source in files:
        for n in WIDTHS:
            xs = [read(dest/'measurements'/source.stem/f'N{n}'/f'run{rep}.json') for rep in range(3)]
            first = xs[0]['records'][-1]
            row = {'matrix': source.stem, 'n': n, 'm': first['m'],
                   'valid_rows': first['valid_rows'], 'tail_rows': first['m']-first['valid_rows'],
                   'skip_max_abs_error': max(x['records'][-1]['max_abs_error'] for x in xs)}
            for i, key in enumerate(KEYS):
                meds = [statistics.median(x['records'][i]['samples_us']) for x in xs]
                row[key+'_process_medians_us'] = meds
                row[key+'_median_us'] = statistics.median(meds)
            for i, key in enumerate(KEYS[:-1]):
                ratios = [statistics.median(a/b for a, b in zip(x['records'][i]['samples_us'],
                           x['records'][-1]['samples_us'])) for x in xs]
                row[key+'_over_skip_per_process'] = ratios
                row[key+'_over_skip'] = statistics.median(ratios)
            rows.append(row)
    result = {'version': 'H-Skip', 'correctness': True, 'configurations': len(rows),
              'paired_processes': len(rows)*3, 'null_processes': 9, 'variants': VARIANTS,
              'rows': rows, 'same_r_ratios': ['v0r_over_skip', 'v2r_over_skip'],
              'optimistic_full_ratios': ['v0_over_skip', 'v2_over_skip', 'hv_over_skip', 'hc_over_skip'],
              'threshold_tuning_allowed': False, 'next_version': 'none', 'stop_required': True,
              'limits': 'Partial output R=all original rows minus frozen T. Full/Skip ratios are optimistic diagnostics, not complete SpMM speedups or mathematical upper bounds.'}
    save(dest/'summary.json', result)
    return result


def provenance(exe: Path, files: list[Path]) -> dict:
    paths = sorted(list((ROOT/'npu').glob('*')) + [ROOT/'rsh/planner.py', ROOT/'rsh/prepare.py',
                   ROOT/'scripts/hv_cases.py', ROOT/'scripts/hc_cases.py', ROOT/'scripts/skip_cases.py'])
    return {'version': 'H-Skip', 'source_hashes': {str(p.relative_to(ROOT)): digest(p) for p in paths if p.is_file()},
            'controller_sha256': digest(Path(__file__)), 'executable_sha256': digest(exe),
            'hv_manifest_sha256': digest(ROOT/'results/hv/manifest.json'),
            'hc_manifest_sha256': digest(ROOT/'results/hc/manifest.json'),
            'hv_mixed_validation_sha256': digest(ROOT/'results/hv/mixed_validation.json'),
            'hv_threshold_decision_sha256': digest(ROOT/'results/hv/threshold_decision.json'),
            'hc_threshold_decision_sha256': digest(ROOT/'results/hc/threshold_decision.json'),
            'inputs': {p.name: digest(p) for p in files},
            'orders': {p.stem: digest(ROOT/'results/v2/orders'/p.stem/'order.bin') for p in files},
            'hv_routes': {p.stem: digest(ROOT/'results/hv/plans'/p.stem/'routing.json') for p in files},
            'protocol': {'new_main_version': 'H-Skip', 'variants': VARIANTS,
                'same_r_ratios': ['V0-R/H-Skip', 'V2-R/H-Skip'],
                'optimistic_full_ratios': ['V0/H-Skip', 'V2/H-Skip', 'H-V/H-Skip', 'H-C/H-Skip'],
                'w': 16, 'tau_nnz': 4, 'tau_inc': 2, 'candidate_budget': 256, 'knn': 16,
                'tail': 'skip exact frozen T; valid[T]=0; R=all original rows minus T',
                'row_ownership': 'whole row; no long-row splitting',
                'order': 'reuse measured V2 order.bin; V2-R restricts order to R then fixed W windows',
                'routing': 'exact frozen default H-V G/S/T/Z; H-Skip retains G/S, no repartition',
                'aic_budget': 24, 'aiv_budget': 48, 'warmups': 10, 'samples': 30,
                'processes': 3, 'seed': SEED, 'b_seed': 'reuse measured full A/B/golden; original seed 20261017+N',
                'timer': 'full synchronized resident call including clearing/B gather/output restore; excludes CPU/H2D',
                'null': 'H-Skip/H-Skip: ca-HepTh/N64, web-NotreDame/N64, thermal1/N256; 3 processes',
                'dispatch': 'unchanged native MIX_AIC_1_2 executable; reuse H-V validated profile',
                'threshold': 'fixed 4/2; H-Skip cannot select thresholds or retrospectively alter full-output decisions',
                'next_version': 'none', 'stop_required': True}}


def freeze_cases(dest: Path, files: list[Path], cases: list[dict]) -> dict:
    roots = [ROOT/'cases_skip'/p.stem/f'N{n}'/v for p in files for n in WIDTHS for v in VARIANTS]
    roots += [ROOT/c['root']/v for c in cases for v in PARTIAL]
    frozen = {'version': 'H-Skip', 'configuration_count': len(files)*len(WIDTHS), 'smoke_cases': len(cases),
              'manifest_sha256': digest(dest/'manifest.json'), 'files': {}, 'binary_files': {}}
    for directory in roots:
        meta = read(directory/'metadata.json')
        assert meta['variant'] == directory.name
        if directory.name in PARTIAL:
            assert meta['coverage'] == ('retained_rows_only' if meta['tail_skip_rows'] else 'full')
        else:
            assert meta['coverage'] == 'full' and meta['tail_skip_rows'] == []
        for name in ['metadata.json', 'config.txt']:
            p = directory/name
            frozen['files'][str(p.relative_to(ROOT))] = digest(p)
        frozen['binary_files'][str(directory.relative_to(ROOT))] = meta['files_sha256']
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
    dest = ROOT/'results/skip'
    dest.mkdir(exist_ok=True)
    exe = ROOT/'build_v4/rsh_runner'
    files = sorted((ROOT/'inputs').glob('*.npz'))
    assert len(files) == 8
    hv_manifest = read(ROOT/'results/hv/manifest.json')
    hc_manifest = read(ROOT/'results/hc/manifest.json')
    validation = read(ROOT/'results/hv/mixed_validation.json')
    assert read(ROOT/'results/hv/progress.json')['state'] == 'complete'
    assert read(ROOT/'results/hc/progress.json')['state'] == 'complete' and validation['passed']
    assert digest(exe) == hv_manifest['executable_sha256'] == hc_manifest['executable_sha256'] == validation['executable_sha256']
    manifest = provenance(exe, files)
    mf = dest/'manifest.json'
    if mf.exists():
        assert read(mf) == manifest, 'Provenance changed; preserve old evidence before continuing'
    else:
        save(mf, manifest)
    sf = dest/'progress.json'
    state = read(sf) if sf.exists() else {'version': 'H-Skip', 'state': 'running', 'stage': 'initial',
                                         'completed': [], 'prepared': []}
    if state['state'] == 'complete':
        print('HSKIP_ALREADY_COMPLETE_STOP_ALL_MAIN_VERSIONS', flush=True)
        return

    def stage(name: str) -> None:
        state.update(state='running', stage=name)
        save(sf, state)
        print(name, flush=True)

    def run(cmd: list[str], out: Path, variants: list[str], warmups: int, repeats: int,
            root: Path, timeout: int = 300) -> dict:
        valid_rows = expected_rows(root, variants)
        if out.exists():
            result = read(out)
            validate_record(result, variants, warmups, repeats, valid_rows)
            print('HSKIP_REUSE_VALID_RECORD', str(out.relative_to(ROOT)), flush=True)
            return result
        out.parent.mkdir(parents=True, exist_ok=True)
        pending = out.with_name(out.stem+f'.pending-{time.time_ns()}.json')
        cmd = [str(pending) if arg == str(out) else arg for arg in cmd]
        completed = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        pending.with_suffix('.log').write_text(completed.stdout+completed.stderr)
        if completed.returncode:
            raise RuntimeError(str(pending)+' '+(completed.stdout+completed.stderr)[-4000:])
        result = read(pending)
        validate_record(result, variants, warmups, repeats, valid_rows)
        assert not out.exists(), 'Concurrent controller output detected; refusing overwrite'
        pending.replace(out)
        pending.with_suffix('.log').replace(out.with_suffix('.log'))
        return result

    try:
        if args.phase == 'prepare':
            stage('HSKIP_LAYOUT_SMOKE')
            cases = smoke_cases(dest)
            assert cases == read(dest/'smoke_preparation.json')['cases'] and cases
            for case in cases:
                for cores in [1, 24]:
                    out = dest/'smoke'/f'{case["name"]}_C{cores}.json'
                    root = ROOT/case['root']
                    run([str(exe), str(root), str(cores), '1', '2', str(SEED), str(out), *PARTIAL],
                        out, PARTIAL, 1, 2, root, 90)
            stage(f'HSKIP_SMOKE_PASS_{len(cases)*2}_OF_{len(cases)*2}')
            for source in files:
                stage('HSKIP_PREPARING_'+source.stem)
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
            state.update(state='prepared', stage='HSKIP_PREPARED_READY_FOR_MEASURE',
                         smoke_cases=len(cases), smoke_checks=len(cases)*2,
                         smoke_variant_checks=len(cases)*2*len(PARTIAL))
            save(sf, state)
            print(state['stage'], flush=True)
        elif args.phase == 'measure':
            assert len(set(state['prepared'])) == len(state['prepared']) == 24
            smoke = read(dest/'smoke_preparation.json')['cases']
            expected_smoke = {f'{case["name"]}_C{cores}.json' for case in smoke for cores in [1, 24]}
            assert {p.name for p in (dest/'smoke').glob('*.json') if '.pending-' not in p.name} == expected_smoke
            for case in smoke:
                for cores in [1, 24]:
                    validate_record(read(dest/'smoke'/f'{case["name"]}_C{cores}.json'), PARTIAL, 1, 2,
                                    expected_rows(ROOT/case['root'], PARTIAL))
            verify_frozen_cases(dest)
            stage('HSKIP_NULL_CONTROLS')
            for name, n in NULLS:
                for rep in range(3):
                    key = f'null/{name}/N{n}/run{rep}'
                    out = dest/'null_control'/f'{name}_N{n}_run{rep}.json'
                    root = ROOT/'cases_skip'/name/f'N{n}'
                    run([str(exe), str(root), '24', '10', '30', str(SEED+rep), str(out),
                         'H-Skip', 'H-Skip'], out, ['H-Skip', 'H-Skip'], 10, 30, root)
                    if key not in state['completed']:
                        state['completed'].append(key)
                    state['last_completed'] = key
                    save(sf, state)
            stage('HSKIP_SEVENWAY_MEASUREMENTS')
            jobs = [(rep, source.stem, n) for rep in range(3) for source in files for n in WIDTHS]
            random.Random(SEED).shuffle(jobs)
            for rep, name, n in jobs:
                key = f'paired/{name}/N{n}/run{rep}'
                out = dest/'measurements'/name/f'N{n}'/f'run{rep}.json'
                root = ROOT/'cases_skip'/name/f'N{n}'
                run([str(exe), str(root), '24', '10', '30', str(SEED+rep), str(out), *VARIANTS],
                    out, VARIANTS, 10, 30, root)
                if key not in state['completed']:
                    state['completed'].append(key)
                state['last_completed'] = key
                save(sf, state)
                print('HSKIP_SEVENWAY_DONE', sum(k.startswith('paired/') for k in state['completed']), '/72', key, flush=True)
            summarize(dest, files)
            state.update(state='measurements_complete', stage='HSKIP_MEASUREMENTS_COMPLETE_READY_FINISH')
            save(sf, state)
            print(state['stage'], flush=True)
        else:
            expected = {f'paired/{p.stem}/N{n}/run{rep}' for p in files for n in WIDTHS for rep in range(3)}
            expected |= {f'null/{name}/N{n}/run{rep}' for name, n in NULLS for rep in range(3)}
            assert len(state['completed']) == len(set(state['completed'])) == len(expected) == 81
            assert set(state['completed']) == expected
            verify_frozen_cases(dest)
            for source in files:
                for n in WIDTHS:
                    root = ROOT/'cases_skip'/source.stem/f'N{n}'
                    for rep in range(3):
                        validate_record(read(dest/'measurements'/source.stem/f'N{n}'/f'run{rep}.json'),
                                        VARIANTS, 10, 30, expected_rows(root, VARIANTS))
            summarize(dest, files)
            state.update(state='complete', stage='HSKIP_COMPLETE_STOP_ALL_MAIN_VERSIONS',
                         next_version='none', stop_required=True, completed_main_versions=6)
            save(sf, state)
            print(state['stage'], flush=True)
    except BaseException:
        state.update(state='failed', error=traceback.format_exc())
        save(sf, state)
        raise


if __name__ == '__main__':
    main()
