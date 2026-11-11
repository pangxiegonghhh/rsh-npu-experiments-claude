"""Read-only, independently enumerated T23 dispatch grid audit; never runs methods."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
FIRST = ['cora', 'ogbn-arxiv', 'wiki-RfA', 'dawson5', 'olafu', 'pattern1', 'human_gene1']
P0 = ['C9-Gorder', 'C9-S', 'C10-BP', 'C2-LSH', 'C3-W1', 'C3-W4', 'C4-U', 'C4-T', 'C7-I', 'C1-J', 'C1-H', 'C5', 'C5-U', 'C8-METIS']
P1 = ['C3-A', 'C3-W4-noP', 'C3-W4-R', 'C3-A-R', 'C4-U-R', 'C4-T-R', 'C7-I-R', 'C5-CN', 'C5-U-CN']
P2 = ['C6-HP', 'C6-RB (T21 口径)', 'C6-M mnc=1 (T21 口径)', 'C6-M mnc=4 (T21 口径)', 'C6-M mnc=16 (T21 口径)']
REFERENCES = ['B0', 'B1', 'B-RCM-ref', 'rabbit-pilot', 'neutron-pilot']


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage3-results', type=Path, default=BASE/'work/stage3-collected/results.csv')
    parser.add_argument('--output', type=Path, default=BASE/'logs/dispatch-grid-independent-audit.json')
    args = parser.parse_args()
    meta_path = BASE/'logs/matrices-and-taus.json'
    meta = {r['matrix']: r for r in json.loads(meta_path.read_text())}
    assert set(meta) == set(FIRST + ['reddit', 'ogbn-products'])
    # mycielskian15 has no input and no measured tau: retain four full-row
    # SKIPPED cells per candidate, never invent a quantile or a residual set.
    first_cases = {(m, c, 16, 0) for m in FIRST for c in REFERENCES + P0}
    first_cases |= {(m, c, 16, seed) for m in FIRST[:2]
                    for c in ['C1-J', 'C1-H', 'C2-LSH', 'C5', 'C5-U', 'C10-BP']
                    for seed in [1, 2]}
    stage3_cases = {(m, c, 16, 0) for m in FIRST for c in P1 + P2}
    stage3_cases |= {(m, c, 16, seed) for m in FIRST[:2]
                     for c in ['C5-CN', 'C5-U-CN'] for seed in [1, 2]}
    sensitivity = {(m, c, w, 0) for m in FIRST[:4] for w in [32, 64, 128]
                   for c in ['B0', 'B1', 'B-RCM-ref'] + P0}
    stage3_cases |= sensitivity
    second = ['reddit', 'ogbn-products', 'mycielskian15']
    stage3_cases |= {(m, c, 16, 0) for m in second for c in REFERENCES + P0 + P1 + P2}
    planned_path = BASE/'logs/stage3-planned-cases.json'
    planned = json.loads(planned_path.read_text())
    actual_cases = [(r['matrix'], r['method'], int(r['W']), int(r['seed'])) for r in planned]
    assert len(actual_cases) == len(set(actual_cases)) == 409
    assert set(actual_cases) == stage3_cases
    assert {(r['matrix'], r['method'], int(r['W']), int(r['seed']))
            for r in planned if r.get('main_tau_only')} == sensitivity

    def own_grid(cases):
        grid = set()
        for m, c, w, seed in cases:
            taus = [str(t['tau']) for t in meta[m]['taus']] if m in meta else []
            if (m, c, w, seed) in sensitivity:
                taus = taus[-1:]
            for diag in ['A0', 'A1']:
                for dr in ['own', 'D-greedy']:
                    grid.add((m, c, w, seed, diag, 'none', 'none', dr, 'own'))
                    for tau in taus:
                        for placement in ['tail-co', 'tail']:
                            grid.add((m, c, w, seed, diag, tau, placement, dr, 'own'))
        return grid

    def post_grid(matrices):
        return {(m, c, 16, 0, diag, str(t['tau']), 'tail-co', dr, 'post-E')
                for m in matrices if m in meta for c in ['B0', 'B1'] + P0
                for t in meta[m]['taus'] for diag in ['A0', 'A1']
                for dr in ['own', 'D-greedy']}

    def verify(path, expected):
        rows = list(csv.DictReader(path.open()))
        keys = [(r['matrix'], r['member'], int(r['W']), int(r.get('seed') or 0),
                 r['diag'], str(r['tau']), r['placement'], r['d_rule'], r['source'])
                for r in rows]
        assert len(keys) == len(set(keys)), 'duplicate condition'
        missing = expected - set(keys)
        extra = set(keys) - expected
        assert not missing and not extra, {'missing': sorted(missing), 'extra': sorted(extra)}
        return dict(path=str(path), sha256=digest(path), conditions=len(keys),
                    grid_exact=True, status_counts={s: sum(r['status'] == s for r in rows)
                                                   for s in ['OK', 'INCOMPLETE', 'SKIPPED']})

    first_path = BASE/'delivery/第一层实验结果/round1-compare-20261106/results.csv'
    first = verify(first_path, own_grid(first_cases) | post_grid(FIRST))
    stage3 = verify(args.stage3_results, own_grid(stage3_cases) | post_grid(second))
    assert first['conditions'] == 4036 and stage3['conditions'] == 6276
    assert first['status_counts'] == {'OK': 4036, 'INCOMPLETE': 0, 'SKIPPED': 0}
    docs = ['第一层工作区/T23派发/说明.md', '第一层工作区/首轮候选比较实验方案.md']
    proof = dict(passed=True,
                 scope='dispatch coverage only; pending/INCOMPLETE/SKIPPED placeholders remain visible; does not prove scientific completion',
                 independent_enumeration=True,
                 dispatch_sources=[dict(path=str(BASE/'repo'/p), sha256=digest(BASE/'repo'/p)) for p in docs],
                 measured_tau_source=dict(path=str(meta_path), sha256=digest(meta_path)),
                 planned_catalog_sha256=digest(planned_path),
                 first_own_cases=len(first_cases), stage3_cases=len(stage3_cases),
                 stage3_W_sensitivity_cases=len(sensitivity), first=first, stage3=stage3,
                 missing_matrix_policy='mycielskian15: 33 candidates x 4 full-row SKIPPED cells; no fabricated tau/post-E conditions')
    args.output.write_text(json.dumps(proof, ensure_ascii=False, indent=2))
    print(json.dumps(dict(passed=True, first_conditions=first['conditions'],
                          stage3_conditions=stage3['conditions'], stage3_cases=len(stage3_cases),
                          stage3_W_sensitivity_cases=len(sensitivity), scientific_completion_claimed=False)))


if __name__ == '__main__':
    main()
