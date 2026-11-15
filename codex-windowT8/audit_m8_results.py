"""Read-only verification of M8 accepted samples and all primary block fits."""
from pathlib import Path
import argparse,csv,hashlib,json,statistics as S
import numpy as np
def main():
 parser=argparse.ArgumentParser();parser.add_argument('root',nargs='?',default=str(Path(__file__).resolve().parent/'t8-m8-results-20261115'));parser.add_argument('--out');args=parser.parse_args();p=Path(args.root)
 v=json.loads((p/'recovery-verification.json').read_text(encoding='utf-8'));raw=(p/'timing-observations.csv').read_bytes();assert hashlib.sha256(raw).hexdigest()==v['original_csv_sha256'];a=json.loads((p/'analysis.json').read_text(encoding='utf-8'));assert hashlib.sha256((p/'analysis.json').read_bytes()).hexdigest()==v['remote_analysis_sha256']
 rows=list(csv.DictReader(raw.decode('ascii').splitlines()));assert len(rows)==16800;observed={}
 for row in rows:
  key=(row['case'],int(row['block']));assert key not in observed;observed[key]=float(row['us_per_window'])
 assert len({name for name,block in observed})==840 and {block for name,block in observed}==set(range(20));assert min(float(row['us']) for row in rows)>=1000
 for name,q in a['statistics'].items():
  values=[observed[name,b] for b in range(20)];assert values==q['values'];assert S.mean(values)==q['mean']
 manifest=json.loads((p/'manifest.json').read_text(encoding='utf-8'));error=0.;count=0
 for fit in a['fits']:
  cases=[m for m in manifest if (m['dtype'],m['n'],m['cache'],m['path'])==(fit['dtype'],fit['n'],fit['cache'],fit['path']) and not m['tag'].startswith('cora')];assert len(cases)==12;x=np.array([[1,m['u'],m['r']] for m in cases],float)
  for b in range(20):
   c=np.linalg.lstsq(x,np.array([observed[m['name'],b] for m in cases]),rcond=None)[0];d=float(np.max(np.abs(c-fit['block_coefficients'][b])));error=max(error,d);assert d<1e-10;count+=1
 result=dict(status='PASS',cases=840,blocks=20,observations=16800,primary_analysis_source_hash_matches=True,independent_numpy_block_fits=count,max_coefficient_error_us=error,evidence_modified=False)
 if args.out:Path(args.out).write_text(json.dumps(result,indent=2),encoding='utf-8')
 print(json.dumps(result))
if __name__=='__main__':main()
