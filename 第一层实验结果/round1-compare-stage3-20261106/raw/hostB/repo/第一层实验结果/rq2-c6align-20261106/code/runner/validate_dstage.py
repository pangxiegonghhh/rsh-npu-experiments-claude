from __future__ import annotations
import csv,json,sys,time
from pathlib import Path
sys.dont_write_bytecode=True
from campaign import BASE,load_adj,ref,dump
from dstage_fast import dstage
adj=load_adj('cora');orders=json.loads((BASE/'work/selfcheck/out/orders.json').read_text());a={r['member']:r for r in csv.DictReader((BASE/'work/selfcheck/out/table_a.csv').open())};b={(r['member'],int(r['tau'])):r for r in csv.DictReader((BASE/'work/selfcheck/out/table_b.csv').open())};cases=[]
for member,order in orders.items():
    for tau in (None,2,3):
        own=ref.evaluate(order,adj,tau=tau,placement='tail')
        for rule in ('greedy','exact'):
            t=time.perf_counter();new=dstage(order,adj,tau=tau,intra=rule);e=ref.evaluate(new,adj,tau=tau,placement='tail')
            assert sorted(new)==list(range(len(adj))) and (own['sumU'],own['sumG'])==(e['sumU'],e['sumG'])
            expected=float(a[member]['R_D'+rule] if tau is None else b[(member,tau)]['R_tail_D'+rule])
            assert abs(round(e['R'],2)-expected)<=.01,(member,tau,rule,e,expected)
            cases.append({'member':member,'tau':tau,'intra':rule,'meanR':e['R'],'expected_rounded_meanR':expected,'sumU':e['sumU'],'sumGamma':e['sumG'],'passed':True,'sec':time.perf_counter()-t})
        print(member,tau,'OK',flush=True)
dump(BASE/'logs/dstage-validation.json',{'passed':True,'tables':['A','B'],'cases':cases,'cases_count':len(cases)})
print('Native D Tables A/B self-check: OK',flush=True)
