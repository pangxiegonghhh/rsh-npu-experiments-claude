"""T21 analysis helpers: load results.csv + joint.csv and tag member variants (C6-M by mnc, P-LS by start/lambda/seed)."""
import json, pandas as pd, numpy as np
from pathlib import Path
BASE=str(Path(__file__).resolve().parents[2]/'第一层实验结果'/'rq2-validate-20261106')+'/'
def load():
    r=pd.read_csv(BASE+'results.csv'); j=pd.read_csv(BASE+'joint.csv')
    r=r[~r.member.isin(['P-LS','P-LS-full-control','C6','C6-M'])].copy()
    r['mv']=r.member
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
