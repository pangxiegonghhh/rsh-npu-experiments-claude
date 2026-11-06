from __future__ import annotations
import json,os,sys
from pathlib import Path
sys.dont_write_bytecode=True
from campaign import BASE,load_adj,evaluate
from fast import FastGraph
adj=load_adj('cora');orders=json.loads((BASE/'work/selfcheck/out/orders.json').read_text());graph=FastGraph(adj);cases=[]
for tau,lam,start,seed in [(None,0.,'rsh',0),(None,1.,'gorder',1),(2,.5,'rsh',2),(2,1.,'gorder',0),(3,2.,'rabbit',1),(3,.5,'rsh',0)]:
    order,info=graph.ls(orders[start],16,tau,lam,seed)
    e=evaluate(order,adj,16,tau,'none' if tau is None else 'tail','A0')
    assert (e['sumU'],e['sumGamma'])==(info['tracked_sumU'],info['tracked_sumGamma'])
    cases.append({'tau':tau,'lambda':lam,'start':start,'seed':seed,'row_perm':order,'info':info})
graph.close();Path(sys.argv[1]).write_text(json.dumps(cases,separators=(',',':')))
