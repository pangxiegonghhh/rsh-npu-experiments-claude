"""Verify reporting provenance from saved rows and source bytes; no method runs."""
import ast
import copy
import hashlib
import json
import time
from pathlib import Path

import numpy as np
from guard_provenance import (DIRECT_WRAPPERS, MEMO_WRAPPERS, PRODUCER_VERSIONS,
                              PAIR_ERROR, classify_failure, is_failure_candidate)

BASE = Path(__file__).resolve().parents[1]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def layout_ast(p):
    tree = ast.parse(p.read_text())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Layout')
    fn = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == 'layout')
    return ast.dump(fn, include_attributes=False)


def main():
    index = {}
    wanted = DIRECT_WRAPPERS | MEMO_WRAPPERS | set().union(*PRODUCER_VERSIONS.values())
    for root in [BASE/'scripts', BASE/'logs/source-snapshots']:
        for p in root.rglob('*'):
            if p.is_file() and (p.suffix == '.py' or p.name in wanted):
                h = sha(p)
                if h in wanted:
                    index.setdefault(h, p)
    assert wanted <= set(index), 'source bytes missing'
    direct_ref = layout_ast(index['3c24bf16a508de49d85eff37b0d68ad06aaf10133c2e5a41d0ad9852fced7e4d'])
    memo_ref = layout_ast(index['7363e80fb095c6297d1e35113e9bf11e6a6ac05e354f5810ef65748b5f23b1e8'])
    bindings = []
    for h in sorted(DIRECT_WRAPPERS | MEMO_WRAPPERS):
        actual = layout_ast(index[h])
        assert actual == (direct_ref if h in DIRECT_WRAPPERS else memo_ref)
        bindings.append(dict(sha256=h, path=str(index[h]),
                             mode='direct_native' if h in DIRECT_WRAPPERS else 'failure_memo',
                             layout_ast_sha256=hashlib.sha256(actual.encode()).hexdigest()))
    producers = []
    for entry, versions in PRODUCER_VERSIONS.items():
        for h in sorted(versions):
            tree = ast.parse(index[h].read_text())
            matrix_calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
                            and isinstance(n.func, ast.Name) and n.func.id == 'Matrix']
            diag_loops = [n for n in ast.walk(tree) if isinstance(n, ast.For)
                          and isinstance(n.target, ast.Name) and n.target.id in ['diag', 'diagmode']
                          and isinstance(n.iter, ast.List)
                          and [x.value for x in n.iter.elts if isinstance(x, ast.Constant)] == [0, 1]]
            assert len(matrix_calls) == 1 and len(diag_loops) == 1, entry
            producers.append(dict(entry=entry, sha256=h, path=str(index[h]),
                                  reviewed_protocol='one Matrix/order/W per process; A0 before A1; A0 residual masks; metrics-only LS validation'))
    degrees = np.load(BASE/'work/matrices/reddit/degrees.npy', mmap_mode='r')
    sizes = {t: int(np.count_nonzero(degrees <= t)) for t in [53, 153]}
    real = []
    fixtures = [
        ('post-e', 'stage3-reddit__C3-W4__W16__seed0__tau153', 'stage3-post-', True),
        ('stage3-evaluations', 'stage3-reddit__C2-LSH__W16__seed0', 'stage3-eval-', True),
        ('stage3-evaluations', 'stage3-reddit__B0__W16__seed0', 'stage3-eval-', False),
    ]
    for folder, key, prefix, memo in fixtures:
        rows_path = BASE/'work'/folder/key/'rows.json'
        command_path = BASE/'logs'/(prefix+key+'.command.json')
        before = sha(rows_path)
        rows = json.loads(rows_path.read_text())
        command = json.loads(command_path.read_text())
        assert (command['source_sha256']['scripts/native.py'] in MEMO_WRAPPERS) == memo
        selected = [i for i, r in enumerate(rows) if is_failure_candidate(r)]
        assert selected and {rows[i]['diag'] for i in selected} == {'A0', 'A1'}
        classified = [classify_failure(rows, i, command, sizes) for i in selected]
        for i, proof in zip(selected, classified):
            expected = 'inherited_failure_cache_count' if memo and rows[i]['diag'] == 'A1' else 'executed_scan_recovered'
            assert proof['guard_scan_execution'] == expected, (key, i, proof)
            if expected == 'inherited_failure_cache_count':
                origin = rows[proof['cache_origin_row_index']]
                assert origin['diag'] == 'A0' and origin['tau'] == rows[i]['tau']
        assert sha(rows_path) == before
        real.append(dict(rows_path=str(rows_path), rows_sha256=before,
                         command_path=str(command_path), command_sha256=sha(command_path),
                         classifications=classified))
    # Explicit reporting fixtures exercise ambiguous and cross-tau cache keys.
    def row(diag='A0', tau=2, W=16):
        return dict(diag=diag, tau=tau, W=W, placement='tail-co', d_rule='own',
                    status='INCOMPLETE', note=PAIR_ERROR)
    cmd = dict(command=['python3', '-B', 'scripts/evaluate_t23.py'], source_sha256={
        'scripts/native.py': '3b7830ca38f2950d938f37de6539bd37fd8893dbfbbc8bca073ce9e019754c98',
        'scripts/evaluate_t23.py': next(iter(PRODUCER_VERSIONS['scripts/evaluate_t23.py']))})
    checks = []
    def check(name, rows, i, command, masks, expected):
        got = classify_failure(rows, i, command, masks)
        assert (None if got is None else got['guard_scan_execution']) == expected, (name, got)
        checks.append(dict(name=name, expected=expected))
    cold = 'executed_scan_recovered'; cached = 'inherited_failure_cache_count'; unknown = 'execution_unproven_structural_only'
    check('cold-first', [row()], 0, cmd, {2: 10}, cold)
    check('A1-cached', [row(), row('A1')], 1, cmd, {2: 10}, cached)
    check('equal-nested-masks-cross-tau', [row(), row(tau=3)], 1, cmd, {2: 10, 3: 10}, cached)
    check('different-mask-cold', [row(), row(tau=3)], 1, cmd, {2: 10, 3: 11}, cold)
    check('different-W-cold', [row(), row(W=32)], 1, cmd, {2: 10}, cold)
    unknown_cmd = copy.deepcopy(cmd); unknown_cmd['source_sha256']['scripts/native.py'] = 'unknown'
    check('unknown-wrapper', [row(), row('A1')], 1, unknown_cmd, {2: 10}, unknown)
    unknown_cmd = copy.deepcopy(cmd); unknown_cmd['source_sha256']['scripts/evaluate_t23.py'] = 'unknown'
    check('unknown-producer', [row()], 0, unknown_cmd, {2: 10}, unknown)
    unknown_cmd['source_sha256']['scripts/native.py'] = next(iter(DIRECT_WRAPPERS))
    check('unknown-producer-direct-wrapper', [row()], 0, unknown_cmd, {2: 10}, unknown)
    check('missing-mask-proof', [row()], 0, cmd, {}, unknown)
    check('missing-A0-prefix', [row('A1')], 0, cmd, {2: 10}, unknown)
    previous = row(); previous.update(status='OK', note='', co_chain_guard_windows_skipped=3)
    check('conflicting-prior-success', [previous, row('A1')], 1, cmd, {2: 10}, unknown)
    other = row(); other['d_rule'] = 'D-greedy'
    check('D-greedy-no-scan-inference', [other], 0, cmd, {2: 10}, None)
    other = row(); other['placement'] = 'tail'
    check('non-co-no-scan-inference', [other], 0, cmd, {2: 10}, None)
    for name in ['guard_recovery.py', 'collect_stage3.py', 'build_stage3.py', 'guard_provenance.py']:
        compile((BASE/'scripts'/name).read_text(), name, 'exec')
    scientific = {
        'scripts/native.py': '3b7830ca38f2950d938f37de6539bd37fd8893dbfbbc8bca073ce9e019754c98',
        'scripts/layouts_flatco.cpp': '5dcea0fff0c13830fe55ceb059e520580acb05b59f3286b653562239fafa7fcf',
        'work/liblayouts-v7.dylib': '772c9c3425fda920badf5f97c8bd1888ca029e4547431383647a3249fe4b07c9',
        'scripts/post_e_job.py': '53f68b4087d536fa90aef408abf6bf534f5177d22b45c377fa2d9eae76254368',
        'scripts/evaluate_t23.py': '33fad739a71e6a20847280c08f0b20af589a84d33f46d394053845bd785cf419',
        'scripts/ls_runtime.py': '4074067ec787cb9be78b87f7d479d4f369cff8b7353daf90fddd755a5508757a',
    }
    for path, expected in scientific.items():
        assert sha(BASE/path) == expected, path
    implementation = {f'scripts/{name}': sha(BASE/'scripts'/name) for name in
                      ['guard_provenance.py', 'guard_recovery.py', 'collect_stage3.py',
                       'build_stage3.py', 'gate_guard_provenance.py']}
    result = dict(passed=True, at_utc=time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime()),
                  scope='metadata-only classification of saved rows, exact source binding and reporting fixtures; no scientific reruns',
                  implementation_sources=implementation, wrapper_source_bindings=bindings,
                  producer_source_bindings=producers, real_saved_row_checks=real,
                  reporting_fixtures=checks, scientific_sources_unchanged=scientific,
                  full_guard_recovery_integration_pending_campaign_end=True)
    output = BASE/'logs/stage3-guard-provenance-gate.json'
    output.write_text(json.dumps(result, indent=2))
    print(json.dumps(dict(passed=True, real_jobs=len(real), reporting_fixtures=len(checks),
                          wrapper_versions=len(bindings), producer_versions=len(producers),
                          scientific_reruns=False)))


if __name__ == '__main__':
    main()
