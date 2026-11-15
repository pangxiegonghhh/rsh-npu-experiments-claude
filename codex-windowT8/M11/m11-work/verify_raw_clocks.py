"""Recompute every accepted observation from saved device clocks; no binary execution."""
from pathlib import Path
import argparse,csv,json,struct,math

def main()->None:
 p=argparse.ArgumentParser();p.add_argument('root',type=Path);a=p.parse_args();root=a.root;report=[];total=0
 for stage,mode,expected in [('stage3',0,216),('stage2',0,2000),('a-micro',1,40),('a-micro',2,40)]:
  base=root/f'results-{stage}-a{mode}';journals=sorted(base.glob('b*-accepted.json'));assert len(journals)==20
  for journal in journals:
   reg=json.loads(journal.read_text());assert reg['valid'];folder=root/reg['path'];rows=list(csv.DictReader((folder/'timing.csv').open()));assert len(rows)==expected
   for row in rows:
    raw=(folder/row['case']/'stats.bin').read_bytes();words=struct.unpack('<'+'I'*(len(raw)//4),raw);cores=int(row['blocks']);assert len(words)==cores*32
    starts=[];ends=[]
    for core in range(cores):
     w=words[core*32:(core+1)*32];starts.append(w[0]+(w[1]<<32));ends.append(w[2]+(w[3]<<32));assert ends[-1]>starts[-1]
     assert w[4]==int(row['api_calls'])
     if stage!='stage3':assert w[5]==int(row['case'].rsplit('-b',1)[1])
    us=(max(ends)-min(starts))/50.;assert math.isclose(us,float(row['us']),rel_tol=1e-10,abs_tol=1e-9),row['case']
    assert math.isclose(us/(int(row['cycles'])*cores),float(row['us_per_matrix']),rel_tol=1e-10,abs_tol=1e-9)
    total+=1
  report.append(dict(stage=stage,a_mode=mode,blocks=20,points=expected,observations=expected*20))
 assert total==45920
 result=dict(status='PASS',observations=total,device_clock_recomputation=True,normalization_verified=True,raw_counter_matches_csv=True,recovered_binaries_executed=False,stages=report)
 (root/'LOCAL-CLOCK-VERIFICATION.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':main()
