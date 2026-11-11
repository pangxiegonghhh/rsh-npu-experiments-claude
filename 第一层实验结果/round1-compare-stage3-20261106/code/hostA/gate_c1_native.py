import hashlib,json,os
from pathlib import Path
from native import BASE
from external_c1 import execute
from evaluate_t23 import read_order
from resource_slots import acquire
slot=acquire();checks=[]
for variant in ['J','H']:
 pi,diag=execute('cora',variant,0,use_native=True);p=BASE/'work/external'/f'cora__C1-{variant}__W16__seed0.record.json';old=json.loads(p.read_text());assert pi==read_order(old['path']);assert all(diag[k]==old['diagnostics'][k] for k in ['graph_components','graph_edges','zero_distance_edges','recall_at16']);checks.append(dict(variant=variant,identical_order_sha256=old['sha256'],identical_diag=True));print('C1-'+variant+' NATIVE_IDENTICAL',flush=True)
(BASE/'logs/c1-native-forest-gate.json').write_text(json.dumps(dict(passed=True,checks=checks,unchanged_PyNNDescent=True,n_jobs=1),indent=2))
