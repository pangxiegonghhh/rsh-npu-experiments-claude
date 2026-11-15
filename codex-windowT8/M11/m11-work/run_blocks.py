"""Run only after complete correctness gates. Persist all attempts and group decisions."""
from pathlib import Path
import argparse,csv,json,subprocess,time,hashlib,statistics
root=Path(__file__).resolve().parent

def main()->None:
 p=argparse.ArgumentParser();p.add_argument('--stage',choices=['stage2','stage3','a-micro'],required=True);p.add_argument('--a-mode',type=int,default=0);p.add_argument('--blocks',type=int,default=20);args=p.parse_args()
 if args.stage=='a-micro':
  if args.a_mode==1:
   from run_A_blocks import main as paired_main
   paired_main(args.blocks)
  else:
   assert all(len(list((root/f'results-a-micro-a{m}').glob('b*-accepted.json')))==args.blocks for m in [1,2])
   print('A paths already completed in shared randomized blocks',flush=True)
   from run_strong_gate import main as strong_gate
   strong_gate()
  return
 # Timing is never started implicitly by source upload or compilation.
 gate=root/'GATES-PASSED.json'
 assert gate.exists(), 'full correctness evidence must be explicitly registered first'
 validation=json.loads(gate.read_text());assert validation['status']=='PASS'
 binary=root/'build/t8_micro';digest=hashlib.sha256(binary.read_bytes()).hexdigest();assert validation['binary_sha256']==digest
 target=root/f'results-{args.stage}-a{args.a_mode}';target.mkdir(exist_ok=True);records=[]
 micro=args.stage!='stage3'
 sentinel_name='micro-copy-FP32-n256-h16-p1-b4096'
 sentinel_list=root/'micro-sentinel.list';sentinel_list.write_text((sentinel_name+'\n')*5)
 def sentinel(out:Path)->float:
  out.mkdir(exist_ok=True)
  with (out/'run.log').open('w') as log:
   result=subprocess.run([str(binary),'check',str(out),str(sentinel_list),'0',str(args.a_mode)],cwd=root,stdout=log,stderr=subprocess.STDOUT,timeout=120)
  assert result.returncode==0, out
  values=[float(r['us']) for r in csv.DictReader((out/'timing.csv').open())]
  assert len(values)==5
  return statistics.median(values)
 for block in range(args.blocks):
  accepted=None
  for attempt in range(3):
   out=target/f'b{block:02}-attempt{attempt}';out.mkdir(exist_ok=False)
   before=sentinel(out/'sentinel-before') if micro else None
   cmd=[str(binary),'check' if micro else 'timeblock',str(out),str(root/(args.stage+'.list')),str(block),str(args.a_mode)]
   start=time.time()
   with (out/'run.log').open('w') as f:r=subprocess.run(cmd,cwd=root,stdout=f,stderr=subprocess.STDOUT,timeout=3600)
   after=sentinel(out/'sentinel-after') if micro else None
   item=dict(block=block,attempt=attempt,returncode=r.returncode,elapsed_s=time.time()-start,path=str(out.relative_to(root)),groups=[])
   if r.returncode:
    records.append(item);(target/'attempt-registration.json').write_text(json.dumps(records,indent=2));raise RuntimeError(f'case/gate failure: {out}')
   with (out/'group-registration.csv').open() as f:item['groups']=list(csv.DictReader(f))
   if micro:
    item['external_sentinel']=dict(before_us=before,after_us=after,drift=abs(after-before)/before,source_pool_bytes=64*1024**2,scope='full random block')
   item['valid']=(not micro or item['external_sentinel']['drift']<=.05) and bool(item['groups']) and all(x['valid']=='1' and x['input_immutable']=='1' for x in item['groups'])
   records.append(item);(target/'attempt-registration.json').write_text(json.dumps(records,indent=2))
   print(json.dumps(item),flush=True)
   if item['valid']:accepted=item;break
  if not accepted:raise RuntimeError(f'three drift-invalid attempts in block {block}')
  (target/f'b{block:02}-accepted.json').write_text(json.dumps(accepted,indent=2))
 print('M11_BLOCKS_COMPLETE',args.stage,args.a_mode,flush=True)
if __name__=='__main__':main()
