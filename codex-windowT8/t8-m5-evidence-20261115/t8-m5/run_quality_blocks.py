from pathlib import Path
import subprocess,json,csv,statistics as st,time
root=Path('results-quality');root.mkdir(exist_ok=True);records=[]
def run(mode,out,block=0):
 out.mkdir(parents=True,exist_ok=True)
 with (out/'run.log').open('w') as log:p=subprocess.run(['timeout','600','./build/t8_micro',mode,str(out),str(block),*(['quality-filter.txt'] if mode=='qualityblock' else [])],stdout=log,stderr=subprocess.STDOUT)
 if p.returncode:raise RuntimeError(f'{mode} {out} RC={p.returncode}')
 if mode=='sentinel':return st.median(float(x['us']) for x in csv.DictReader((out/'timing.csv').open()))
for block in range(20):
 for attempt in range(3):
  target=root/f'b{block:02d}-a{attempt}';start=run('sentinel',target/'sentinel-before');t0=time.time();run('qualityblock',target/'samples',block);end=run('sentinel',target/'sentinel-after');drift=abs(end-start)/start;valid=drift<=.05;r=dict(block=block,attempt=attempt,start_us=start,end_us=end,drift=drift,valid=valid,elapsed_s=time.time()-t0,path=str(target));records.append(r);(root/'block-registration.json').write_text(json.dumps(records,indent=2));print(json.dumps(r),flush=True)
  if valid:break
 else:raise RuntimeError('three unstable attempts')
print('M5_QUALITY_BLOCKS_COMPLETE',flush=True)
