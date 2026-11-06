"""T21 analysis helpers: load results.csv + joint.csv and tag member variants (C6-M by mnc, P-LS by start/lambda/seed).

If the T21 supplement directory (rq2-c6align-20261106, pattern1 x C6 / C6-M after alignment repair) is present,
its 64 rows replace the 64 INCOMPLETE pattern1 C6 / C6-M rows of joint.csv. Set RQ2_NO_SUPPLEMENT=1 to disable.
"""
import json, os, sys, pandas as pd, numpy as np
from pathlib import Path
BASE=str(Path(__file__).resolve().parents[2]/'第一层实验结果'/'rq2-validate-20261106')+'/'
SUPP=str(Path(__file__).resolve().parents[2]/'第一层实验结果'/'rq2-c6align-20261106')+'/'
def load():
    r=pd.read_csv(BASE+'results.csv'); j=pd.read_csv(BASE+'joint.csv')
    r=r[~r.member.isin(['P-LS','P-LS-full-control','C6','C6-M'])].copy()
    r['mv']=r.member
    if os.path.exists(SUPP+'joint-c6align.csv') and not os.environ.get('RQ2_NO_SUPPLEMENT'):
        s=pd.read_csv(SUPP+'joint-c6align.csv')
        drop=(j.matrix=='pattern1')&j.member.isin(['C6','C6-M'])
        assert drop.sum()==64 and (j[drop].status=='INCOMPLETE').all() and len(s)==64 and (s.status=='OK').all()
        j=pd.concat([j[~drop],s],ignore_index=True)
        print('[load] pattern1 C6 / C6-M: 64 INCOMPLETE rows replaced by rq2-c6align-20261106', file=sys.stderr)
    j=j.copy()
    def jv(x):
        if x.member in ('C6','C6-M'): return f"{x.member}(mnc={int(x.mnc)})" if x.member=='C6-M' else 'C6'
        return f"{x.member}[{x.start},λ={x['lambda']:g},s={int(x.seed)}]"
    j['mv']=j.apply(jv,axis=1)
    cols=list(r.columns)
    d=pd.concat([r,j[[c for c in j.columns if c in cols]+['start','lambda','mnc','seed']]],ignore_index=True)
    d['tau']=d['tau'].astype(str)
    return d
BASE_MEMBERS=['B0','rsh-α0','rabbit-pilot','neutron-pilot','C9-Gorder','C9-S','C10-BP','B-RCM-ref','SlashBurn','C6','C6-M(mnc=4)']
