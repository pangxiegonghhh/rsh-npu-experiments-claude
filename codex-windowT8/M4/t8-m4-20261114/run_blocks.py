"""Registered 20-block timing run, preserving failures and retry provenance."""
import csv
import hashlib
import json
import statistics
import subprocess
import time
from pathlib import Path

root = Path(__file__).resolve().parent
rows = json.loads((root / 'm4-manifest.json').read_text())
points = {r['name']: r for r in rows if 'alias_of' not in r}
assert len(points) == 2592
assert (root / 'check-v5.rc').read_text().strip() == '0'
assert 'M4_ALL_PASS 2592 mode=check' in (root / 'check-v5.log').read_text()
pilot = json.loads((root / 'pilot-v5-summary.json').read_text())
assert len(pilot) == 5 and all(r['valid'] for r in pilot), 'Pilot drift gate failed'
samples = {}
for b in range(5):
    for r in csv.DictReader((root / 'results-pilot-v5' / f'b{b:02d}' / 'timing.csv').open()):
        samples.setdefault(r['case'], []).append(r)
noise = []
for name, data in samples.items():
    sigma = statistics.stdev(float(r['us']) for r in data)
    wpc = int(data[0]['windows_per_core'])
    signal = .005 * 32 * wpc
    noise.append(dict(case=name, sigma_us=sigma, signal_5ns_deltaR32_us=signal,
                      signal_to_sigma=signal / sigma if sigma else None,
                      pass_gate=signal >= 10 * sigma))
(root / 'pilot-resolution-gate.json').write_text(json.dumps(noise, indent=2))
assert all(r['pass_gate'] for r in noise), 'Increase batch before formal timing'
registration = dict(blocks=20, random_seed_base=20261114, max_group_drift=.05,
                    group_retries=3, source_hashes={p: hashlib.sha256((root/p).read_bytes()).hexdigest()
                    for p in ['kernel.cpp','host.cpp','m4-manifest.json','cases.list']},
                    pilot_resolution_pass=True, normalization='global makespan / total windows across 24 AICs',
                    start_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()))
(root / 'formal-registration-v5.json').write_text(json.dumps(registration, indent=2))

def run(out, seed, listing=None):
    cmd = [str(root/'build/t8_micro'),'timeblock',str(out),str(seed)]
    if listing: cmd.append(str(listing))
    started=time.monotonic()
    with out.with_suffix('.log').open('w') as log:
        rc=subprocess.run(cmd,cwd=root,stdout=log,stderr=subprocess.STDOUT).returncode
    assert rc==0, f'Correctness/runtime failure in {out}; stop'
    reg=list(csv.DictReader((out/'group-registration.csv').open()))
    assert all(r['input_immutable']=='1' for r in reg)
    return reg,time.monotonic()-started

target=root/'results-blocks-v5'; target.mkdir(exist_ok=True)
for block in range(20):
    journal=target/f'b{block:02d}-accepted.json'
    if journal.exists():
        raise RuntimeError(f'Existing block {journal}: resume must explicitly verify it')
    out=target/f'b{block:02d}-a0'
    reg,wall=run(out,block)
    accepted={}; attempts=[dict(path=str(out.relative_to(root)),seed=block,wall_seconds=wall,registration=reg)]
    for r in reg:
        key=(int(r['dtype']),int(r['N']))
        if r['valid']=='1': accepted[key]=str(out.relative_to(root))
    for attempt in range(1,4):
        pending={(int(r['dtype']),int(r['N'])) for r in reg}-set(accepted)
        if not pending: break
        listing=target/f'b{block:02d}-a{attempt}.list'
        names=[name for name,r in points.items() if (int(r['dtype']=='FP32'),r['n']) in pending]
        listing.write_text(''.join(name+'\n' for name in names))
        retry=target/f'b{block:02d}-a{attempt}'; seed=block+attempt*1000
        retry_reg,retry_wall=run(retry,seed,listing)
        attempts.append(dict(path=str(retry.relative_to(root)),seed=seed,wall_seconds=retry_wall,registration=retry_reg))
        for r in retry_reg:
            if r['valid']=='1': accepted[(int(r['dtype']),int(r['N']))]=str(retry.relative_to(root))
    assert len(accepted)==10, f'Block {block}: drift still exceeds 5% after retries'
    result=dict(block=block,groups=[dict(dtype=k[0],N=k[1],path=v) for k,v in sorted(accepted.items())],attempts=attempts)
    journal.write_text(json.dumps(result,indent=2))
    print('BLOCK_ACCEPTED',block,'wall_seconds',sum(a['wall_seconds'] for a in attempts),flush=True)
print('M4_FORMAL_COMPLETE 20 blocks',flush=True)
