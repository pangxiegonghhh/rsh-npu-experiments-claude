from __future__ import annotations
import json,sys,time
from pathlib import Path
sys.dont_write_bytecode=True
from campaign import BASE,load_adj,order_for,evaluate
from fast import FastGraph,LIB
adj=load_adj('ogbn-arxiv');graph=FastGraph(adj)
order,_,_=order_for('ogbn-arxiv','C9-Gorder',16,graph)
t=time.perf_counter();out,info=graph.ls(order,16,2,2.,2,sweeps=1)
elapsed=time.perf_counter()-t
actual=info['history'][0];expected={'sweep':0,'accepted':39670,'sumU':1250825,'sumGamma':548589}
metrics=evaluate(out,adj,16,2,'tail','A0')
assert actual==expected,(actual,expected)
assert (metrics['sumU'],metrics['sumGamma'])==(actual['sumU'],actual['sumGamma'])
result={'passed':True,'same_reference_first_sweep_counters_and_accepted':True,'expected':expected,'actual':actual,'elapsed_sec':elapsed,'library':str(LIB._name)}
Path(sys.argv[1]).write_text(json.dumps(result));graph.close();print(result,flush=True)
