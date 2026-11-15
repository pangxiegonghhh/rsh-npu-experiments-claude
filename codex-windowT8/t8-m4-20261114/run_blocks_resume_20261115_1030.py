"""Resume the unchanged, registered 20-block experiment on verified physical NPU 1."""
import csv
import hashlib
import json
import statistics
import subprocess
import time
from pathlib import Path

root=Path(__file__).resolve().parent
epoch='20261115-1030'
p0=root.parent/f'p0-resume-{epoch}'
assert (p0/'p0-timing.rc').read_text().strip()=='0'
p0_files=list((p0/'results/p0-timing').glob('summary*.json'));assert len(p0_files)==1
p0_summary=json.loads(p0_files[0].read_text())
assert len(p0_summary)==2 and all(r['pass_gate'] for r in p0_summary)
registration=json.loads((root/'formal-registration-v5.json').read_text())
assert all(hashlib.sha256((root/name).read_bytes()).hexdigest()==digest
           for name,digest in registration['source_hashes'].items()),'Registered source changed'
rows=json.loads((root/'m4-manifest.json').read_text())
points={r['name']:r for r in rows if 'alias_of' not in r};assert len(points)==2592
assert (root/'check-v5.rc').read_text().strip()=='0'
assert json.loads((root/'model-v5-verification.json').read_text())['status']=='PASS'

def verify_accepted(path):
    journal=json.loads(path.read_text());assert journal['block']==int(path.name[1:3])
    assert len(journal['groups'])==10
    names=set()
    for g in journal['groups']:
        directory=root/g['path']
        regs=list(csv.DictReader((directory/'group-registration.csv').open()))
        valid=[r for r in regs if (int(r['dtype']),int(r['N']))==(g['dtype'],g['N'])]
        assert len(valid)==1 and valid[0]['valid']=='1' and valid[0]['input_immutable']=='1'
        assert float(valid[0]['drift'])<=.05
        for r in csv.DictReader((directory/'timing.csv').open()):
            geom=points[r['case']]
            if (int(geom['dtype']=='FP32'),geom['n'])!=(g['dtype'],g['N']):continue
            gate=json.loads((directory/r['case']/'gate.json').read_text())
            assert gate['status']=='PASS' and gate['guards'] and gate['metadata_input_immutable']
            assert float(r['us'])>0 and r['case'] not in names
            names.add(r['case'])
    assert names==set(points),'Incomplete accepted block'
    return journal['block']

target=root/'results-blocks-v5'
existing=[verify_accepted(p) for p in sorted(target.glob('b*-accepted.json'))]
assert existing==list(range(6)),f'Unexpected checkpoint: {existing}'
print('VERIFIED_PRE_PAUSE_BLOCKS',existing,flush=True)
for name in ('acl_probe','resource_probe'):
    with (p0/f'{name}.txt').open('w') as log:
        subprocess.run([str(root.parent/'k0-r3/p0'/name)],cwd=root.parent/'k0-r3/p0',stdout=log,stderr=subprocess.STDOUT,check=True)
with (p0/'m4-first.log').open('w') as log:
    subprocess.run([str(root/'build/t8_micro'),'first',str(root/f'results-first-resume-{epoch}')],cwd=root,
                   stdout=log,stderr=subprocess.STDOUT,check=True)
assert 'M4_ALL_PASS 24 mode=first' in (p0/'m4-first.log').read_text()
pilot_source=(root/'run_pilot.py').read_text().replace('results-pilot-v5',f'results-pilot-resume-{epoch}')
pilot_source=pilot_source.replace('pilot-v5',f'pilot-resume-{epoch}').replace("'pilot.list'",f"'pilot-resume-{epoch}.list'")
pilot_file=root/f'run_pilot_resume_{epoch}.py';assert not pilot_file.exists();pilot_file.write_text(pilot_source)
with (root/f'pilot-driver-resume-{epoch}.log').open('w') as log:
    subprocess.run(['python3',str(pilot_file)],cwd=root,stdout=log,stderr=subprocess.STDOUT,check=True)
pilot=json.loads((root/f'pilot-resume-{epoch}-summary.json').read_text())
assert len(pilot)==5 and all(r['valid'] for r in pilot)
samples={}
for b in range(5):
    for r in csv.DictReader((root/f'results-pilot-resume-{epoch}'/f'b{b:02d}'/'timing.csv').open()):
        samples.setdefault(r['case'],[]).append(r)
noise=[]
for name,data in samples.items():
    sigma=statistics.stdev(float(r['us']) for r in data)
    signal=.005*32*int(data[0]['windows_per_core'])
    noise.append(dict(case=name,sigma_us=sigma,signal_us=signal,pass_gate=signal>=10*sigma))
(root/f'resume-resolution-{epoch}.json').write_text(json.dumps(noise,indent=2))
assert all(r['pass_gate'] for r in noise),'Resume resolution gate failed'
resume=dict(epoch=epoch,pre_pause_blocks=existing,physical_npu=1,node='dengjia-ascend910b-node02',
            p0=p0_summary,unchanged_source_hashes=registration['source_hashes'],
            output_policy='New output directories; preserve the interrupted b06-a0 and all accepted pre-pause data',
            start_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()))
(root/f'resume-registration-{epoch}.json').write_text(json.dumps(resume,indent=2))
print('RESUME_QUALIFIED',epoch,flush=True)

def run(out,seed,listing=None):
    assert not out.exists(),f'Output already exists: {out}'
    cmd=[str(root/'build/t8_micro'),'timeblock',str(out),str(seed)]
    if listing:cmd.append(str(listing))
    started=time.monotonic()
    with out.with_suffix('.log').open('w') as log:
        rc=subprocess.run(cmd,cwd=root,stdout=log,stderr=subprocess.STDOUT).returncode
    assert rc==0,f'Correctness/runtime failure in {out}; stop'
    reg=list(csv.DictReader((out/'group-registration.csv').open()))
    assert all(r['input_immutable']=='1' for r in reg)
    return reg,time.monotonic()-started

for block in range(6,20):
    journal=target/f'b{block:02d}-accepted.json';assert not journal.exists()
    out=target/f'b{block:02d}-resume-{epoch}-a0';reg,wall=run(out,block)
    accepted={};attempts=[dict(path=str(out.relative_to(root)),seed=block,wall_seconds=wall,registration=reg)]
    for r in reg:
        if r['valid']=='1':accepted[int(r['dtype']),int(r['N'])]=str(out.relative_to(root))
    for attempt in range(1,4):
        pending={(int(r['dtype']),int(r['N'])) for r in reg}-set(accepted)
        if not pending:break
        listing=target/f'b{block:02d}-resume-{epoch}-a{attempt}.list'
        listing.write_text(''.join(name+'\n' for name,r in points.items() if (int(r['dtype']=='FP32'),r['n']) in pending))
        retry=target/f'b{block:02d}-resume-{epoch}-a{attempt}';seed=block+attempt*1000
        rr,wall=run(retry,seed,listing);attempts.append(dict(path=str(retry.relative_to(root)),seed=seed,wall_seconds=wall,registration=rr))
        for r in rr:
            if r['valid']=='1':accepted[int(r['dtype']),int(r['N'])]=str(retry.relative_to(root))
    assert len(accepted)==10,f'Block {block}: drift persists'
    journal.write_text(json.dumps(dict(block=block,epoch=epoch,groups=[dict(dtype=k[0],N=k[1],path=v) for k,v in sorted(accepted.items())],attempts=attempts),indent=2))
    print('BLOCK_ACCEPTED',block,'wall_seconds',sum(r['wall_seconds'] for r in attempts),flush=True)
assert len(list(target.glob('b*-accepted.json')))==20
print('M4_FORMAL_COMPLETE 20 blocks',flush=True)
