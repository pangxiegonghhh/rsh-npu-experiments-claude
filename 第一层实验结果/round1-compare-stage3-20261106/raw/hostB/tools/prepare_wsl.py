"""Verify transfer files, relocate input pointers and build Linux libraries.

This is preparation, never a scientific PASS or readiness gate.
"""
import hashlib, json, os, platform, re, shutil, subprocess, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''): h.update(chunk)
    return h.hexdigest()

def main():
    assert platform.system() == 'Linux', 'Run inside WSL2 Ubuntu, not Windows Python/macOS.'
    os.chdir(ROOT)
    (ROOT/'logs').mkdir(exist_ok=True)
    receipt = ROOT/'logs/remote-port-preparation.json'
    assert not receipt.exists(), 'Preserve the previous run; use a fresh extraction for a new preparation.'
    for name in ['SHA256SUMS.source', 'SHA256SUMS.inputs']:
        for line in (ROOT/name).read_text().splitlines():
            digest, rel = line.split('  ', 1)
            assert sha(ROOT/rel) == digest, rel
    assignment = json.loads((ROOT/'assignment.json').read_text())
    changes = []
    needle = '.ru_maxrss/2**20'
    replacement = ".ru_maxrss/(2**20 if __import__('sys').platform=='darwin' else 2**10)"
    for p in sorted((ROOT/'scripts').glob('*.py')):
        before = p.read_bytes(); text = before.decode()
        if needle not in text: continue
        h = hashlib.sha256(before).hexdigest()
        saved = ROOT/'reference_evidence/source-before-linux'/h/p.name
        saved.parent.mkdir(parents=True, exist_ok=True); saved.write_bytes(before)
        after = text.replace(needle, replacement)
        assert after.replace(replacement, needle) == text
        p.write_text(after)
        changes.append(dict(path=str(p.relative_to(ROOT)), before_sha256=h, after_sha256=sha(p), change='Linux KiB to MiB reporting only; default 8GiB native guard unchanged'))
    index_path = ROOT/'logs/reused-orders.json'
    index = json.loads(index_path.read_text())
    relocation = json.loads((ROOT/'reference_inputs/reuse-relocation.json').read_text())
    for item in index:
        old = item.get('runtime_path', item.get('path'))
        if old in relocation:
            new = ROOT/relocation[old]
            assert sha(new) == item['sha256']
            item.update(runtime_path=str(new), relocated_from_runtime_path=old)
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2)+'\n')
    for p in (ROOT/'work/rabbit-coarse').glob('*.record.json'):
        original = p.read_bytes(); r = json.loads(original)
        target = ROOT/'work/rabbit-coarse'/Path(r['runtime_path']).name
        assert sha(target) == r['mapping_sha256']
        saved = ROOT/'reference_evidence/coarse-records-original'/p.name
        saved.parent.mkdir(parents=True, exist_ok=True); saved.write_bytes(original)
        r['relocation'] = dict(source_record_sha256=hashlib.sha256(original).hexdigest(), source_runtime_path=r['runtime_path'], new_runtime_path=str(target), note='Genuine cached mapping; original coarse time, memory and author fields unchanged; no author execution on this host.')
        r['runtime_path'] = str(target)
        p.write_text(json.dumps(r, ensure_ascii=False, indent=2)+'\n')
    (ROOT/'work/t21').mkdir(parents=True, exist_ok=True)
    builds = [
        ('scripts/layouts_flatco.cpp', 'work/liblayouts-v7.dylib'),
        ('scripts/layouts_cached.cpp', 'work/liblayouts-v4.dylib'),
        ('scripts/candidates.cpp', 'work/libcandidates-v2.dylib'),
        ('scripts/rect.cpp', 'work/librect.dylib'),
        ('scripts/large_rcm.cpp', 'work/liblarge-rcm.dylib'),
        ('scripts/rabbit_local.cpp', 'work/librabbit-local.dylib'),
        ('scripts/independent_sorted.cpp', 'work/libindependent-sorted.dylib'),
        ('native_sources/accelerate-v8.cpp', 'work/t21/librq2-v8.dylib'),
        ('scripts/t21/slashburn.cpp', 'work/libslashburn.dylib'),
    ]
    records = []
    for i, (src, dest) in enumerate(builds):
        command = ['g++','-std=c++17','-O3','-ffp-contract=off','-shared','-fPIC',src,'-o',dest]
        result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
        (ROOT/'logs'/f'remote-build-{i}.stdout').write_text(result.stdout)
        (ROOT/'logs'/f'remote-build-{i}.stderr').write_text(result.stderr)
        records.append(dict(command=command, returncode=result.returncode, source_sha256=sha(ROOT/src)))
        assert result.returncode == 0, dest
        records[-1]['binary_sha256'] = sha(ROOT/dest)
    command = ['gcc','-std=c11','-D_POSIX_C_SOURCE=200809L','-O2','-shared','-fPIC','-pthread','scripts/memory_guard.c','-o','work/libmemory-guard.dylib']
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    (ROOT/'logs/remote-build-memory.stdout').write_text(result.stdout)
    (ROOT/'logs/remote-build-memory.stderr').write_text(result.stderr)
    assert result.returncode == 0
    records.append(dict(command=command, returncode=result.returncode, source_sha256=sha(ROOT/'scripts/memory_guard.c'), binary_sha256=sha(ROOT/'work/libmemory-guard.dylib')))
    import numpy, scipy
    data = dict(preparation_completed=True, scientific_readiness=False, host_id=assignment['remote_host_id'], split_id=assignment['split_id'], platform=platform.platform(), machine=platform.machine(), python=sys.version, numpy=numpy.__version__, scipy=scipy.__version__, compiler=subprocess.check_output(['g++','--version'],text=True), memory_info=Path('/proc/meminfo').read_text(), cpu_info=Path('/proc/cpuinfo').read_text(), metadata_only_python_changes=changes, builds=records, completed_at=time.time(), next_action='Run all fresh Cora and memory-unit gates in HANDOFF.md; do not create PASS before they execute.')
    receipt.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n')
    print('LINUX_PREPARATION_COMPLETE; FRESH_GATES_STILL_REQUIRED')

if __name__ == '__main__': main()
