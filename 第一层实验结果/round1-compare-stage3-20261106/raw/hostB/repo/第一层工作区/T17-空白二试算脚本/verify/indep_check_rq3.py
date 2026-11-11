# Independent re-implementation (numpy/scipy only; imports neither rq2lib nor rq3lib).
# Usage: python3 -I indep_check_rq3.py <matrix.mtx> <layouts.json>
# layouts.json: {"<name>|tau<k>|<kind>": [...]} where kind is
#   "order": a full row order pi -> prints T_full, T_inplace, T_keep, sumU_inplace, sumU_keep, mean T over cut offsets 1..15
#   "sigma": a final numbering sigma -> AIC windows = 16-row chunks of sigma restricted to kept rows (deg_A0 > k);
#            prints meanU, T, meanR, AIC write runs, residual write runs
# Structure = stored pattern (explicit zeros kept), symmetric expansion, diagonal removed (A0), as in rq2lib.load_mtx.
import json, sys, numpy as np, scipy.sparse as sp
mtx = sys.argv[1]; lay = json.load(open(sys.argv[2]))
rows = []; cols = []
with open(mtx) as f:
    lines = [l for l in f if not l.startswith('%')]
n = int(lines[0].split()[0])
for l in lines[1:]:
    t = l.split(); a, b = int(t[0]) - 1, int(t[1]) - 1
    if a == b: continue
    rows += [a, b]; cols += [b, a]
A = sp.csr_matrix((np.ones(len(rows)), (rows, cols)), shape=(n, n)); A.data[:] = 1
deg = np.asarray(A.sum(axis=1)).ravel()
W = 16

def nruns(sorted_pos):
    return 0 if len(sorted_pos) == 0 else 1 + int(np.count_nonzero(np.diff(sorted_pos) != 1))

def UT(groups):
    U = T = 0
    for g in groups:
        c = np.unique(A[np.array(g, dtype=int)].indices) if len(g) else np.array([], dtype=int)
        U += len(c); T += -(-len(c) // 16)
    return U, T

for key, seq in lay.items():
    name, tk, kind = key.split('|'); tau = int(tk[3:]); seq = np.array(seq)
    assert sorted(seq.tolist()) == list(range(n)), key
    resid = deg <= tau
    if kind == 'order':
        full = [seq[s:s + W] for s in range(0, n, W)]
        inpl = [g[~resid[g]] for g in full]; inpl = [g for g in inpl if len(g)]
        kept = seq[~resid[seq]]; keep = [kept[s:s + W] for s in range(0, len(kept), W)]
        Tf = UT(full)[1]; Ui, Ti = UT(inpl); Uk, Tk = UT(keep)
        ph = np.mean([UT([seq[:o]] + [seq[s:s + W] for s in range(o, n, W)])[1] for o in range(1, W)])
        print(key, dict(T_full=Tf, T_inplace=Ti, T_keep=Tk, U_inplace=Ui, U_keep=Uk, T_full_phase=round(float(ph), 1)))
    else:
        pos = np.empty(n, dtype=int); pos[seq] = np.arange(n)
        kept = seq[~resid[seq]]; wins = [kept[s:s + W] for s in range(0, len(kept), W)]
        U = T = R = WR = 0
        for g in wins:
            c = np.sort(pos[np.unique(A[g].indices)])
            U += len(c); T += -(-len(c) // 16); R += nruns(c); WR += nruns(np.sort(pos[g]))
        k = len(wins)
        print(key, dict(U=round(U / k, 2), T=T, R=round(R / k, 2), write_runs_aic=WR,
                        write_runs_resid=nruns(np.sort(pos[np.nonzero(resid)[0]]))))
