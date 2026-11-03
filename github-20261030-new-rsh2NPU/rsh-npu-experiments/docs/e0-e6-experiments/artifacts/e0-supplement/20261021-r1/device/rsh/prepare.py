from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np

from .planner import Matrix, reorder, partition, layout, execute_cpu

VARIANTS = ['V0', 'V1', 'V2', 'H-V', 'H-C', 'H-Skip', 'V0-R', 'V2-R']


def export(a: Matrix, plan: dict, b: np.ndarray, golden: np.ndarray, out: Path, metadata: dict) -> None:
    out.mkdir(parents=True, exist_ok=True)
    m,k = a.shape
    n = b.shape[1]
    stride = (n+15)//16*16
    padded_b = np.zeros((k+1,stride), np.float16)
    padded_b[:k,:n] = b
    expected = np.zeros((m,stride), np.float32)
    expected[:,:n] = golden
    arrays = {'ptr':a.ptr,'cols':a.col,'values':a.val,'cube_ptr':plan['cube_ptr'],
              'colref':plan['colref'],'tiles':plan['tiles'],'rowmap':plan['rowmap'],
              'srows':plan['srows'],'valid':plan['valid'],'rhs':padded_b,'golden':expected}
    hashes = {}
    for name,arr in arrays.items():
        data = np.ascontiguousarray(arr).tobytes()
        (out/f'{name}.bin').write_bytes(data)
        hashes[name] = hashlib.sha256(data).hexdigest()
    (out/'config.txt').write_text(f'{m} {k} {n} {stride} {len(a.col)} {len(plan["cube_ptr"])-1} {len(plan["tiles"])} {len(plan["srows"])}\n')
    (out/'metadata.json').write_text(json.dumps(metadata | {'variant':plan['variant'],'files_sha256':hashes,
        'coverage':'full' if np.all(plan['valid']) else 'retained_rows_only',
        'tail_skip_rows':np.flatnonzero(plan['valid']==0).tolist()}, indent=2))


def prepare(path: Path, out: Path, widths: list[int], tau_nnz: int = 4, tau_inc: int = 2) -> dict:
    started = time.perf_counter()
    a = Matrix.load(str(path))
    order, stats = reorder(a)
    split = partition(a, order, tau_nnz, tau_inc)
    plans = {}
    report = {'source':str(path),'input_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
              'shape':a.shape,'nnz':len(a.col),'reorder':stats,'tau_nnz':tau_nnz,'tau_inc':tau_inc,
              'cube_groups':len(split['groups']),'residual_rows':len(split['residual']),
              'tail_original_rows':split['tail'],'tail_nnz':int(sum(a.ptr[r+1]-a.ptr[r] for r in split['tail'])),
              'variants':{}}
    for variant in VARIANTS:
        t = time.perf_counter()
        plans[variant] = layout(a, order, split, variant)
        p = plans[variant]
        report['variants'][variant] = {'layout_seconds':time.perf_counter()-t,
            'groups':len(p['cube_ptr'])-1,'physical_k16_tiles':len(p['tiles']),
            'aiv_rows':len(p['srows']),'included_rows':int(p['valid'].sum())}
    from scipy.sparse import csr_matrix
    ref = csr_matrix((a.val.astype(np.float64),a.col,a.ptr), shape=a.shape)
    for n in widths:
        b = np.random.default_rng(20261017+n).uniform(-1,1,(a.shape[1],n)).astype(np.float16)
        golden = (ref @ b.astype(np.float64)).astype(np.float32)
        for variant,p in plans.items():
            if a.shape[0] <= 200:
                cpu = execute_cpu(a,p,b)
                keep = p['valid'].astype(bool)
                np.testing.assert_allclose(cpu[keep],golden[keep],atol=1e-2,rtol=1e-2)
            export(a,p,b,golden,out/f'N{n}'/variant,report | {'n':n,'b_seed':20261017+n})
    report['prepare_export_seconds'] = time.perf_counter()-started
    out.mkdir(parents=True,exist_ok=True)
    (out/'structure.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({'matrix':path.stem,'shape':a.shape,'groups':report['cube_groups'],
                      'tail_rows':len(split['tail']),'seconds':report['prepare_export_seconds']}),flush=True)
    return report


def main() -> None:
    p=argparse.ArgumentParser()
    p.add_argument('--matrix',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--widths',nargs='+',type=int,default=[64]);p.add_argument('--tau-nnz',type=int,default=4);p.add_argument('--tau-inc',type=int,default=2)
    args=p.parse_args()
    prepare(args.matrix,args.out,args.widths,args.tau_nnz,args.tau_inc)


if __name__ == '__main__': main()
