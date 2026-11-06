from __future__ import annotations
import ast, csv, importlib.util, json, os, sys, time
from pathlib import Path
sys.dont_write_bytecode = True
BASE = Path(__file__).resolve().parents[1]
REPO = Path("/Users/Zhuanz/.codex/visualizations/2026/11/05/01a1ac73-0f55-70c0-8e27-bb94bed5ad09/t21-rq2-20261106/repo")
REF = REPO / '第一层工作区/T17-空白一试算脚本'
os.environ['RQ2_HK'] = str(BASE / 'work/selfcheck/rq2_hk_bin')
sys.path.insert(0, str(REF))
from rq2lib import load_cora, evaluate, dstage
from methods import rcm, slashburn
from fast import FastGraph

assert json.loads((BASE/'logs/selfcheck-gate.json').read_text())['passed']
n, adj = load_cora(); graph = FastGraph(adj)
orders = json.loads((BASE/'work/selfcheck/out/orders.json').read_text())
native = {'original': list(range(n)), 'rcm': rcm(adj), 'slashburn': slashburn(adj)}
if os.environ.get('RQ2_USE_NATIVE_SLASHBURN')=='1':
    from slashburn_fast import reorder
    native['slashburn']=reorder(graph)
for key in ('rsh','rabbit','neutron'): native[key] = graph.order(key)
native.update({'bp': graph.bp(), 'gorder': graph.order('gorder'), 'gorder-S': graph.order('gorder', beta=0.)})
checks = {'native_orders_equal_reference': {m: native[m] == orders[m] for m in orders}, 'TableA': []}
print(checks['native_orders_equal_reference'], flush=True)
assert all(checks['native_orders_equal_reference'].values()), checks
expected = {r['member']: r for r in csv.DictReader((BASE/'work/selfcheck/out/table_a.csv').open())}
for member, order in native.items():
    before = evaluate(order, adj); new = dstage(order, adj); after = evaluate(new, adj)
    greedy = evaluate(dstage(order, adj, intra='greedy'), adj)
    assert (before['sumU'], before['sumG']) == (after['sumU'], after['sumG'])
    actual = [round(before['U'],2), before['T'], round(before['G'],2), round(before['R'],2), round(after['R'],2), round(greedy['R'],2)]
    exp = [float(expected[member][x]) for x in ('U','T','Gamma','R_own','R_Dexact','R_Dgreedy')]
    assert all(abs(a-b) <= .01 for a,b in zip(actual,exp)), (member,actual,exp)
    checks['TableA'].append({'member':member,'actual':actual,'expected':exp,'passed':True})
    print(member, actual, flush=True)
graph.close()
checks['passed'] = True
(BASE/'logs/port-validation.json').write_text(json.dumps(checks, indent=2))
print('Accelerated Table A self-check: OK', flush=True)
