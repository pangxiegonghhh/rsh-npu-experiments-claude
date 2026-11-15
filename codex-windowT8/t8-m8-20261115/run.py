"""Run correctness before timing, retain drift failures, checkpoint each accepted block."""
from pathlib import Path
import subprocess,json,csv,time,gzip,shutil,hashlib,sys
p=Path(__file__).resolve().parent
def run(args,out,env=None):
    out.mkdir(parents=True,exist_ok=False)
    with (out/'driver.log').open('w') as log:
        a=subprocess.run([str(p/'build/t8_micro'),*args,str(out)],cwd=p,stdout=log,stderr=subprocess.STDOUT,env=env)
    if a.returncode:raise RuntimeError(f'{out.name} failed rc={a.returncode}; see driver.log')
def invoke(mode,out,block=0,listing='cases.list',env=None):
    out.mkdir(parents=True,exist_ok=False)
    with (out/'driver.log').open('w') as log:
        a=subprocess.run([str(p/'build/t8_micro'),mode,str(out),str(block),listing],cwd=p,stdout=log,stderr=subprocess.STDOUT,env=env)
    if a.returncode:raise RuntimeError(f'{out.name} failed rc={a.returncode}; see driver.log')
def compress_readbacks(root):
    for file in root.glob('*/readback-f32.bin'):
        with file.open('rb') as src,gzip.open(str(file)+'.gz','wb',compresslevel=1) as dst:shutil.copyfileobj(src,dst)
        file.unlink()
def status(**kw):
    state=dict(updated=time.strftime('%Y-%m-%dT%H:%M:%S%z'),**kw)
    (p/'status.json').write_text(json.dumps(state,indent=2));print(json.dumps(state),flush=True)
def main():
    import os
    if not (p/'results-first').exists():
        status(stage='single_core_correctness',cases=48);invoke('first',p/'results-first',listing='first.list');compress_readbacks(p/'results-first')
    if not (p/'results-stress').exists():
        status(stage='whole_card_stress',cases=48);env=dict(os.environ,M8_STRESS='1');invoke('check',p/'results-stress',listing='first.list',env=env);compress_readbacks(p/'results-stress')
    if not (p/'results-check').exists():
        status(stage='all_correctness',cases=840);invoke('check',p/'results-check');compress_readbacks(p/'results-check')
    for path,count in [(p/'results-first',48),(p/'results-stress',48),(p/'results-check',840)]:
        gates=list(path.glob('*/gate.json'));assert len(gates)==count and all(json.loads(q.read_text())['status']=='PASS' for q in gates)
    status(stage='correctness_pass',cases=840)
    # Caller may inspect correctness and new-card timing before authorizing formal dispatch locally.
    if '--check-only' in sys.argv:return
    manifest={q['name']:q for q in json.loads((p/'manifest.json').read_text())}
    pilot='--pilot' in sys.argv
    blocks=p/('pilot-blocks' if pilot else 'blocks');blocks.mkdir(exist_ok=True)
    for block in range(1 if pilot else 20):
        journal=blocks/f'b{block:02d}-accepted.json'
        if journal.exists():continue
        status(stage='timing',block=block,accepted=block)
        out=blocks/f'b{block:02d}-try0';invoke('timeblock',out,block)
        accepted=[]
        for group in csv.DictReader((out/'groups.csv').open()):
            key=(int(group['dtype']),int(group['N']));chosen=out;attempt=0
            while group['valid']!='1':
                attempt+=1
                if attempt>3:raise RuntimeError(f'drift repeatedly failed block={block} group={key}')
                names=[name for name,m in manifest.items() if (m['dtype'],m['n'])==key]
                listing=blocks/f'b{block:02d}-{key[0]}-{key[1]}.list';listing.write_text('\n'.join(names)+'\n')
                chosen=blocks/f'b{block:02d}-retry{attempt}-{key[0]}-{key[1]}'
                invoke('timeblock',chosen,block,str(listing))
                retry=list(csv.DictReader((chosen/'groups.csv').open()));assert len(retry)==1;group=retry[0]
            accepted.append(dict(dtype=key[0],N=key[1],path=str(chosen.relative_to(p)),attempt=attempt,drift=float(group['drift'])))
        assert len(accepted)==10
        journal.write_text(json.dumps(dict(block=block,groups=accepted),indent=2))
    if pilot:status(stage='pilot_complete',accepted=1);return
    status(stage='timing_complete',accepted=20)
    subprocess.run([sys.executable,str(p/'analyze.py')],check=True,cwd=p)
    status(stage='complete',accepted=20)
if __name__=='__main__':
    try:main()
    except Exception as e:status(stage='failed',error=str(e));raise
