#!/usr/bin/env python3
"""Gate 1 of the T21 C6 alignment-repair supplement.

Replays c6.align_repair on the four KaHyPar outputs that failed in T21 (the *-failed-model.json
files kept under 第一层实验结果/rq2-validate-20261106/checks/) and compares the result with
expected-repairs.json. Pure Python; does not import KaHyPar.

usage: python3 -I check_failed_models.py <T21 checks dir> [<output json>]
exit code 0 = all four cases match, 1 = mismatch.
"""
import hashlib, importlib.util, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('c6_align', HERE / 'c6.py')
c6 = importlib.util.module_from_spec(spec); spec.loader.exec_module(c6)

checks = Path(sys.argv[1])
expected = json.loads((HERE / 'expected-repairs.json').read_text())
out, ok = [], True
for case, exp in sorted(expected.items()):
    m = json.loads((checks / f'{case}-failed-model.json').read_text())
    trace = json.loads((checks / f'{case}.json').read_text())
    call = trace['calls'][-1]
    P, Q, Wt, L = m['pointers'], m['pins'], m['weights'], m['labels']
    nets = [Q[P[e]:P[e + 1]] for e in range(len(Wt))]
    s1, s2 = m['targets']
    size = len(m['vertices'])
    raw_sha = hashlib.sha256(json.dumps(L).encode()).hexdigest()
    cut0 = c6.weighted_cut(nets, Wt, L)
    lab, moves = c6.align_repair(size, nets, Wt, L, s1, s2)
    cut1 = c6.weighted_cut(nets, Wt, lab)
    got = {
        'part_id': call['part_id'], 'targets': [s1, s2], 'raw_sizes': [L.count(0), L.count(1)],
        'raw_labels_sha256_matches_trace': raw_sha == call['labels_sha256'],
        'weighted_cut_before': cut0, 'weighted_cut_before_matches_trace': cut0 == call['weighted_cut'],
        'moved_local_vertices': [mv['local_vertex'] for mv in moves],
        'moved_global_vertices': [m['vertices'][mv['local_vertex']] for mv in moves],
        'weighted_cut_after': cut1,
        'final_labels_sha256': hashlib.sha256(json.dumps(lab).encode()).hexdigest(),
    }
    match = all(got[k] == exp[k] for k in exp) and got['raw_labels_sha256_matches_trace'] and got['weighted_cut_before_matches_trace']
    ok &= match
    out.append({'case': case, 'match': match, 'got': got})
    print(case, 'MATCH' if match else 'MISMATCH', got['raw_sizes'], '->', got['targets'],
          'moved', got['moved_global_vertices'], 'cut', cut0, '->', cut1)
result = {'passed': ok, 'c6_py_sha256': hashlib.sha256((HERE / 'c6.py').read_bytes()).hexdigest(), 'cases': out}
if len(sys.argv) > 2:
    Path(sys.argv[2]).write_text(json.dumps(result, ensure_ascii=False, indent=1))
print('Gate 1 (failed-model replay):', 'OK' if ok else 'FAILED')
sys.exit(0 if ok else 1)
