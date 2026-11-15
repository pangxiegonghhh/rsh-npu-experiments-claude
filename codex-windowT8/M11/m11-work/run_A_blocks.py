"""Compare A paths in shared randomized blocks, with the same raw column-major A."""
from pathlib import Path
import json,csv,hashlib,subprocess,random,statistics,time
ROOT=Path(__file__).resolve().parent

def main(blocks:int=20)->None:
 binary=ROOT/'build/t8_micro';gate=json.loads((ROOT/'GATES-PASSED.json').read_text());assert gate['binary_sha256']==hashlib.sha256(binary.read_bytes()).hexdigest()
 regroot=ROOT/'results-A-paired';regroot.mkdir(exist_ok=True);records=[]
 sentinel_list=ROOT/'A-sentinel.list';sentinel_list.write_text(('micro-copy-FP32-n256-h16-p1-b4096\n')*5)
 def run(out:Path,mode:int,block:int,sentinel:bool=False)->float|None:
  out.mkdir(parents=True,exist_ok=False)
  with (out/'run.log').open('w') as log:
   p=subprocess.run([str(binary),'check',str(out),str(sentinel_list if sentinel else ROOT/'a-micro.list'),str(block),str(mode)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=600)
  if p.returncode:raise RuntimeError(f'A-path failure mode={mode} block={block} path={out}')
  groups=list(csv.DictReader((out/'group-registration.csv').open()));assert all(g['input_immutable']=='1' for g in groups)
  if sentinel:return statistics.median(float(r['us']) for r in csv.DictReader((out/'timing.csv').open()))
  assert len(list(csv.DictReader((out/'timing.csv').open())))==40
 for block in range(blocks):
  for attempt in range(3):
   now=time.time();location=regroot/f'b{block:02}-attempt{attempt}';location.mkdir(exist_ok=False)
   before=run(location/'sentinel-before',0,block,True);order=[1,2];random.Random(20261115+block).shuffle(order);paths={}
   for mode in order:
    base=ROOT/f'results-a-micro-a{mode}';base.mkdir(exist_ok=True);out=base/f'b{block:02}-attempt{attempt}';run(out,mode,block);paths[mode]=str(out.relative_to(ROOT))
   after=run(location/'sentinel-after',0,block,True);drift=abs(after-before)/before;valid=drift<=.05
   r=dict(block=block,attempt=attempt,valid=valid,mode_order=order,before_us=before,after_us=after,drift=drift,elapsed_s=time.time()-now,mode_paths=paths,paired_block=True)
   records.append(r);(regroot/'attempt-registration.json').write_text(json.dumps(records,indent=2));print(json.dumps(r),flush=True)
   for mode,path in paths.items():
    item=dict(r,path=path,a_mode=mode,returncode=0,groups=list(csv.DictReader((ROOT/path/'group-registration.csv').open())))
    (ROOT/f'results-a-micro-a{mode}'/f'b{block:02}-attempt{attempt}.json').write_text(json.dumps(item,indent=2))
    if valid:(ROOT/f'results-a-micro-a{mode}'/f'b{block:02}-accepted.json').write_text(json.dumps(item,indent=2))
   if valid:break
  else:raise RuntimeError('three invalid A-block attempts')
 print('M11_A_PAIRED_BLOCKS_COMPLETE',flush=True)
if __name__=='__main__':main()
