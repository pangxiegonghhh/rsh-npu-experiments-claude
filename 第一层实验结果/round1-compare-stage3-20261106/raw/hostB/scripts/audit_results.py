import csv,json,math,sys
from pathlib import Path
from native import BASE
def audit(path):
 rows=list(csv.DictReader(open(path)));checked=0;groups={};baselines={};errors=[]
 for r in rows:
  if r.get('status')!='OK':continue
  key=(r['matrix'],r['diag'],int(r['W']),str(r['tau']),r['placement'],r['d_rule'])
  if r['member']=='B0' and str(r.get('seed','0')) in ['','0'] and r['source']=='own':baselines[key]=r
  k=int(r['k_windows']);U=int(r['sumU']);T=int(r['T']);R=int(r['sumR']);G=int(r['sumGamma']);assert U>=R>=0 and U>=G>=0 and 0<=T<=U and 16*T>=U,(path,r)
  assert int(r['R_max'])>=int(r['R_p90'])>=int(r['R_p50'])>=0
  if k:
   assert abs(float(r['meanU'])-U/k)<1e-6
   assert abs(float(r['meanGamma'])-G/k)<1e-6
   assert abs(float(r['meanR'])-R/k)<=.500001e-6
  if r.get('sumR_minus_Gamma','')!='':assert int(r['sumR_minus_Gamma'])==R-G
  membership=(r['matrix'],r['diag'],r['member'],int(r['W']),str(r['tau']),r['source'],str(r.get('seed','0')))
  if membership in groups:assert groups[membership]==(U,T,k),(membership,groups[membership],(U,T,k))
  else:groups[membership]=(U,T,k)
  checked+=1
 for r in rows:
  key=(r['matrix'],r['diag'],int(r['W']),str(r['tau']),r['placement'],r['d_rule'])
  b=baselines.get(key)
  if r.get('status')=='OK' and r.get('T_ratio_B0','')!='' and b and float(b['T']):assert abs(float(r['T_ratio_B0'])-float(r['T'])/float(b['T']))<1e-12
 return dict(path=str(path),rows=len(rows),successful_rows_checked=checked,fixed_membership_UT_groups=len(groups),passed=True)
if __name__=='__main__':
 path=Path(sys.argv[1]);result=audit(path);p=BASE/'logs'/('audit-'+path.parent.name+'.json');p.write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
