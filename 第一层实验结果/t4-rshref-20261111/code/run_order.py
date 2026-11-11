import argparse, hashlib, json, platform, resource, time, traceback
from pathlib import Path
import numpy as np
from native import BASE, Matrix, RectT4, Candidates
from memory_guard import ensure_limit

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('matrix'); ap.add_argument('alpha', type=float)
    ap.add_argument('k', type=int); ap.add_argument('iso', type=int)
    ap.add_argument('--tag', default=''); ap.add_argument('--c4', action='store_true')
    args = ap.parse_args()
    ensure_limit()
    name = 'C4-U-calibration' if args.c4 else 'B-RSH-ref'
    params = f'alpha={args.alpha:g},k={args.k},iso={"near" if args.iso else "tail"}'
    key = f'{args.matrix}__{name}__{params}{args.tag}'
    record = dict(matrix=args.matrix, t23_member=name, method=name, params=params,
                  W=16, seed=0, recorded_execution_host_id='hostA-macos-arm64',
                  hostname=platform.node(), alpha=args.alpha, k=args.k, iso=args.iso)
    started = time.time()
    try:
        m = Matrix(args.matrix)
        if args.c4:
            graph = Candidates(m)
            try: order, diag = graph.order('C4-U')
            finally: graph.close()
        else:
            graph = RectT4(m, np.flatnonzero(m.deg).tolist())
            try:
                order = graph.order_rsh(args.alpha, args.k, args.iso)
                diag = graph.diagnostics()
            finally: graph.close()
            empty = np.flatnonzero(m.deg == 0).tolist()
            order += empty
            diag['empty_rows_appended'] = len(empty)
        assert sorted(order) == list(range(m.n))
        path = BASE/'orders'/(key+'.order.json')
        path.write_text(json.dumps(order, separators=(',', ':'))+'\n')
        record.update(status='OK', path=str(path), runtime_path=str(path),
                      sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                      diagnostics=diag, size=path.stat().st_size)
    except Exception as error:
        record.update(status='INCOMPLETE', error=str(error), traceback=traceback.format_exc())
    record.update(start=started, end=time.time(), seconds=time.time()-started,
                  peak_mem_mb=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/2**20)
    (BASE/'orders'/(key+'.record.json')).write_text(json.dumps(record, indent=2))
    print(json.dumps(record), flush=True)
    return 0 if record['status']=='OK' else 1

if __name__=='__main__':
    raise SystemExit(main())
