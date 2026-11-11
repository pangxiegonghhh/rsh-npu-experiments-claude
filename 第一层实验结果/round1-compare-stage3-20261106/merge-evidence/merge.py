"""Read-only evidence verification and isolated, host-aware result merge.

Never executes supplied programs or scientific jobs. Original archives, local
results and WSL evidence stay unchanged. Only derived metadata paths are mapped.
"""
import ast
import csv
import hashlib
import json
import os
from pathlib import Path
import sys
from collections import Counter

import numpy as np

BASE = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent
REMOTE = BASE/'remote-evidence/hostB-windows16gb-wsl2/t23-hostb-results'
ORDERS = REMOTE.parent/'t23-hostb-orders'
VIEW = OUT/'view'
HOST = 'hostB-windows16gb-wsl2'
WSL = '/root/t23-hostb-x86v2-20261109/t23-remote-runtime'

def sha(p):
    with Path(p).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

def read(p):
    return json.loads(Path(p).read_text())

def dump(p, data):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n')

def checksums(root):
    result = []
    for line in (root/'SHA256SUMS').read_text().splitlines():
        digest, name = line.split(maxsplit=1)
        p = root/name.lstrip('*')
        assert p.resolve().is_relative_to(root.resolve())
        assert p.is_file() and sha(p) == digest, p
        result.append(dict(path=p.relative_to(root).as_posix(), sha256=digest))
    return result

def verify():
    evidence = {'checksums': {r.name: checksums(r) for r in [REMOTE, ORDERS]}}
    assignment = read(BASE/'handoff/T23-split-20261109/assignment.json')
    assert sha(REMOTE/'assignment.json') == sha(BASE/'handoff/T23-split-20261109/assignment.json')
    expected = {c['case_id'] for c in assignment['remote_cases']}
    actual = {p.parent.name for p in (REMOTE/'work/stage3-cases').glob('*/record.json')}
    assert actual == expected and len(actual) == 20
    frozen = []
    for p in (REMOTE/'repo').rglob('*'):
        if p.is_file():
            relative = p.relative_to(REMOTE/'repo')
            assert sha(p) == sha(BASE/'repo'/relative), relative
            frozen.append(relative.as_posix())
    assert len(frozen) == 263
    evidence['frozen_repository_files_verified'] = len(frozen)
    inputs = read(REMOTE/'INPUT-MANIFEST.json')['files']
    input_log = (REMOTE/'logs/transfer-inputs-check.log').read_text()
    for x in inputs:
        assert sha(BASE/x['path']) == x['sha256'], x
        assert x['path']+': OK' in input_log, x
    evidence['inputs'] = inputs
    evidence['input_scope'] = 'Local matching input bytes independently hashed; raw WSL readback SHA check log retained. Large CSR inputs were not duplicated in the returned result archive.'
    prep = read(REMOTE/'logs/remote-port-preparation.json')
    ready = read(REMOTE/'logs/remote-readiness.json')
    assert ready['passed'] and ready['fresh_remote_gates'] and ready['host_id'] == HOST
    assert sha(REMOTE/'logs/remote-port-preparation.json') == ready['preparation_receipt_sha256']
    for g in ready['gate_receipts']:
        assert sha(REMOTE/g['path']) == g['sha256'], g
        d = read(REMOTE/g['path'])
        assert d.get('passed') is True or d.get('status') == 'OK' or d.get('returncode') == 0 or d.get('exitcode') == 0, g
    commands = []
    for p in sorted((REMOTE/'logs').glob('remote-fresh-gate-*.command.json')):
        d = read(p)
        assert d['returncode'] == 0 and d['cwd'] == WSL
        script = next(x for x in d['command'] if x.endswith('.py'))
        assert sha(REMOTE/script) == d['source_sha256']
        commands.append(p.name)
    assert len(commands) == 11
    evidence['fresh_gates'] = commands
    evidence['rss_only_source_adaptations'] = []
    new_rss = "ru_maxrss/(2**20 if __import__('sys').platform=='darwin' else 2**10)"
    for x in prep['metadata_only_python_changes']:
        p = REMOTE/x['path']
        old = REMOTE/'reference_evidence/source-before-linux'/x['before_sha256']/p.name
        assert sha(old) == x['before_sha256'] and sha(p) == x['after_sha256']
        restored = p.read_text().replace(new_rss, 'ru_maxrss/2**20')
        assert ast.dump(ast.parse(restored)) == ast.dump(ast.parse(old.read_text())), p
        evidence['rss_only_source_adaptations'].append(x)
    for x in prep['builds']:
        assert x['returncode'] == 0
        assert sha(REMOTE/x['command'][-1]) == x['binary_sha256']
        source = next(s for s in x['command'] if s.endswith(('.cpp', '.c')))
        assert sha(REMOTE/source) == x['source_sha256']
        assert (REMOTE/x['command'][-1]).read_bytes()[:4] == b'\x7fELF'
    evidence['native_builds'] = prep['builds']
    backends = []
    for p in (REMOTE/'logs/layout-context-backends').glob('*.json'):
        d = read(p)
        lib = REMOTE/Path(d['library_path']).relative_to(WSL)
        assert sha(lib) == d['library_sha256'], p
        backends.append({'path': str(p.relative_to(REMOTE)), 'sha256': sha(p), 'pid': d['pid']})
    evidence['actual_loaded_backend_records'] = backends
    # Entrypoints and all statically declared local imports, using recorded SHA.
    index = {}
    for folder in ['scripts', 'reference_evidence']:
        for p in (REMOTE/folder).rglob('*.py'):
            index[sha(p)] = p
    versions = {}; command_count = 0
    for p in (REMOTE/'logs').glob('stage3-*.command.json'):
        d = read(p); hashes = d.get('source_sha256', {}); entry = None
        for x in d.get('command', []):
            if not x.endswith('.py'): continue
            x = x[len(WSL)+1:] if x.startswith(WSL+'/') else x
            if x in hashes: entry = x; break
        if entry is None: continue
        stack = [entry]; seen = set(); command_count += 1
        while stack:
            relative = stack.pop()
            if relative in seen or relative not in hashes: continue
            seen.add(relative); digest = hashes[relative]
            assert digest in index, (p.name, relative, digest)
            versions[(relative,digest)] = str(index[digest].relative_to(REMOTE))
            for n in ast.walk(ast.parse(index[digest].read_text())):
                modules = [a.name.split('.')[0] for a in n.names] if isinstance(n,ast.Import) else [n.module.split('.')[0]] if isinstance(n,ast.ImportFrom) and n.module else []
                for module in modules:
                    relative_import = 'scripts/'+module+'.py'
                    if relative_import in hashes: stack.append(relative_import)
    evidence['source_provenance'] = dict(commands=command_count, versions=[dict(path=k[0],sha256=k[1],source=v) for k,v in versions.items()])
    order_records = read(ORDERS/'orders-transfer-manifest.json')
    assert order_records == read(REMOTE/'orders-transfer-manifest.json')
    assert len(order_records) == 19
    for x in order_records:
        p = ORDERS/x['path']
        assert sha(p) == x['sha256'] and p.stat().st_size == x['size']
        pi = np.asarray(read(p), dtype=np.int64)
        assert len(pi) == 2449029 and np.array_equal(np.sort(pi), np.arange(2449029)), p
    evidence['orders'] = order_records
    ledger = {str(Path(WSL)/x['path']): x for x in order_records}
    for k in expected:
        d = read(REMOTE/'work/stage3-cases'/k/'record.json')
        assert d['execution_host_id'] == HOST and d['status'] in ['OK','INCOMPLETE','SKIPPED']
        if d['status'] == 'OK': assert ledger[d['path']]['sha256'] == d['sha256']
    rows = list(csv.DictReader((REMOTE/'work/stage3-collected/results.csv').open()))
    assert len(rows) == 488 and Counter(r['status'] for r in rows) == {'OK':200,'INCOMPLETE':288}
    independent = read(REMOTE/'work/stage3-independent/ogbn-products/status.json')
    assert independent['status'] == 'OK' and independent['independent_orders'] == 3
    assert len(independent['checks']) == 18
    for c in independent['checks']:
        assert c['identical']
        matches = [r for r in rows if r['member']==c['member'] and r['diag']=='A'+str(c['diag']) and r['source']=='own' and r['tau']==str(c['tau'] if c['tau'] is not None else 'none') and r['placement']==('tail' if c['tau'] is not None else 'none') and r['d_rule']=='own']
        assert len(matches) == 1
        assert all(int(matches[0][k]) == v for k,v in c['metrics'].items() if k in matches[0]), c
        assert any(x['sha256'] == c['order_sha256'] for x in order_records)
    evidence['independent_scope'] = dict(orders=3,checks=18,placement_scope=independent['placement_scope'])
    evidence['remote_condition_counts'] = dict(Counter(r['status'] for r in rows))
    evidence['passed'] = True
    dump(OUT/'remote-verification.json', evidence)
    print('REMOTE_VERIFIED', len(actual), len(rows), len(order_records), 'source commands', command_count, flush=True)

def relocate(x):
    if isinstance(x, str):
        if x.startswith(WSL+'/'): return str(VIEW)+x[len(WSL):]
        if x.startswith(str(BASE)+'/') and not x.startswith(str(OUT)+'/'): return str(VIEW)+x[len(str(BASE)):]
        return x
    if isinstance(x, list): return [relocate(v) for v in x]
    if isinstance(x, dict): return {k:relocate(v) for k,v in x.items()}
    return x

def project():
    assert not VIEW.exists(), 'Use a new view rather than overwrite derived artifacts'
    VIEW.mkdir(); (VIEW/'work').mkdir(); (VIEW/'logs').mkdir()
    for n in ['inputs','delivery','repo','deps','local-orders','local-checkpoints']:
        if (BASE/n).exists(): (VIEW/n).symlink_to(BASE/n, target_is_directory=True)
    for n in ['matrices','t21','rabbit-coarse']:
        (VIEW/'work'/n).symlink_to(BASE/'work'/n, target_is_directory=True)
    projections = []
    def put(p, relative):
        q = VIEW/relative
        assert not q.exists(), ('projection collision',relative)
        q.parent.mkdir(parents=True,exist_ok=True)
        if p.suffix == '.json' and not p.name.endswith(('order.json','checkpoint.json')):
            data = read(p); mapped = relocate(data)
            if data != mapped:
                dump(q,mapped);projections.append(dict(source=str(p),source_sha256=sha(p),projection=str(q.relative_to(VIEW)),projection_sha256=sha(q)))
                return
        os.link(p,q)
    folders = ['stage3-cases','stage3-evaluations','stage3-diagnostics','stage3-post-catalog','post-e','stage3-partial-post','stage3-generated','generated','external','stage3-independent']
    remote_ids = {c['case_id'] for c in read(BASE/'handoff/T23-split-20261109/assignment.json')['remote_cases']}
    for n in folders:
        root = BASE/'work'/n
        if not root.exists(): continue
        for p in root.rglob('*'):
            if p.is_file(): put(p,p.relative_to(BASE))
    # Only owned remote scientific output. Small Cora gate files remain raw evidence.
    for n in folders:
        root = REMOTE/'work'/n
        if not root.exists(): continue
        for p in root.rglob('*'):
            if not p.is_file(): continue
            rel = p.relative_to(root)
            if not (any(str(rel).startswith(k) for k in remote_ids) or str(rel).startswith('ogbn-products')): continue
            put(p,Path('work')/n/rel)
    for p in (ORDERS/'work').rglob('*.order.json'): put(p,p.relative_to(ORDERS))
    for p in (BASE/'logs').iterdir():
        if p.is_file() and p.suffix == '.json': put(p,p.relative_to(BASE))
    for p in (REMOTE/'logs').glob('stage3-*.command.json'):
        if any(k in p.name for k in remote_ids): put(p,p.relative_to(REMOTE))
    # Guard paths are scoped by host, never combine PID-named files.
    dump(OUT/'path-projections.json',projections)
    sys.path.insert(0,str(BASE/'scripts'))
    import collect_stage3
    collect_stage3.BASE = VIEW
    coverage = collect_stage3.collect()
    assert coverage['planned_cases']==409 and coverage['attempted']==409 and coverage['all_attempted']
    assert coverage['result_rows']==6276
    from audit_results import audit
    dump(OUT/'merged-arithmetic-audit.json',audit(VIEW/'work/stage3-collected/results.csv'))
    dump(OUT/'coverage.json',coverage)
    print('PROJECTED_AND_COLLECTED',coverage,flush=True)

if __name__ == '__main__':
    if sys.argv[-1] == 'verify': verify()
    elif sys.argv[-1] == 'project': project()
    else: raise SystemExit('verify | project')
