"""Sequential replay timing after the complete synthetic M4 run."""
import csv
import hashlib
import json
import subprocess
import time
from pathlib import Path

root=Path(__file__).resolve().parent
main=root.parent/'t8-m4'
while not (main/'formal-driver-v5.rc').exists():time.sleep(10)
assert (main/'formal-driver-v5.rc').read_text().strip()=='0','Synthetic formal run failed'
assert len(list((main/'results-blocks-v5').glob('b*-accepted.json')))==20
assert json.loads((root/'interlude-registration.json').read_text())['status']=='PASS','Replay correctness failed'
assert (root/'check-v1.rc').read_text().strip()=='0'
rows=json.loads((root/'replay-manifest.json').read_text())
points={r['name']:r for r in rows}
target=root/'results-blocks-v1';target.mkdir(exist_ok=True)
(root/'formal-registration-v1.json').write_text(json.dumps(dict(blocks=20,max_drift=.05,retries=3,
    source_sha256={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in ['kernel.cpp','host.cpp','host-base.h','replay-manifest.json']},
    batch_useful_bytes=8*1024**3,scope='Cora B0/B1 exact gathered B-row tables with fixed dense A; all 24 AICs replay identical window order on disjoint dense-B replicas',
    normalization='global device makespan / (cycles per core * 24 AICs)',
    cache='32 MiB or >=1 GiB effective unique B-row working set; not single-copy end-to-end SpMM'),indent=2))

def run(out,seed,listing=None):
    cmd=[str(root/'build/t8_micro'),'timeblock',str(out),str(seed)]
    if listing:cmd.append(str(listing))
    start=time.monotonic()
    with out.with_suffix('.log').open('w') as log:
        rc=subprocess.run(cmd,cwd=root,stdout=log,stderr=subprocess.STDOUT).returncode
    assert rc==0,f'Replay runtime/correctness failure: {out}'
    reg=list(csv.DictReader((out/'group-registration.csv').open()))
    assert all(r['input_immutable']=='1' for r in reg)
    return reg,time.monotonic()-start

for block in range(20):
    journal=target/f'b{block:02d}-accepted.json';assert not journal.exists()
    out=target/f'b{block:02d}-a0';reg,wall=run(out,block)
    accepted={};attempts=[dict(path=str(out.relative_to(root)),seed=block,wall_seconds=wall,registration=reg)]
    for r in reg:
        if r['valid']=='1':accepted[int(r['dtype']),int(r['N'])]=str(out.relative_to(root))
    for attempt in range(1,4):
        pending={(int(r['dtype']),int(r['N'])) for r in reg}-set(accepted)
        if not pending:break
        listing=target/f'b{block:02d}-a{attempt}.list'
        listing.write_text(''.join(name+'\n' for name,r in points.items() if (r['dtype'],r['n']) in pending))
        out=target/f'b{block:02d}-a{attempt}';seed=block+attempt*1000
        rr,wall=run(out,seed,listing);attempts.append(dict(path=str(out.relative_to(root)),seed=seed,wall_seconds=wall,registration=rr))
        for r in rr:
            if r['valid']=='1':accepted[int(r['dtype']),int(r['N'])]=str(out.relative_to(root))
    assert len(accepted)==10,f'Replay block {block}: drift persists after retries'
    journal.write_text(json.dumps(dict(block=block,groups=[dict(dtype=k[0],N=k[1],path=v) for k,v in sorted(accepted.items())],attempts=attempts),indent=2))
    print('REPLAY_BLOCK_ACCEPTED',block,'wall_seconds',sum(r['wall_seconds'] for r in attempts),flush=True)
print('REPLAY_FORMAL_COMPLETE 20 blocks',flush=True)
